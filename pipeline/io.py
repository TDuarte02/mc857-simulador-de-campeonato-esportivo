"""Leitura e escrita dos artefatos tabulares do pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import COLUNAS_CONVOCACAO, COLUNAS_ESCALACAO


def carregar_dataset(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(f"dataset não encontrado: {caminho}")
    df = pd.read_csv(caminho, low_memory=False)
    obrigatorias = {"sofifa_id", "short_name", "long_name", "player_positions", "overall", "nationality_name"}
    faltantes = sorted(obrigatorias - set(df.columns))
    if faltantes:
        raise ValueError(f"colunas obrigatórias ausentes no dataset: {', '.join(faltantes)}")
    return df


def carregar_convocacoes(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(f"convocações não encontradas: {caminho}")
    df = pd.read_csv(caminho, dtype=str).fillna("")
    faltantes = sorted(set(COLUNAS_CONVOCACAO) - set(df.columns))
    if faltantes:
        raise ValueError(f"colunas obrigatórias ausentes nas convocações: {', '.join(faltantes)}")
    if df.empty:
        raise ValueError("arquivo de convocações vazio")
    if df["pais"].eq("").any() or df["nome"].eq("").any():
        raise ValueError("convocações devem ter pais e nomes não vazios")
    return df


def carregar_escalacao(caminho: Path | None) -> pd.DataFrame:
    if caminho is None:
        return pd.DataFrame(columns=COLUNAS_ESCALACAO)
    if not caminho.exists():
        raise FileNotFoundError(f"escalação não encontrada: {caminho}")
    df = pd.read_csv(caminho, dtype=str).fillna("")
    faltantes = sorted(set(COLUNAS_ESCALACAO) - set(df.columns))
    if faltantes:
        raise ValueError(f"colunas obrigatórias ausentes na escalação: {', '.join(faltantes)}")
    return df


def escrever_csv(df: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, encoding="utf-8")
