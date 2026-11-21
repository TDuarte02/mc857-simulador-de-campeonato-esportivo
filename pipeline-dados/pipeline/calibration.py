"""Estatísticas e amostras usadas como régua de calibração."""

from __future__ import annotations

import math

import pandas as pd

from .config import ATRIBUTOS_GK, ATRIBUTOS_LINHA, grupo_posicao


def pool_por_posicao(dataset: pd.DataFrame, pais: str | None, grupo: str) -> pd.DataFrame:
    """Pool de calibração. `pais=None` usa o conjunto inteiro (escala global).

    O pool do país serve para jogadores atuais: um titular de seleção é o topo
    daquele país. Para históricos isso não funciona — o teto do pool de um país
    (ex.: meias da Argentina, 87) não deixa espaço para uma lenda. Nesses casos a
    calibração usa a distribuição global, onde o topo é o melhor jogador da base.
    """
    recorte = dataset[dataset["nationality_name"].eq(pais)].copy() if pais else dataset.copy()
    if grupo == "GK":
        mascara = recorte["player_positions"].fillna("").str.upper().str.contains(r"(?:^|,\s*)GK(?:,|$)", regex=True)
    else:
        mascara = ~recorte["player_positions"].fillna("").str.upper().str.contains(r"(?:^|,\s*)GK(?:,|$)", regex=True)
        grupos = {"DEF": {"CB", "LB", "RB", "LWB", "RWB"}, "MID": {"DM", "CDM", "CM", "AM", "CAM", "LM", "RM"}, "ATT": {"LW", "RW", "ST", "CF", "LS", "RS", "LF", "RF"}}
        posicoes = grupos.get(grupo, set())
        mascara &= recorte["player_positions"].fillna("").apply(
            lambda valor: bool({p.strip() for p in str(valor).upper().split(",")} & posicoes)
        )
    return recorte[mascara]


def _resumo_coluna(pool: pd.DataFrame, coluna: str) -> dict[str, float | int | None]:
    if coluna not in pool:
        return {"n": 0, "min": None, "q25": None, "mediana": None, "q75": None, "max": None}
    serie = pd.to_numeric(pool[coluna], errors="coerce").dropna()
    if serie.empty:
        return {"n": 0, "min": None, "q25": None, "mediana": None, "q75": None, "max": None}
    return {
        "n": int(serie.size),
        "min": float(serie.min()),
        "q25": float(serie.quantile(0.25)),
        "mediana": float(serie.median()),
        "q75": float(serie.quantile(0.75)),
        "max": float(serie.max()),
    }


def estatisticas_calibracao(dataset: pd.DataFrame, pais: str, grupo: str) -> dict:
    pool = pool_por_posicao(dataset, pais, grupo)
    atributos = (ATRIBUTOS_GK if grupo == "GK" else ATRIBUTOS_LINHA) + ("overall",)
    return {
        "pais": pais,
        "grupo": grupo,
        "n_jogadores": int(len(pool)),
        "atributos": {coluna: _resumo_coluna(pool, coluna) for coluna in atributos},
    }


def amostra_representativa(dataset: pd.DataFrame, pais: str, grupo: str, limite: int = 10) -> list[dict]:
    pool = pool_por_posicao(dataset, pais, grupo).sort_values("overall", ascending=False)
    if pool.empty:
        return []
    indices = sorted(set([0, len(pool) - 1] + [round(i * (len(pool) - 1) / max(limite - 1, 1)) for i in range(limite)]))
    colunas = [c for c in ("short_name", "long_name", "player_positions", "overall", "pace", "shooting", "passing", "dribbling", "defending", "physic", *ATRIBUTOS_GK) if c in pool]
    return pool.iloc[indices].loc[:, colunas].where(pd.notna(pool.iloc[indices].loc[:, colunas]), None).to_dict("records")


def converter_percentil(pool: pd.DataFrame, coluna: str, percentil: object) -> int | None:
    """Converte percentil [0, 1] em nota inteira; retorna None para ausência."""
    if percentil is None or (isinstance(percentil, float) and math.isnan(percentil)):
        return None
    try:
        valor = float(percentil)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"percentil inválido para {coluna}: {percentil!r}") from exc
    if not 0 <= valor <= 1:
        raise ValueError(f"percentil fora de [0, 1] para {coluna}: {valor}")
    serie = pd.to_numeric(pool.get(coluna, pd.Series(dtype=float)), errors="coerce").dropna()
    if serie.empty:
        return None
    return max(1, min(99, round(float(serie.quantile(valor)))))


def grupo_da_proposta(posicao: str) -> str:
    grupo = grupo_posicao(posicao)
    if not grupo:
        raise ValueError(f"posição não reconhecida: {posicao!r}")
    return grupo


# Política declarada para históricos: o `overall` da base é comprimido no topo
# (p90 -> ~75, p99 -> ~82, máximo 93), então o percentil não tem como expressar uma
# lenda. Estes pontos preservam a ordem dos percentis mas movem o topo para uma
# faixa compatível com "maiores de todos os tempos".
ANCORAS_BANDA_LENDA = (
    (0.00, 74), (0.50, 74), (0.70, 77), (0.80, 80),
    (0.90, 86), (0.95, 90), (0.99, 96), (1.00, 97),
)


def banda_lenda(percentil: object) -> int | None:
    """Converte o percentil de um jogador histórico no overall da banda de lenda."""
    if percentil is None:
        return None
    if isinstance(percentil, bool) or not isinstance(percentil, (int, float)):
        return None
    p = max(0.0, min(1.0, float(percentil)))
    for (x0, y0), (x1, y1) in zip(ANCORAS_BANDA_LENDA, ANCORAS_BANDA_LENDA[1:]):
        if p <= x1:
            return y1 if x1 == x0 else round(y0 + (y1 - y0) * (p - x0) / (x1 - x0))
    return ANCORAS_BANDA_LENDA[-1][1]
