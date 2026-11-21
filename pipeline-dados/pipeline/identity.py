"""Matching conservador entre nomes de convocação e jogadores da base."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import normalizar_nome


def carregar_aliases(caminho: Path | None) -> dict[str, str]:
    if caminho is None or not caminho.exists():
        return {}
    aliases = pd.read_csv(caminho, dtype=str).fillna("")
    obrigatorias = {"nome_convocacao", "nome_base"}
    faltantes = obrigatorias - set(aliases.columns)
    if faltantes:
        raise ValueError(f"colunas ausentes no aliases: {', '.join(sorted(faltantes))}")
    return {
        normalizar_nome(row.nome_convocacao): normalizar_nome(row.nome_base)
        for row in aliases.itertuples(index=False)
        if row.nome_convocacao and row.nome_base
    }


def _indices_nomes(dataset: pd.DataFrame) -> dict[str, set[int]]:
    indices: dict[str, set[int]] = {}
    for coluna in ("short_name", "long_name"):
        for idx, nome in dataset[coluna].items():
            chave = normalizar_nome(nome)
            if chave:
                indices.setdefault(chave, set()).add(idx)
    return indices


def _mesma_data(base: object, convocacao: object) -> bool:
    base_iso = str(base or "")[:10]
    conv_iso = str(convocacao or "")[:10]
    return bool(base_iso) and base_iso == conv_iso


def _filtrar_por_dob(candidatos: list[int], dataset: pd.DataFrame, dob: str | None) -> list[int]:
    """Quando há data de nascimento, exige igualdade — senão o candidato é descartado.

    A base não tem `dob` nulo, então uma data que não confere significa outra pessoa.
    Sem essa exigência, nomes curtos casariam por engano (ex.: "Bento" com
    "Thales Bento Oleques").
    """
    if not dob or "dob" not in dataset.columns or not candidatos:
        return candidatos
    return [idx for idx in candidatos if _mesma_data(dataset.loc[idx, "dob"], dob)]


def encontrar_candidatos(
    nome: str,
    dataset: pd.DataFrame,
    aliases: dict[str, str] | None = None,
    dob: str | None = None,
) -> list[int]:
    """Casa por nome exato e, como fallback, por subconjunto de tokens do long_name.

    A base guarda o nome comum abreviado ("A. Sánchez") e o nome completo
    ("Alexis Alejandro Sánchez Sánchez"); a convocação costuma trazer o nome
    comum ("Alexis Sánchez"). O fallback aceita o candidato quando todos os
    tokens da convocação aparecem no long_name; nos dois caminhos, a data de
    nascimento é exigida quando disponível, para não casar homônimos.
    """
    indices = _indices_nomes(dataset)
    chave = normalizar_nome(nome)
    alvo = (aliases or {}).get(chave, chave)
    exatos = indices.get(alvo)
    if exatos:
        return sorted(_filtrar_por_dob(sorted(exatos), dataset, dob))

    tokens_alvo = set(alvo.split())
    if not tokens_alvo:
        return []
    candidatos = [
        idx
        for idx, nome_base in dataset["long_name"].items()
        if tokens_alvo <= set(normalizar_nome(nome_base).split())
    ]
    return sorted(_filtrar_por_dob(candidatos, dataset, dob))


def descobrir_lacunas(
    convocacoes: pd.DataFrame,
    dataset: pd.DataFrame,
    aliases: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Classifica cada convocado sem fazer fuzzy matching silencioso."""
    linhas = []
    for row in convocacoes.to_dict("records"):
        pais = row["pais"]
        recorte = dataset[dataset["nationality_name"].eq(pais)]
        candidatos = encontrar_candidatos(row["nome"], recorte, aliases, row.get("dob"))
        if not candidatos:
            status = "missing"
            indice = ""
            nome_base = ""
            sofifa_id = ""
        elif len(candidatos) > 1:
            status = "ambiguous"
            indice = "|".join(map(str, candidatos))
            nome_base = ""
            sofifa_id = ""
        else:
            status = "present"
            indice = str(candidatos[0])
            jogador = recorte.loc[candidatos[0]]
            nome_base = jogador["long_name"]
            sofifa_id = str(jogador["sofifa_id"])
        linhas.append({
            **row,
            "status": status,
            "indice_base": indice,
            "nome_base": nome_base,
            "sofifa_id": sofifa_id,
        })
    return pd.DataFrame(linhas)
