"""Validação de propostas intermediárias devolvidas pelo LLM e do catálogo final."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd

from .config import ATRIBUTOS_GK, ATRIBUTOS_LINHA, grupo_posicao
from .sources import validar_fontes

CAMPOS_OBRIGATORIOS = {"nome", "pais", "posicao", "percentis", "fontes", "observacao", "status"}
CAMPOS_PERCENTIS = set(ATRIBUTOS_LINHA + ATRIBUTOS_GK + ("overall",))
STATUS_PERMITIDOS = {"approved", "review_required", "rejected"}


def carregar_propostas(caminho) -> list[dict[str, Any]]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if isinstance(dados, dict):
        dados = dados.get("jogadores")
    if not isinstance(dados, list):
        raise ValueError("a resposta deve ser uma lista JSON de jogadores")
    return dados


def validar_proposta(proposta: dict[str, Any], pais_esperado: str | None = None) -> list[str]:
    erros: list[str] = []
    faltantes = CAMPOS_OBRIGATORIOS - set(proposta)
    erros.extend(f"campo obrigatório ausente: {campo}" for campo in sorted(faltantes))
    if proposta.get("pais") and pais_esperado and proposta["pais"] != pais_esperado:
        erros.append(f"país incorreto: esperado {pais_esperado}, recebido {proposta['pais']}")
    if proposta.get("status") not in STATUS_PERMITIDOS:
        erros.append(f"status inválido: {proposta.get('status')!r}")
    elif proposta.get("status") != "approved":
        erros.append("proposta ainda não está aprovada")
    grupo = grupo_posicao(proposta.get("posicao", ""))
    if not grupo:
        erros.append(f"posição inválida: {proposta.get('posicao')!r}")
    percentis = proposta.get("percentis")
    if not isinstance(percentis, dict):
        erros.append("percentis deve ser um objeto JSON")
    else:
        desconhecidos = set(percentis) - CAMPOS_PERCENTIS
        erros.extend(f"atributo desconhecido: {campo}" for campo in sorted(desconhecidos))
        for coluna, valor in percentis.items():
            if valor is None:
                continue
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0 <= valor <= 1:
                erros.append(f"percentil inválido para {coluna}: {valor!r}")
        if grupo == "GK":
            if any(percentis.get(c) is not None for c in ATRIBUTOS_LINHA):
                erros.append("goleiro não pode ter percentis de atributos de linha")
            if not any(percentis.get(c) is not None for c in ATRIBUTOS_GK):
                erros.append("goleiro deve ter ao menos um atributo específico")
        elif any(percentis.get(c) is not None for c in ATRIBUTOS_GK):
            erros.append("jogador de linha não pode ter percentis de goleiro")
    erros.extend(validar_fontes(proposta.get("fontes")))
    if not str(proposta.get("observacao", "")).strip():
        erros.append("observacao obrigatória")
    dob = proposta.get("dob")
    if dob:
        try:
            date.fromisoformat(dob)
        except (TypeError, ValueError):
            erros.append(f"dob não está em ISO-8601: {dob!r}")
    confianca = proposta.get("confianca")
    if confianca is not None and (isinstance(confianca, bool) or not isinstance(confianca, (int, float)) or not 0 <= confianca <= 1):
        erros.append("confianca deve estar entre 0 e 1")
    return erros


def validar_propostas(propostas: list[dict[str, Any]], pais_esperado: str | None = None) -> list[dict[str, Any]]:
    nomes: set[tuple[str, str]] = set()
    resultado = []
    for proposta in propostas:
        chave = (str(proposta.get("pais", "")), str(proposta.get("nome", "")).casefold())
        erros = validar_proposta(proposta, pais_esperado)
        if chave in nomes:
            erros.append("jogador duplicado na proposta")
        nomes.add(chave)
        resultado.append({"nome": proposta.get("nome", ""), "erros": erros, "status": "approved" if not erros else "review_required"})
    return resultado


# ============================================================
# Catálogo final (o arquivo que o servidor carrega no Mongo)
# ============================================================

# Mínimo de pessoas distintas por setor da posição principal: uma convocação
# precisa de 3 GK, 8 DEF, 8 MID e 7 FW (ATT no pipeline).
MINIMOS_POR_SETOR = {"GK": 3, "DEF": 8, "MID": 8, "ATT": 7}
ESCALA_MOTOR = (0, 100)


def validar_catalogo(
    catalogo: pd.DataFrame,
    convocacoes: pd.DataFrame,
    campos_motor: tuple[str, ...],
) -> list[str]:
    """Erros do catálogo: campos do motor, ids, cotas por setor e convocados.

    - toda linha tem os campos do motor em [0, 100]; só os atributos de linha de
      goleiros podem ficar vazios (o motor os lê como 0);
    - ids únicos;
    - cada seleção tem ao menos 3 GK / 8 DEF / 8 MID / 7 ATT pela posição
      principal, contando `person_key` distintos (duas versões de uma pessoa
      contam uma vez);
    - todo convocado listado está presente (`is_convocado_2024`).
    """
    erros: list[str] = []
    goleiro = catalogo["player_positions"].map(grupo_posicao).eq("GK")
    for campo in campos_motor:
        if campo not in catalogo.columns:
            erros.append(f"coluna do motor ausente: {campo}")
            continue
        valores = pd.to_numeric(catalogo[campo], errors="coerce")
        vazio = valores.isna()
        if campo in ATRIBUTOS_LINHA:
            vazio &= ~goleiro
        baixo, alto = ESCALA_MOTOR
        fora = valores.notna() & ((valores < baixo) | (valores > alto))
        for idx in catalogo.index[vazio | fora]:
            linha = catalogo.loc[idx]
            erros.append(
                f"{linha['nationality_name']}: {linha['short_name']} ({linha['sofifa_id']}): "
                f"{campo} {'vazio' if vazio[idx] else f'fora de [0, 100]: {valores[idx]}'}"
            )

    repetidos = catalogo["sofifa_id"][catalogo["sofifa_id"].duplicated(keep=False)]
    for sofifa_id in sorted(set(repetidos)):
        nomes = catalogo.loc[catalogo["sofifa_id"].eq(sofifa_id), "short_name"].tolist()
        erros.append(f"id repetido {sofifa_id}: {nomes}")

    setores = catalogo["player_positions"].map(grupo_posicao)
    for pais in sorted(convocacoes["pais"].unique()):
        da_selecao = catalogo["nationality_name"].eq(pais)
        for setor, minimo in MINIMOS_POR_SETOR.items():
            pessoas = catalogo.loc[da_selecao & setores.eq(setor), "person_key"].nunique()
            if pessoas < minimo:
                erros.append(f"{pais}: {pessoas} pessoa(s) em {setor}, mínimo {minimo}")
        listados = int(convocacoes["pais"].eq(pais).sum())
        presentes = int((da_selecao & catalogo["is_convocado_2024"].fillna(False).astype(bool)).sum())
        if presentes != listados:
            erros.append(f"{pais}: {presentes} convocado(s) no catálogo, {listados} listado(s)")
    return erros
