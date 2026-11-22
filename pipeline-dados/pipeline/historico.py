"""Metadados da camada histórica (lendas por seleção).

A camada histórica reaproveita o mesmo `pacote`/`proposta`/`materializar` dos
convocados, mas os registros precisam de rastreio diferente e de uma convenção
de idade. Aplicar isso aqui, e não no prompt do pesquisador, mantém a
transformação determinística e auditável.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .config import ATRIBUTOS_GK, ATRIBUTOS_LINHA
from .research import chave_jogador

IDADE_PICO = 27
ORIGEM_REGISTRO = "historico_estimado"
FONTE_ATRIBUTOS = "inferencia_llm_calibrada_historico"
VALIDACAO_VIA = "wikidata"
FONTE_ATRIBUTOS_REAL = "ea_fc_icon"
COLUNAS_ATRIBUTOS = ("overall",) + ATRIBUTOS_LINHA + ATRIBUTOS_GK


def carregar_atributos_reais(caminhos: Iterable[Path | str]) -> dict[str, dict[str, int]]:
    """Extrai as notas REAIS (EA FC Icon) dos CSVs históricos anteriores.

    Devolve um mapa chave_jogador -> atributos, usado como override na
    materialização, já que o percentil calibrado não tem como representar um
    jogador acima da escala da base.
    """
    reais: dict[str, dict[str, int]] = {}
    for caminho in caminhos:
        df = pd.read_csv(caminho, dtype=str, low_memory=False).fillna("")
        if "fonte_atributos" not in df.columns:
            continue
        for row in df[df["fonte_atributos"].eq(FONTE_ATRIBUTOS_REAL)].to_dict("records"):
            valores = {}
            for coluna in COLUNAS_ATRIBUTOS:
                bruto = str(row.get(coluna, "")).strip()
                if bruto:
                    try:
                        valores[coluna] = int(float(bruto))
                    except ValueError:
                        continue
            if valores:
                reais[chave_jogador(row["nationality_name"], row["short_name"], row.get("dob"))] = valores
    return reais


def marcar_propostas(
    propostas: list[dict[str, Any]],
    idade_pico: int = IDADE_PICO,
    atributos_reais: dict[str, dict[str, int]] | None = None,
) -> list[dict[str, Any]]:
    """Aplica os metadados da camada histórica às propostas.

    A idade de pico é uma convenção de modelagem, não um dado observado: comparar
    eras é impreciso e a idade em 2024 (referência da base) seria absurda para um
    jogador nascido em 1960. `setdefault` mantém a operação idempotente.
    """
    reais = atributos_reais or {}
    for proposta in propostas:
        proposta.setdefault("age", idade_pico)
        proposta["is_historico"] = True
        proposta["origem_registro"] = ORIGEM_REGISTRO
        proposta["fonte_atributos"] = FONTE_ATRIBUTOS
        proposta["validacao_via"] = VALIDACAO_VIA
        override = reais.get(chave_jogador(proposta["pais"], proposta["nome"], proposta.get("dob")))
        if override:
            proposta["atributos_override"] = override
            proposta["fonte_atributos"] = FONTE_ATRIBUTOS_REAL
    return propostas


def marcar_arquivo(
    caminho: Path | str,
    idade_pico: int = IDADE_PICO,
    atributos_reais: dict[str, dict[str, int]] | None = None,
) -> int:
    """Lê uma resposta JSON, aplica os metadados históricos e regrava. Retorna o total."""
    caminho = Path(caminho)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if isinstance(dados, dict):
        dados = dados.get("jogadores", [])
    marcar_propostas(dados, idade_pico, atributos_reais)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(dados)
