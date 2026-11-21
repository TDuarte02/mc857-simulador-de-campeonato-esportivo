"""Converte propostas aprovadas em linhas compatíveis com players_22.csv."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from .calibration import converter_percentil, grupo_da_proposta, pool_por_posicao
from .config import ATRIBUTOS_GK, ATRIBUTOS_LINHA, COLUNAS_RASTREIO
from .research import chave_jogador


def _carregar_registry(caminho: Path) -> pd.DataFrame:
    colunas = ["sofifa_id", "player_key", "nome", "pais", "dob", "tipo_registro"]
    if not caminho.exists():
        return pd.DataFrame(columns=colunas)
    return pd.read_csv(caminho, dtype={"sofifa_id": "Int64", "player_key": str}).reindex(columns=colunas)


def alocar_id(caminho: Path, proposta: dict) -> int:
    registry = _carregar_registry(caminho)
    key = chave_jogador(proposta["pais"], proposta["nome"], proposta.get("dob"))
    existentes = registry[registry["player_key"] == key]
    if not existentes.empty:
        return int(existentes.iloc[0]["sofifa_id"])
    negativos = pd.to_numeric(registry["sofifa_id"], errors="coerce").dropna()
    proximo = min(negativos.min(), 0) - 1 if not negativos.empty else -1
    nova = pd.DataFrame([{
        "sofifa_id": int(proximo), "player_key": key, "nome": proposta["nome"],
        "pais": proposta["pais"], "dob": proposta.get("dob", ""),
        "tipo_registro": "convocado_2024_adicionado",
    }])
    caminho.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([registry, nova], ignore_index=True).to_csv(caminho, index=False, quoting=csv.QUOTE_MINIMAL)
    return int(proximo)


def _idade(dob: str | None, data_referencia: str) -> int | None:
    if not dob:
        return None
    nascimento = pd.Timestamp(dob)
    referencia = pd.Timestamp(data_referencia)
    return referencia.year - nascimento.year - ((referencia.month, referencia.day) < (nascimento.month, nascimento.day))


def materializar_linha(
    proposta: dict,
    dataset: pd.DataFrame,
    colunas_dataset: list[str],
    data_referencia: str,
    registry: Path,
) -> dict:
    grupo = grupo_da_proposta(proposta["posicao"])
    pool = pool_por_posicao(dataset, proposta["pais"], grupo)
    percentis = proposta["percentis"]
    atributos = {}
    colunas = ("overall",) + (ATRIBUTOS_GK if grupo == "GK" else ATRIBUTOS_LINHA)
    for coluna in colunas:
        atributos[coluna] = converter_percentil(pool, coluna, percentis.get(coluna))

    linha = {coluna: None for coluna in colunas_dataset}
    linha.update({
        "sofifa_id": alocar_id(registry, proposta),
        "short_name": proposta["nome"],
        "long_name": proposta["nome"],
        "player_positions": proposta["posicao"],
        "overall": atributos.get("overall"),
        "potential": atributos.get("overall"),
        "age": _idade(proposta.get("dob"), data_referencia),
        "dob": proposta.get("dob"),
        "height_cm": proposta.get("height_cm"),
        "weight_kg": proposta.get("weight_kg"),
        "nationality_name": proposta["pais"],
        "club_name": proposta.get("club_name"),
        "league_name": proposta.get("league_name"),
        "preferred_foot": proposta.get("preferred_foot"),
        "weak_foot": proposta.get("weak_foot"),
        "skill_moves": proposta.get("skill_moves"),
    })
    for coluna in ATRIBUTOS_LINHA + ATRIBUTOS_GK:
        linha[coluna] = atributos.get(coluna) if coluna in atributos else None
    linha.update({
        "is_historico": False,
        "origem_registro": "convocado_2024_adicionado",
        "fonte_atributos": "inferencia_llm_calibrada",
        "fonte_validacao": "pesquisa_web_convocacao",
        "observacao": proposta.get("observacao", ""),
        "validacao_via": "convocacao_copa_america",
        "data_referencia": data_referencia,
        "status_validacao": proposta.get("status", "review_required"),
        "confianca": proposta.get("confianca"),
    })
    return linha


def materializar(propostas: list[dict], dataset: pd.DataFrame, data_referencia: str, registry: Path) -> pd.DataFrame:
    colunas = list(dataset.columns)
    resultado = [materializar_linha(p, dataset, colunas, data_referencia, registry) for p in propostas]
    return pd.DataFrame(resultado).reindex(columns=colunas + [c for c in COLUNAS_RASTREIO if c not in colunas])
