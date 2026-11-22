"""Relatórios consolidados da execução e merge dos snapshots publicados."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .runner import diretorio_pais, nome_snapshot
from .state import STATUS_PENDING, STATUS_PUBLISHED

COLUNAS_RESUMO = (
    "pais", "convocados", "presentes", "ausentes",
    "aprovados", "revisao_manual", "tentativas", "status",
)


def _contagens_lacunas(caminho: Path) -> dict[str, int | None]:
    if not caminho.exists():
        return {"convocados": None, "presentes": None, "ausentes": None}
    df = pd.read_csv(caminho, dtype=str).fillna("")
    return {
        "convocados": int(len(df)),
        "presentes": int((df["status"] == "present").sum()),
        "ausentes": int((df["status"] == "missing").sum()),
    }


def consolidar_resumo(manifesto: dict[str, Any], raiz: Path | None = None) -> pd.DataFrame:
    """Uma linha por país, com contagens de convocação e estado do manifesto."""
    linhas = []
    for pais, entrada in manifesto["paises"].items():
        contagens = (
            _contagens_lacunas(diretorio_pais(raiz, pais) / "lacunas.csv")
            if raiz is not None
            else {"convocados": None, "presentes": None, "ausentes": None}
        )
        linhas.append({
            "pais": pais,
            **contagens,
            "aprovados": int(entrada.get("approved", 0)),
            "revisao_manual": int(entrada.get("review_required", 0)),
            "tentativas": int(entrada.get("attempts", 0)),
            "status": entrada.get("status", STATUS_PENDING),
        })
    resumo = pd.DataFrame(linhas).reindex(columns=list(COLUNAS_RESUMO))
    inteiros = [c for c in COLUNAS_RESUMO if c not in {"pais", "status"}]
    return resumo.astype({coluna: "Int64" for coluna in inteiros})


def mesclar_publicados(manifesto: dict[str, Any], raiz: Path) -> pd.DataFrame:
    """Concatena os snapshots já publicados, preservando o schema do dataset."""
    partes = []
    for pais, entrada in manifesto["paises"].items():
        if entrada.get("status") != STATUS_PUBLISHED:
            continue
        caminho = Path(entrada.get("output_path") or (diretorio_pais(raiz, pais) / nome_snapshot(pais, manifesto["edicao"])))
        if not caminho.exists():
            raise FileNotFoundError(f"snapshot publicado ausente: {caminho}")
        partes.append(pd.read_csv(caminho, low_memory=False))
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True)
