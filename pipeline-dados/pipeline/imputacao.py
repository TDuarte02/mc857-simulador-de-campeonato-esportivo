"""Imputação dos atributos do motor que a pesquisa não produz (decisão D5).

O motor de partidas usa 18 campos por jogador. As linhas pesquisadas (convocados
de 2024 fora da base e lendas) só trazem `overall`, os 6 atributos principais
(ou os 6 de goleiro) e as notas de posição: os 9 atributos detalhados abaixo, e
`goalkeeping_reflexes` dos jogadores de linha, ficam vazios.

Mesma técnica de `posicoes.py`: uma regressão linear por atributo, ajustada na
própria base FIFA 22 (19 mil jogadores completos).

- jogador de linha: `overall`, os 6 atributos principais e o grupo da posição
  principal (DEF/MID/ATT);
- goleiro: `overall` e os 6 atributos de goleiro.

O valor previsto é arredondado e limitado a [0, 99]; a linha registra em
`atributos_imputados` quais campos foram estimados. O erro por atributo é medido
num corte 15k/4k da base (`avaliar_imputacao`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ATRIBUTOS_GK, ATRIBUTOS_LINHA, grupo_posicao

ATRIBUTOS_DETALHADOS = (
    "attacking_heading_accuracy", "movement_agility", "movement_reactions",
    "movement_balance", "power_jumping", "power_stamina",
    "mentality_aggression", "mentality_penalties", "mentality_composure",
)
# Os 18 campos numéricos do jogador no motor (collective_attributes.Player).
CAMPOS_MOTOR = (
    "overall", "potential", *ATRIBUTOS_LINHA, *ATRIBUTOS_DETALHADOS, "goalkeeping_reflexes",
)
COLUNA_IMPUTADOS = "atributos_imputados"
VALOR_MINIMO, VALOR_MAXIMO = 0, 99
GRUPOS_LINHA = ("DEF", "MID")  # ATT é a referência das variáveis indicadoras
N_TREINO = 15_000


def _alvos(goleiro: bool) -> tuple[str, ...]:
    return ATRIBUTOS_DETALHADOS if goleiro else (*ATRIBUTOS_DETALHADOS, "goalkeeping_reflexes")


def _matriz(df: pd.DataFrame, goleiro: bool) -> np.ndarray:
    def coluna(nome: str) -> np.ndarray:
        return pd.to_numeric(df[nome], errors="coerce").to_numpy(dtype=float)

    if goleiro:
        variaveis = [coluna(c) for c in ("overall", *ATRIBUTOS_GK)]
    else:
        grupos = df["player_positions"].map(grupo_posicao)
        variaveis = [coluna(c) for c in ("overall", *ATRIBUTOS_LINHA)]
        variaveis += [grupos.eq(g).to_numpy(dtype=float) for g in GRUPOS_LINHA]
    return np.column_stack([np.ones(len(df)), *variaveis])


def _eh_goleiro(df: pd.DataFrame) -> pd.Series:
    return df["player_positions"].map(grupo_posicao).eq("GK")


def treinar_imputacao(base: pd.DataFrame) -> dict[str, dict[str, np.ndarray]]:
    """Coeficientes por atributo, separados para goleiros e jogadores de linha."""
    modelo: dict[str, dict[str, np.ndarray]] = {}
    goleiros = _eh_goleiro(base)
    for tipo, recorte in (("goleiro", base[goleiros]), ("linha", base[~goleiros & base["player_positions"].map(grupo_posicao).notna()])):
        goleiro = tipo == "goleiro"
        X = _matriz(recorte, goleiro)
        completas = ~np.isnan(X).any(axis=1)
        modelo[tipo] = {}
        for alvo in _alvos(goleiro):
            y = pd.to_numeric(recorte[alvo], errors="coerce").to_numpy(dtype=float)
            validas = completas & ~np.isnan(y)
            if validas.sum() < 100:
                raise ValueError(f"base insuficiente para imputar {alvo} ({tipo}): {int(validas.sum())} linhas")
            coeficientes, *_ = np.linalg.lstsq(X[validas], y[validas], rcond=None)
            modelo[tipo][alvo] = coeficientes
    return modelo


def _prever(coeficientes: np.ndarray, X: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(X @ coeficientes), VALOR_MINIMO, VALOR_MAXIMO)


def imputar(df: pd.DataFrame, modelo: dict[str, dict[str, np.ndarray]]) -> pd.DataFrame:
    """Preenche os atributos do motor vazios e registra quais foram estimados.

    Os atributos de linha vazios dos goleiros não são imputados: o motor os lê
    como 0 (convenção do dataset).
    """
    resultado = df.copy()
    imputados: dict[int, list[str]] = {idx: [] for idx in resultado.index}
    goleiros = _eh_goleiro(resultado)
    for tipo, mascara in (("goleiro", goleiros), ("linha", ~goleiros)):
        recorte = resultado[mascara]
        if recorte.empty:
            continue
        X = _matriz(recorte, tipo == "goleiro")
        if np.isnan(X).any():
            faltando = recorte.index[np.isnan(X).any(axis=1)].tolist()
            raise ValueError(f"linhas sem as variáveis da imputação ({tipo}): índices {faltando[:10]}")
        for alvo, coeficientes in modelo[tipo].items():
            vazios = pd.to_numeric(recorte[alvo], errors="coerce").isna().to_numpy()
            if not vazios.any():
                continue
            indices = recorte.index[vazios]
            resultado.loc[indices, alvo] = _prever(coeficientes, X[vazios])
            for idx in indices:
                imputados[idx].append(alvo)
    ordem = {campo: i for i, campo in enumerate(CAMPOS_MOTOR)}
    resultado[COLUNA_IMPUTADOS] = [
        ",".join(sorted(imputados[idx], key=ordem.__getitem__)) for idx in resultado.index
    ]
    return resultado


def avaliar_imputacao(base: pd.DataFrame, semente: int = 0, n_treino: int = N_TREINO) -> pd.DataFrame:
    """Erro absoluto médio por atributo, treinando em `n_treino` linhas e testando no resto."""
    ordem = np.random.default_rng(semente).permutation(len(base))
    treino, teste = base.iloc[ordem[:n_treino]], base.iloc[ordem[n_treino:]]
    modelo = treinar_imputacao(treino)
    linhas = []
    goleiros = _eh_goleiro(teste)
    for tipo, recorte in (("goleiro", teste[goleiros]), ("linha", teste[~goleiros & teste["player_positions"].map(grupo_posicao).notna()])):
        X = _matriz(recorte, tipo == "goleiro")
        for alvo, coeficientes in modelo[tipo].items():
            y = pd.to_numeric(recorte[alvo], errors="coerce").to_numpy(dtype=float)
            validas = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
            erro = np.abs(_prever(coeficientes, X[validas]) - y[validas])
            linhas.append({"tipo": tipo, "atributo": alvo, "n_teste": int(validas.sum()), "erro_medio": round(float(erro.mean()), 2)})
    return pd.DataFrame(linhas)
