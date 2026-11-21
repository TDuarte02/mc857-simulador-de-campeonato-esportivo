"""Reâncora as lendas históricas pela força real do país.

**O problema que isto resolve.** A banda de lenda (`calibration.banda_lenda`) tinha
âncoras fixas e globais: qualquer jogador que o enriquecimento julgasse "lenda
nacional" (percentil 0,95–0,99) recebia 90–96, **independente do país**. Só que a
curadoria mediu grandeza *dentro* do país, e a banda converteu isso em grandeza
*absoluta*. O resultado, medido nos dados:

    teto da base real (FIFA 22):  Bolívia 71  ->  Argentina 93   (amplitude 22)
    teto das nossas lendas:       Bolívia 90  ->  Argentina 97   (amplitude  7)

Ou seja: De Rosario (Canadá) ficou com 93 — a mesma nota do Messi — e a Bolívia
ganhou uma lenda de 90 quando seu melhor jogador real é 71. No jogo isso aparecia
como times quase equivalentes: o Brasil vencia o Canadá só 60% das vezes.

**A correção.** Em vez de âncora global, cada país ancora na sua própria força: a
média dos `k` melhores jogadores da base daquele país. O deslocamento resultante é
aplicado às lendas **estimadas**; as que têm nota real de EA FC Icon não são tocadas,
porque essas já são dado observado e não estimativa.
"""

from __future__ import annotations

import pandas as pd

from .motor import ATRIBUTOS_LINHA, GOLEIRO, SUB_ATRIBUTOS

# A média dos `k` melhores evita o artefato de uma estrela isolada: o melhor
# costa-riquenho da base é o Navas (88), muito acima do resto do elenco, e usar o
# máximo fazia o México × Costa Rica inverter (43% -> 30% para a Costa Rica).
ANCORA_TOPO_K = 3
# Quanto a melhor lenda do país deve ficar acima do nível atual dele.
BONUS_PADRAO = 4.0
# Topo de referência da banda de lenda (a âncora de percentil 0,99 em
# `calibration.ANCORAS_BANDA_LENDA`).
BANDA_TOPO = 96.0
# Notas reais não são reescaladas: são dado observado, não estimativa.
FONTE_REAL = "ea_fc_icon"
# Só as colunas de atributo são deslocadas — nunca `sofifa_id`, `age`,
# `confianca` ou qualquer campo de rastreio.
COLUNAS_ATRIBUTOS = ("overall", "potential", *ATRIBUTOS_LINHA, *SUB_ATRIBUTOS, *GOLEIRO)


def calcular_ancoras(dataset: pd.DataFrame, k: int = ANCORA_TOPO_K) -> dict[str, float]:
    """Média dos `k` melhores `overall` da base, por nacionalidade.

    É a medida de "quão forte é este país hoje" — mais robusta que o máximo, que
    seria dominado por um único craque.
    """
    if k < 1:
        raise ValueError("k deve ser pelo menos 1")
    ancoras: dict[str, float] = {}
    for pais, recorte in dataset.groupby("nationality_name"):
        melhores = pd.to_numeric(recorte["overall"], errors="coerce").dropna().nlargest(k)
        if not melhores.empty:
            ancoras[str(pais)] = float(melhores.mean())
    return ancoras


def calcular_deslocamento(
    ancora: float | None,
    bonus: float = BONUS_PADRAO,
    banda_topo: float = BANDA_TOPO,
) -> float:
    """Quanto deslocar a banda do país para que o topo dela caia em `ancora + bonus`.

    Positivo = o país é mais fraco que a banda global, então as lendas descem.
    """
    if ancora is None:
        return 0.0
    return banda_topo - ancora - bonus


def deslocamentos_por_pais(
    dataset: pd.DataFrame,
    bonus: float = BONUS_PADRAO,
    k: int = ANCORA_TOPO_K,
) -> dict[str, float]:
    """Deslocamento da banda para cada nacionalidade da base."""
    return {
        pais: calcular_deslocamento(ancora, bonus)
        for pais, ancora in calcular_ancoras(dataset, k).items()
    }


def _mascara_historico(df: pd.DataFrame) -> pd.Series:
    """Identifica as linhas da camada histórica, com ou sem a coluna `camada`."""
    if "camada" in df.columns:
        return df["camada"].eq("historico")
    if "is_historico" in df.columns:
        return df["is_historico"].astype(bool)
    raise ValueError("não dá para identificar a camada histórica: falta 'camada' ou 'is_historico'")


def reescalar_lendas(
    pool: pd.DataFrame,
    dataset: pd.DataFrame,
    *,
    bonus: float = BONUS_PADRAO,
    k: int = ANCORA_TOPO_K,
    colunas: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Aplica o deslocamento por país às lendas estimadas do `pool`.

    Funciona tanto no pool consolidado (coluna `camada`) quanto num snapshot por
    país (coluna `is_historico`). Devolve `(pool reescalado, deslocamentos usados)`.
    As linhas com nota real (`fonte_atributos == "ea_fc_icon"`) ficam intactas.
    """
    deslocamentos = deslocamentos_por_pais(dataset, bonus, k)
    alvo = colunas or [c for c in COLUNAS_ATRIBUTOS if c in pool.columns]
    df = pool.copy()
    historico = _mascara_historico(df)
    fonte = df["fonte_atributos"] if "fonte_atributos" in df.columns else pd.Series("", index=df.index)
    for pais, deslocamento in deslocamentos.items():
        if deslocamento == 0:
            continue
        indices = df.index[historico & df["nationality_name"].eq(pais) & fonte.ne(FONTE_REAL)]
        for coluna in alvo:
            if coluna not in df.columns or not pd.api.types.is_numeric_dtype(df[coluna]):
                continue
            df.loc[indices, coluna] = (
                pd.to_numeric(df.loc[indices, coluna], errors="coerce") - deslocamento
            ).clip(1, 99).round()
    return df, deslocamentos
