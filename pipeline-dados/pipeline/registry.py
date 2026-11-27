"""Registro de IDs dos jogadores enriquecidos (ids negativos).

O registro (`artefatos/autoresearch/registry/player_ids.csv`) é versionado: sem
ele, `alocar_id` recomeçaria em -1 num clone limpo e os ids deixariam de ser
reproduzíveis.

A chave inclui a **camada** (`convocado_2024` ou `historico`): a versão 2024 e
a versão lenda de uma mesma pessoa têm (país, nome, data de nascimento) iguais,
e uma chave sem a camada dava às duas o mesmo id.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from .research import chave_jogador

COLUNAS_REGISTRY = ["sofifa_id", "player_key", "nome", "pais", "dob", "tipo_registro"]
CAMADA_CONVOCADO = "convocado_2024"
CAMADA_HISTORICO = "historico"
TIPO_POR_CAMADA = {CAMADA_CONVOCADO: "convocado_2024_adicionado", CAMADA_HISTORICO: "historico_estimado"}


def camada_da_proposta(proposta: dict) -> str:
    historica = proposta.get("is_historico") or proposta.get("origem_registro") == TIPO_POR_CAMADA[CAMADA_HISTORICO]
    return CAMADA_HISTORICO if historica else CAMADA_CONVOCADO


def chave_registro(camada: str, pais: str, nome: str, dob: str | None = None) -> str:
    return f"{camada}|{chave_jogador(pais, nome, dob)}"


def _dob(valor: object) -> str | None:
    texto = "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor)
    return texto[:10] or None


def carregar_registry(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        return pd.DataFrame(columns=COLUNAS_REGISTRY)
    return pd.read_csv(caminho, dtype={"sofifa_id": "Int64", "player_key": str}).reindex(columns=COLUNAS_REGISTRY)


def _gravar(registry: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    registry.to_csv(caminho, index=False, quoting=csv.QUOTE_MINIMAL)


def alocar_id(caminho: Path, proposta: dict) -> int:
    """Id já registrado para a chave (camada, país, nome, dob) ou o próximo negativo livre."""
    registry = carregar_registry(caminho)
    camada = camada_da_proposta(proposta)
    key = chave_registro(camada, proposta["pais"], proposta["nome"], proposta.get("dob"))
    existentes = registry[registry["player_key"] == key]
    if not existentes.empty:
        return int(existentes.iloc[0]["sofifa_id"])
    negativos = pd.to_numeric(registry["sofifa_id"], errors="coerce").dropna()
    proximo = min(negativos.min(), 0) - 1 if not negativos.empty else -1
    nova = pd.DataFrame([{
        "sofifa_id": int(proximo), "player_key": key, "nome": proposta["nome"],
        "pais": proposta["pais"], "dob": proposta.get("dob", ""),
        "tipo_registro": proposta.get("origem_registro", TIPO_POR_CAMADA[camada]),
    }])
    _gravar(pd.concat([registry, nova], ignore_index=True), caminho)
    return int(proximo)


def reconstruir_registry(
    camadas: Iterable[tuple[str, pd.DataFrame]], caminho: Path
) -> pd.DataFrame:
    """Reconstrói o registro a partir dos ids que já estão nos artefatos publicados.

    `camadas` vem na ordem em que foram publicadas (2024 antes das lendas). Um id
    que já pertence a outra chave não é registrado de novo: essa linha fica sem
    registro e recebe um id novo no próximo `alocar_id`. Devolve essas linhas.
    """
    registradas: list[dict] = []
    dono: dict[int, str] = {}
    pendentes: list[dict] = []
    for camada, df in camadas:
        for row in df.to_dict("records"):
            sofifa_id = int(row["sofifa_id"])
            nome, pais, dob = row["short_name"], row["nationality_name"], _dob(row.get("dob"))
            key = chave_registro(camada, pais, nome, dob)
            if dono.get(sofifa_id, key) != key:
                pendentes.append({"camada": camada, "sofifa_id": sofifa_id, "player_key": key, "nome": nome, "pais": pais, "dob": dob or ""})
                continue
            if sofifa_id in dono:
                continue
            dono[sofifa_id] = key
            registradas.append({
                "sofifa_id": sofifa_id, "player_key": key, "nome": nome, "pais": pais,
                "dob": dob or "", "tipo_registro": TIPO_POR_CAMADA[camada],
            })
    registry = pd.DataFrame(registradas, columns=COLUNAS_REGISTRY).sort_values("sofifa_id", ascending=False)
    _gravar(registry, caminho)
    return pd.DataFrame(pendentes)


def aplicar_registry(pool: pd.DataFrame, caminho: Path, coluna_camada: str = "camada") -> pd.DataFrame:
    """Reescreve o `sofifa_id` das linhas enriquecidas a partir do registro.

    Linhas sem registro (as lendas que dividiam o id com a versão 2024) recebem
    um id novo de `alocar_id`, que também é gravado no registro.
    """
    df = pool.copy()
    enriquecidas = df[coluna_camada].isin((CAMADA_CONVOCADO, CAMADA_HISTORICO))
    for idx, row in df[enriquecidas].iterrows():
        proposta = {
            "pais": row["nationality_name"], "nome": row["short_name"], "dob": _dob(row.get("dob")) or "",
            "is_historico": row[coluna_camada] == CAMADA_HISTORICO,
        }
        if not proposta["dob"]:
            proposta.pop("dob")
        df.at[idx, "sofifa_id"] = alocar_id(caminho, proposta)
    return df
