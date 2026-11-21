"""Geração de pacotes de pesquisa para revisão ou uso com um LLM."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .calibration import amostra_representativa, estatisticas_calibracao, grupo_da_proposta
from .config import COLUNAS_ESCALACAO
from .config import normalizar_nome

PROMPT_VERSION = "convocados-v1"


def gerar_pacote(
    dataset: pd.DataFrame,
    lacunas: pd.DataFrame,
    pais: str,
    data_referencia: str,
    escalacao: pd.DataFrame | None = None,
) -> dict:
    jogadores = lacunas[(lacunas["pais"] == pais) & (lacunas["status"] == "missing")].copy()
    grupos = {}
    for posicao in jogadores["posicao"].drop_duplicates():
        grupo = grupo_da_proposta(posicao)
        grupos[grupo] = {
            "estatisticas": estatisticas_calibracao(dataset, pais, grupo),
            "amostra": amostra_representativa(dataset, pais, grupo),
        }
    entradas = []
    for row in jogadores.to_dict("records"):
        entrada = {
            "nome": row["nome"],
            "pais": row["pais"],
            "posicao": row["posicao"],
            "fonte_convocacao": row.get("fonte_url", ""),
            "titular_ultima_partida": str(row.get("titular_ultima_partida", "")).lower() == "true",
        }
        for opcional in ("dob", "clube", "numero"):
            valor = row.get(opcional)
            if isinstance(valor, str) and valor.strip():
                entrada[opcional] = valor.strip()
        entradas.append(entrada)
    titulares = []
    if escalacao is not None and not escalacao.empty:
        titulares = escalacao[escalacao["pais"].eq(pais)].to_dict("records")
        titulares = [{chave: valor for chave, valor in linha.items() if chave in COLUNAS_ESCALACAO} for linha in titulares]
    return {
        "prompt_version": PROMPT_VERSION,
        "pais": pais,
        "data_referencia": data_referencia,
        "jogadores": entradas,
        "ultima_escalacao": titulares,
        "calibracao": grupos,
        "instrucoes": {
            "titularidade_e_convocacao_sao_dados_distintos": True,
            "colunas_escalacao": list(COLUNAS_ESCALACAO),
            "retorno": "JSON válido, sem markdown",
            "usar_percentis": True,
            "nao_inventar": True,
            "fontes_obrigatorias": True,
        },
    }


def escrever_pacote(pacote: dict, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(pacote, ensure_ascii=False, indent=2), encoding="utf-8")


def chave_jogador(pais: str, nome: str, dob: str | None = None) -> str:
    return "|".join(filter(None, (normalizar_nome(pais), normalizar_nome(nome), dob or "")))
