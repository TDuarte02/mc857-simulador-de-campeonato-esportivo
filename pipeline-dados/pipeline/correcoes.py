"""Correções de dados de origem, versionadas e com fonte.

A base FIFA 22 e as pesquisas nunca são reescritas: um erro conhecido entra em
`artefatos/correcoes/datas_nascimento.csv` (sofifa_id, dob, fonte_url, observacao)
e é aplicado ao pool durante o `build-catalog`.

Ordem importa: as correções entram DEPOIS do registro de ids (a chave do registro
inclui a data de nascimento, então corrigir antes trocaria o id da linha) e ANTES
do casamento de convocados e de `person_key`, que usam a data.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUNAS = ("sofifa_id", "dob", "fonte_url", "observacao")
CORRECOES_PADRAO = Path(__file__).resolve().parents[1] / "artefatos/correcoes/datas_nascimento.csv"


def carregar_correcoes(caminho: Path | None) -> pd.DataFrame:
    if caminho is None or not Path(caminho).exists():
        return pd.DataFrame(columns=COLUNAS)
    df = pd.read_csv(caminho, dtype=str).fillna("")
    faltando = [c for c in COLUNAS if c not in df.columns]
    if faltando:
        raise ValueError(f"{caminho}: colunas ausentes: {', '.join(faltando)}")
    sem_fonte = df[df["fonte_url"].str.strip().eq("")]
    if not sem_fonte.empty:
        raise ValueError(f"{caminho}: correção sem fonte para os ids {', '.join(sem_fonte['sofifa_id'])}")
    return df


def aplicar_datas_nascimento(pool: pd.DataFrame, correcoes: pd.DataFrame) -> pd.DataFrame:
    """Substitui `dob` das linhas corrigidas; id inexistente ou repetido interrompe a execução."""
    if correcoes.empty:
        return pool
    pool = pool.copy()
    ids = pool["sofifa_id"].astype("Int64").astype(str)
    for _, correcao in correcoes.iterrows():
        alvo = ids.eq(str(int(correcao["sofifa_id"])))
        if alvo.sum() != 1:
            raise ValueError(
                f"correção de data de nascimento para o id {correcao['sofifa_id']}: "
                f"{int(alvo.sum())} linha(s) no pool, esperada 1"
            )
        pool.loc[alvo, "dob"] = correcao["dob"]
    return pool
