"""Validação de propostas intermediárias devolvidas pelo LLM."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

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
