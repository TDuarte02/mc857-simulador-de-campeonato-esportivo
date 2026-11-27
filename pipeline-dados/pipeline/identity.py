"""Matching conservador entre nomes de convocação e jogadores da base."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import normalizar_nome

CAMADA_BASE = "base_22"
CAMADA_CONVOCADO = "convocado_2024"
CAMADA_HISTORICO = "historico"


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
    nascimento é exigida quando disponível, para não casar homônimos. Se o
    nome exato só casa com outra pessoa (data diferente), o fallback também é
    tentado: "Andrés Cubas" (1996-05-22) não é a lenda homônima de outra data,
    e sim "Adrián Andrés Cubas".
    """
    indices = _indices_nomes(dataset)
    chave = normalizar_nome(nome)
    alvo = (aliases or {}).get(chave, chave)
    exatos = indices.get(alvo)
    if exatos:
        confirmados = _filtrar_por_dob(sorted(exatos), dataset, dob)
        if confirmados:
            return sorted(confirmados)
        # O nome exato era de outra pessoa (data diferente): tenta os tokens.

    tokens_alvo = set(alvo.split())
    if not tokens_alvo:
        return []
    candidatos = [
        idx
        for idx, nome_base in dataset["long_name"].items()
        if tokens_alvo <= set(normalizar_nome(nome_base).split())
    ]
    return sorted(_filtrar_por_dob(candidatos, dataset, dob))


def _preferir_camada(candidatos: list[int], recorte: pd.DataFrame) -> list[int]:
    """Entre candidatos de camadas diferentes, a pesquisa de 2024 vence a base FIFA 22."""
    if "camada" not in recorte.columns or len(candidatos) < 2:
        return candidatos
    pesquisados = [idx for idx in candidatos if recorte.loc[idx, "camada"] == CAMADA_CONVOCADO]
    return pesquisados or candidatos


def descobrir_lacunas(
    convocacoes: pd.DataFrame,
    dataset: pd.DataFrame,
    aliases: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Classifica cada convocado sem fazer fuzzy matching silencioso.

    Com a coluna `camada` (o pool combinado), a camada histórica fica de fora —
    uma lenda nunca é o convocado de 2024 — e, entre a base e a pesquisa de
    2024, a pesquisa é preferida.
    """
    linhas = []
    for row in convocacoes.to_dict("records"):
        pais = row["pais"]
        recorte = dataset[dataset["nationality_name"].eq(pais)]
        if "camada" in recorte.columns:
            recorte = recorte[recorte["camada"].ne(CAMADA_HISTORICO)]
        candidatos = encontrar_candidatos(row["nome"], recorte, aliases, row.get("dob"))
        candidatos = _preferir_camada(candidatos, recorte)
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


def exigir_convocados(lacunas: pd.DataFrame) -> None:
    """Falha, com um relatório, se algum convocado ficou ambíguo ou sem par no pool."""
    problemas = lacunas[lacunas["status"].ne("present")]
    if problemas.empty:
        repetidos = lacunas[lacunas["indice_base"].duplicated(keep=False)]
        if repetidos.empty:
            return
        linhas = [f"  {r.pais}: {r.nome} -> linha {r.indice_base} (mesma linha de outro convocado)" for r in repetidos.itertuples()]
        raise ValueError("convocados casados com a mesma linha do pool:\n" + "\n".join(linhas))
    linhas = [
        f"  {r.status}: {r.pais}: {r.nome} (dob {getattr(r, 'dob', '') or '?'})"
        + (f" -> candidatos {r.indice_base}" if r.indice_base else "")
        for r in problemas.itertuples()
    ]
    raise ValueError(
        f"{len(problemas)} convocado(s) sem correspondência única no pool:\n" + "\n".join(linhas)
    )


def atribuir_pessoas(pool: pd.DataFrame) -> pd.Series:
    """`person_key` de cada linha: a mesma para as versões 2024 e lenda de uma pessoa (D8).

    A chave é o `sofifa_id` da versão atual (base FIFA 22 ou pesquisa de 2024).
    Cada lenda é casada com as linhas atuais da mesma seleção pelas regras do
    matching de convocados (nome exato ou tokens do long_name, data de nascimento
    obrigatória); sem par único, a lenda é uma pessoa própria.
    """
    chaves = pool["sofifa_id"].astype("Int64").astype(str)
    if "camada" not in pool.columns:
        return chaves
    for pais, recorte in pool.groupby("nationality_name", sort=False):
        atuais = recorte[recorte["camada"].ne(CAMADA_HISTORICO)]
        lendas = recorte[recorte["camada"].eq(CAMADA_HISTORICO)]
        if atuais.empty or lendas.empty:
            continue
        for idx, lenda in lendas.iterrows():
            dob = str(lenda.get("dob") or "")[:10] or None
            if dob is None:
                continue  # sem data não há como confirmar que é a mesma pessoa
            candidatos = _preferir_camada(
                encontrar_candidatos(lenda["short_name"], atuais, dob=dob), atuais
            )
            if len(candidatos) == 1:
                chaves.loc[idx] = chaves.loc[candidatos[0]]
    return chaves
