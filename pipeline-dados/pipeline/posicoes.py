"""Posições: códigos válidos, normalização e derivação das notas por posição.

A base traz 27 colunas de posição específica (`st`, `cb`, `cam`, …) preenchidas para
praticamente todos os jogadores, inclusive fora da posição natural. É o jogo que
decide por limiar quem pode atuar onde — o campo vazio não significa "não joga ali".

Para os jogadores enriquecidos só geramos essas colunas nas **posições plausíveis**
(principal + até duas secundárias), deixando as outras 24 vazias: preencher as 27 por
extrapolação produziria números que ninguém pediu e que sugeririam polivalência que o
jogador não tem.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

# Os 15 códigos que existem de fato no conjunto da base.
CODIGOS_VALIDOS = (
    "CAM", "CB", "CDM", "CF", "CM", "GK", "LB", "LM", "LW", "LWB",
    "RB", "RM", "RW", "RWB", "ST",
)
COLUNAS_POSICAO = (
    "ls", "st", "rs", "lw", "lf", "cf", "rf", "rw", "lam", "cam", "ram",
    "lm", "lcm", "cm", "rcm", "rm", "lwb", "ldm", "cdm", "rdm", "rwb",
    "lb", "lcb", "cb", "rcb", "rb", "gk",
)
ATRIBUTOS_MODELO = ("overall", "pace", "shooting", "passing", "dribbling", "defending", "physic")
# A curadoria histórica usava AM/DM; a base usa CAM/CDM.
NORMALIZACAO = {"AM": "CAM", "DM": "CDM"}
MAX_SECUNDARIAS = 2
VALOR_MINIMO, VALOR_MAXIMO = 1, 99


def normalizar_codigo(codigo: object) -> str:
    """Uppercase + correção dos códigos da curadoria que não existem na base."""
    limpo = str(codigo or "").strip().upper()
    return NORMALIZACAO.get(limpo, limpo)


def parse_valor(bruto: object) -> int | None:
    """Converte o formato FIFA da base ('90+2' = nota + bônus) em inteiro."""
    if bruto is None or (isinstance(bruto, float) and np.isnan(bruto)):
        return None
    achado = re.match(r"^\s*(\d+)(?:\+(\d+))?\s*$", str(bruto))
    if not achado:
        return None
    return int(achado.group(1)) + int(achado.group(2) or 0)


def validar_secundarias(principal: str, secundarias: object) -> tuple[list[str], list[str]]:
    """Devolve (lista limpa, erros). Goleiro nunca tem secundária; máximo de 2."""
    principal = normalizar_codigo(principal)
    erros: list[str] = []
    limpas: list[str] = []
    if secundarias is None:
        return limpas, erros
    if not isinstance(secundarias, (list, tuple)):
        return limpas, [f"posicoes_secundarias deve ser lista, veio {type(secundarias).__name__}"]
    for codigo in secundarias:
        normalizado = normalizar_codigo(codigo)
        if normalizado not in CODIGOS_VALIDOS:
            erros.append(f"código inválido: {codigo!r}")
            continue
        if normalizado == principal:
            erros.append(f"secundária repete a principal: {normalizado}")
            continue
        if normalizado in limpas:
            continue
        limpas.append(normalizado)
    if len(limpas) > MAX_SECUNDARIAS:
        erros.append(f"mais de {MAX_SECUNDARIAS} secundárias")
        limpas = limpas[:MAX_SECUNDARIAS]
    if principal == "GK" and limpas:
        erros.append("goleiro não deve ter posições secundárias")
        limpas = []
    return limpas, erros


def posicoes_plausiveis(principal: str, secundarias: list[str] | None = None) -> list[str]:
    """Principal + secundárias válidas, na ordem, sem repetição."""
    limpas, _ = validar_secundarias(principal, secundarias or [])
    return [normalizar_codigo(principal), *limpas]


def treinar_modelo(dataset: pd.DataFrame) -> dict[str, np.ndarray]:
    """Ajusta uma regressão linear por coluna de posição, na própria base.

    A base é o conjunto de treino natural: ela tem, para 19 mil jogadores, os 7
    atributos disponíveis E as 27 notas de posição. Validado em 15k/4k: erro médio
    de ~1,5 ponto na escala 0-99.
    """
    colunas = [pd.to_numeric(dataset[c], errors="coerce").fillna(0).to_numpy(dtype=float) for c in ATRIBUTOS_MODELO]
    X = np.column_stack([np.ones(len(dataset)), *colunas])
    modelo: dict[str, np.ndarray] = {}
    for coluna in COLUNAS_POSICAO:
        if coluna not in dataset.columns:
            continue
        y = dataset[coluna].map(parse_valor).to_numpy(dtype=float)
        validos = ~np.isnan(y)
        if validos.sum() < 100:
            continue
        coeficientes, *_ = np.linalg.lstsq(X[validos], y[validos], rcond=None)
        modelo[coluna] = coeficientes
    return modelo


def _numero(valor: object) -> float:
    """Converte para float tratando None/NaN — `nan or 0` devolveria nan, não 0."""
    if valor is None:
        return 0.0
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if np.isnan(numero) else numero


def prever_colunas(
    modelo: dict[str, np.ndarray],
    atributos: dict,
    principal: str,
    secundarias: list[str] | None = None,
) -> dict[str, int | None]:
    """Notas só para as posições plausíveis; as demais 24 colunas ficam `None`."""
    vetor = np.array([1.0, *[_numero(atributos.get(c)) for c in ATRIBUTOS_MODELO]])
    plausiveis = {c.lower() for c in posicoes_plausiveis(principal, secundarias)}
    previsoes: dict[str, int | None] = {}
    for coluna in COLUNAS_POSICAO:
        if coluna not in plausiveis or coluna not in modelo:
            previsoes[coluna] = None
            continue
        previsoes[coluna] = max(VALOR_MINIMO, min(VALOR_MAXIMO, int(round(float(vetor @ modelo[coluna])))))
    return previsoes


def formatar_posicoes(principal: str, secundarias: list[str] | None = None) -> str:
    """Formata como a base: 'CAM, ST'."""
    return ", ".join(posicoes_plausiveis(principal, secundarias))


def injetar_secundarias(propostas: list[dict], respostas: list[dict]) -> int:
    """Copia as posições secundárias pesquisadas para dentro das propostas.

    Assim elas viajam pelo pipeline (validate → publish → materialize) em vez de
    serem aplicadas à mão por cima do snapshot publicado.
    """
    indice = {(str(r.get("nome", "")), str(r.get("dob", ""))[:10]): r for r in respostas}
    injetadas = 0
    for proposta in propostas:
        chave = (str(proposta.get("nome", "")), str(proposta.get("dob") or "")[:10])
        resposta = indice.get(chave)
        if resposta is None:
            continue
        limpas, _ = validar_secundarias(proposta.get("posicao", ""), resposta.get("posicoes_secundarias"))
        if limpas:
            proposta["posicoes_secundarias"] = limpas
            injetadas += 1
    return injetadas


def aplicar_posicoes(
    snapshot: pd.DataFrame,
    respostas: list[dict],
    modelo: dict[str, np.ndarray],
    *,
    coluna_nome: str = "short_name",
    coluna_dob: str = "dob",
    coluna_posicao: str = "player_positions",
) -> tuple[pd.DataFrame, int]:
    """Atualiza `player_positions` e as colunas de posição de um snapshot já publicado.

    Atalho para reprocessar um artefato solto. O caminho normal do pipeline é a
    proposta carregar `posicoes_secundarias` e o `materialize` preencher as colunas
    ao publicar — ver `injetar_secundarias`.
    """
    indice = {(str(r.get("nome", "")), str(r.get("dob", ""))[:10]): r for r in respostas}
    df = snapshot.copy()
    atualizados = 0
    for i in df.index:
        linha = df.loc[i]
        chave = (str(linha[coluna_nome]), str(linha.get(coluna_dob) or "")[:10])
        resposta = indice.get(chave)
        if resposta is None:
            continue
        principal = normalizar_codigo(str(linha[coluna_posicao]).split(",")[0])
        secundarias = resposta.get("posicoes_secundarias") or []
        df.at[i, coluna_posicao] = formatar_posicoes(principal, secundarias)
        for coluna, valor in prever_colunas(modelo, linha.to_dict(), principal, secundarias).items():
            if valor is not None:
                df.at[i, coluna] = valor
        atualizados += 1
    return df, atualizados
