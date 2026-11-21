"""Exporta o pool no formato que o motor do simulador consome.

O `Player` do motor (`simulador/python_prototype/collective_attributes.py`) exige 18
campos numéricos por jogador. Deste conjunto, o motor **lê de fato**:

- jogador de linha: os 6 principais + 7 dos 9 sub-atributos
- goleiro: apenas `goalkeeping_reflexes`

Os demais campos são exigidos pela dataclass mas nunca entram nos atributos coletivos
(o próprio docstring do motor registra que `overall`, `potential`, `power_stamina` e
`mentality_penalties` ficam de fora).

Duas decisões de preenchimento, medidas antes de tomadas:

1. **Sub-atributos derivados por regressão** treinada na própria base. Erro médio de
   ~5,4 pontos por jogador, que cai para ~0,3 no atributo do time e deixa **93% dos
   placares idênticos** aos que os valores reais produziriam. Pesquisar cada jogador
   não se pagaria.
2. **Goleiro com zeros nos 6 atributos de linha.** São multiplicados por peso 0 na
   agregação (verificado: mudar de 0 para 99 não altera o time). Ficam em zero, e não
   vazios, porque o motor calcularia `None * peso` e quebraria.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ("overall", "pace", "shooting", "passing", "dribbling", "defending", "physic")
ATRIBUTOS_LINHA = ("pace", "shooting", "passing", "dribbling", "defending", "physic")
SUB_ATRIBUTOS = (
    "attacking_heading_accuracy", "movement_agility", "movement_reactions",
    "movement_balance", "power_jumping", "power_stamina", "mentality_aggression",
    "mentality_penalties", "mentality_composure",
)
GOLEIRO = (
    "goalkeeping_diving", "goalkeeping_handling", "goalkeeping_kicking",
    "goalkeeping_positioning", "goalkeeping_reflexes", "goalkeeping_speed",
)
# name + pos + os 18 numéricos que a dataclass exige.
COLUNAS_MOTOR = ("name", "pos", "overall", "potential", *ATRIBUTOS_LINHA, *SUB_ATRIBUTOS, "goalkeeping_reflexes")
# Colunas extras, fora do contrato do motor, só para rastreio.
COLUNAS_EXTRA = ("pais", "camada", "sofifa_id", "player_positions")

POSICAO_PADRAO = "CM"


def _numerico(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce")


def treinar_sub_atributos(dataset: pd.DataFrame) -> dict[str, np.ndarray]:
    """Ajusta uma regressão por sub-atributo a partir dos 7 atributos principais.

    Só usa jogadores de linha: goleiro não tem os atributos principais na base, então
    não há o que aprender para eles (e o motor não os lê mesmo).
    """
    linhas = dataset[~dataset["player_positions"].astype(str).str.startswith("GK")]
    linhas = linhas.dropna(subset=[*FEATURES, *SUB_ATRIBUTOS])
    X = np.column_stack([np.ones(len(linhas)), *[_numerico(linhas[c]).to_numpy(float) for c in FEATURES]])
    modelo: dict[str, np.ndarray] = {}
    for coluna in SUB_ATRIBUTOS:
        y = _numerico(linhas[coluna]).to_numpy(float)
        modelo[coluna], *_ = np.linalg.lstsq(X, y, rcond=None)
    return modelo


def _prever(modelo: dict[str, np.ndarray], linha: pd.Series) -> dict[str, int]:
    vetor = np.array([1.0, *[float(_numerico(pd.Series([linha.get(c)]))[0] or 0) for c in FEATURES]])
    return {
        coluna: int(round(min(99, max(1, float(vetor @ coeficientes)))))
        for coluna, coeficientes in modelo.items()
    }


def _codigo_posicao(bruto: object) -> str:
    """Primeiro código de `player_positions` ('CAM, CF' -> 'CAM')."""
    primeiro = str(bruto or "").split(",")[0].strip().upper()
    return primeiro or POSICAO_PADRAO


def exportar_jogadores(pool: pd.DataFrame, dataset: pd.DataFrame) -> pd.DataFrame:
    """Monta o dataframe no formato do motor: uma linha por jogador do pool.

    Onde a base já tem os sub-atributos (jogadores de linha vindos do `players_22.csv`),
    usa o valor real; onde não tem (os enriquecidos), usa o derivado.
    """
    modelo = treinar_sub_atributos(dataset)
    registros = []
    for linha in pool.to_dict("records"):
        posicao = _codigo_posicao(linha.get("player_positions"))
        goleiro = posicao == "GK"
        registro = {
            "name": str(linha.get("short_name") or linha.get("long_name") or ""),
            "pos": posicao,
            "overall": int(linha.get("overall") or 0),
            "potential": int(linha.get("potential") or linha.get("overall") or 0),
        }
        for coluna in ATRIBUTOS_LINHA:
            valor = linha.get(coluna)
            # Goleiro: zero explícito (peso 0 na agregação; a dataclass exige número).
            registro[coluna] = 0 if goleiro or pd.isna(valor) else int(valor)
        if goleiro:
            # Não entram no cálculo do goleiro (a defesa dele é o `reflexes`).
            registro.update({coluna: 0 for coluna in SUB_ATRIBUTOS})
        else:
            derivados = _prever(modelo, pd.Series(linha))
            for coluna in SUB_ATRIBUTOS:
                valor = linha.get(coluna)
                registro[coluna] = derivados[coluna] if pd.isna(valor) else int(valor)
        registro["goalkeeping_reflexes"] = int(linha.get("goalkeeping_reflexes") or 0) if goleiro else 0
        registro.update({
            "pais": linha.get("nationality_name"),
            "camada": linha.get("camada"),
            "sofifa_id": linha.get("sofifa_id"),
            "player_positions": linha.get("player_positions"),
        })
        registros.append(registro)
    return pd.DataFrame(registros).reindex(columns=[*COLUNAS_MOTOR, *COLUNAS_EXTRA])
