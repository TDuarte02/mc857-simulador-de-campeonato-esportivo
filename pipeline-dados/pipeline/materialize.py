"""Converte propostas aprovadas em linhas compatíveis com players_22.csv."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from .calibration import banda_lenda, converter_percentil, grupo_da_proposta, pool_por_posicao
from .config import ATRIBUTOS_GK, ATRIBUTOS_LINHA, COLUNAS_RASTREIO
from .posicoes import formatar_posicoes, prever_colunas
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
        "tipo_registro": proposta.get("origem_registro", "convocado_2024_adicionado"),
    }])
    caminho.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([registry, nova], ignore_index=True).to_csv(caminho, index=False, quoting=csv.QUOTE_MINIMAL)
    return int(proximo)


def _aplicar_banda_lenda(atributos: dict, percentil_overall: object) -> dict:
    """Move as notas de um histórico para a banda de lenda, preservando o perfil.

    O percentil já ordena corretamente as lendas (0,95–0,99), mas o quantil da base
    não tem espaço acima do topo (~82–87). Aqui o `overall` vai para a banda
    declarada e os demais atributos são escalados na mesma proporção, mantendo a
    forma do perfil (um zagueiro continua defendendo mais do que finalizando).
    """
    alvo = banda_lenda(percentil_overall)
    calibrado = atributos.get("overall")
    if not alvo or not calibrado:
        return atributos
    fator = alvo / calibrado
    escalados = {
        coluna: (None if valor is None else max(1, min(99, round(valor * fator))))
        for coluna, valor in atributos.items()
    }
    escalados["overall"] = alvo
    return escalados


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
    modelo_posicoes: dict | None = None,
) -> dict:
    grupo = grupo_da_proposta(proposta["posicao"])
    # Histórico calibra na escala global; convocado atual, no pool do próprio país.
    escopo = None if proposta.get("is_historico") else proposta["pais"]
    pool = pool_por_posicao(dataset, escopo, grupo)
    percentis = proposta["percentis"]
    atributos = {}
    colunas = ("overall",) + (ATRIBUTOS_GK if grupo == "GK" else ATRIBUTOS_LINHA)
    for coluna in colunas:
        atributos[coluna] = converter_percentil(pool, coluna, percentis.get(coluna))
    # Nota real (ex.: EA FC Icon) tem precedência sobre o percentil calibrado.
    # Só aceita colunas válidas para o grupo, preservando a regra GK/linha.
    override = proposta.get("atributos_override") or {}
    for coluna, valor in override.items():
        if coluna in colunas and valor is not None:
            atributos[coluna] = int(valor)
    if proposta.get("is_historico") and not override:
        atributos = _aplicar_banda_lenda(atributos, percentis.get("overall"))
    # Posições: escreve 'PRINCIPAL, SEC1, SEC2' e preenche as colunas de posição
    # só nas posições plausíveis — as outras 24 ficam vazias de propósito.
    secundarias = proposta.get("posicoes_secundarias") or []
    colunas_posicao: dict[str, int | None] = {}
    if modelo_posicoes is not None:
        colunas_posicao = prever_colunas(modelo_posicoes, atributos, proposta["posicao"], secundarias)

    linha = {coluna: None for coluna in colunas_dataset}
    idade = proposta.get("age")
    linha.update({
        "sofifa_id": alocar_id(registry, proposta),
        "short_name": proposta["nome"],
        "long_name": proposta["nome"],
        "player_positions": formatar_posicoes(proposta["posicao"], secundarias),
        "overall": atributos.get("overall"),
        "potential": atributos.get("overall"),
        "age": int(idade) if idade is not None else _idade(proposta.get("dob"), data_referencia),
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
    for coluna, valor in colunas_posicao.items():
        if valor is not None:
            linha[coluna] = valor
    linha.update({
        "is_historico": bool(proposta.get("is_historico", False)),
        "origem_registro": proposta.get("origem_registro", "convocado_2024_adicionado"),
        "fonte_atributos": proposta.get("fonte_atributos", "inferencia_llm_calibrada"),
        "fonte_validacao": proposta.get("fonte_validacao", "pesquisa_web_convocacao"),
        "observacao": proposta.get("observacao", ""),
        "validacao_via": proposta.get("validacao_via", "convocacao_copa_america"),
        "data_referencia": data_referencia,
        "status_validacao": proposta.get("status", "review_required"),
        "confianca": proposta.get("confianca"),
    })
    return linha


def materializar(
    propostas: list[dict],
    dataset: pd.DataFrame,
    data_referencia: str,
    registry: Path,
    modelo_posicoes: dict | None = None,
) -> pd.DataFrame:
    colunas = list(dataset.columns)
    resultado = [
        materializar_linha(p, dataset, colunas, data_referencia, registry, modelo_posicoes)
        for p in propostas
    ]
    return pd.DataFrame(resultado).reindex(columns=colunas + [c for c in COLUNAS_RASTREIO if c not in colunas])
