"""Filtro de praticabilidade do pool de jogadores.

O pool completo (base + enriquecidos) tem ~5.000 jogadores para 16 seleções, o que
é inviável num jogo. O filtro corta por **cota de posição por seleção**, mantendo a
forma de um elenco real em vez de ordenar tudo por nota (que produziria elencos com
1 goleiro e 35 meias).

Regra: os jogadores enriquecidos entram **sempre** (são o produto do trabalho e
foram declarados obrigatórios); a base completa cada posição até a cota, pelos
melhores `overall`. Por isso a cota é um **piso**, não um teto: uma seleção com mais
enriquecidos do que a cota mantém todos eles.
"""

from __future__ import annotations

import pandas as pd

from .config import grupo_posicao

COTAS_PADRAO = {"GK": 5, "DEF": 12, "MID": 12, "ATT": 11}
CAMADAS_ENRIQUECIDAS = ("convocado_2024", "historico")


def parse_cotas(texto: str) -> dict[str, int]:
    """Converte 'GK=5,DEF=12,MID=12,ATT=11' em dicionário, validando as chaves."""
    cotas: dict[str, int] = {}
    for parte in texto.split(","):
        if not parte.strip():
            continue
        if "=" not in parte:
            raise ValueError(f"cota inválida (esperado GRUPO=N): {parte!r}")
        grupo, valor = (x.strip() for x in parte.split("=", 1))
        if grupo not in COTAS_PADRAO:
            raise ValueError(f"grupo desconhecido: {grupo!r}")
        cotas[grupo] = int(valor)
    faltantes = set(COTAS_PADRAO) - set(cotas)
    if faltantes:
        raise ValueError(f"cotas ausentes para: {', '.join(sorted(faltantes))}")
    return cotas


def filtrar_pool(
    pool: pd.DataFrame,
    cotas: dict[str, int] | None = None,
    selecoes: list[str] | None = None,
    *,
    coluna_pais: str = "nationality_name",
    coluna_posicao: str = "player_positions",
    coluna_overall: str = "overall",
    coluna_camada: str = "camada",
) -> pd.DataFrame:
    """Aplica a cota de posição por seleção e devolve o pool filtrado."""
    cotas = cotas or COTAS_PADRAO
    colunas = list(pool.columns)
    df = pool.copy()
    df["_grupo"] = df[coluna_posicao].map(grupo_posicao)
    df = df[df["_grupo"].notna()]
    if selecoes is not None:
        df = df[df[coluna_pais].isin(selecoes)]

    partes = []
    for _, recorte in df.groupby(coluna_pais, sort=False):
        for grupo, cota in cotas.items():
            do_grupo = recorte[recorte["_grupo"] == grupo]
            if do_grupo.empty:
                continue
            enriquecidos = do_grupo[do_grupo[coluna_camada].isin(CAMADAS_ENRIQUECIDAS)]
            base = do_grupo[~do_grupo[coluna_camada].isin(CAMADAS_ENRIQUECIDAS)]
            base = base.sort_values(coluna_overall, ascending=False)
            # enriquecidos nunca são cortados: a cota é piso
            partes.append(enriquecidos)
            partes.append(base.head(max(0, cota - len(enriquecidos))))

    if not partes:
        return pool.head(0).copy()
    return pd.concat(partes, ignore_index=True).reindex(columns=colunas)


def resumo_por_selecao(filtrado: pd.DataFrame, coluna_pais: str = "nationality_name") -> pd.DataFrame:
    """Contagem por seleção e posição, para conferir o efeito do filtro."""
    if filtrado.empty:
        return pd.DataFrame()
    df = filtrado.copy()
    df["_grupo"] = df["player_positions"].map(grupo_posicao)
    tabela = df.pivot_table(index=coluna_pais, columns="_grupo", values="sofifa_id", aggfunc="count").fillna(0).astype(int)
    tabela["TOTAL"] = tabela.sum(axis=1)
    return tabela.sort_values("TOTAL", ascending=False)
