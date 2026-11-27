"""Catálogo final: do pool combinado ao `jogadores_copa_america_2024_filtrado.csv`.

Passos, nesta ordem:

1. ids das linhas enriquecidas vêm do registro versionado (lendas que dividiam o
   id com a versão 2024 ganham um id novo); em seguida entram as correções de
   data de nascimento (`correcoes.py`), antes de tudo que usa a data;
2. cada convocado listado em `convocacoes/<pais>.csv` é casado com o pool
   (`identity.descobrir_lacunas`); ambíguo ou ausente interrompe a execução;
3. `is_convocado_2024` e `person_key` (versões 2024 e lenda da mesma pessoa);
4. filtro de praticabilidade, que sempre mantém os convocados;
5. imputação dos atributos do motor que faltam (D5);
6. validação do catálogo; qualquer erro interrompe a execução.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import SELECOES_COPA_AMERICA_2024, grupo_posicao, slug
from .correcoes import aplicar_datas_nascimento
from .filtro import COTAS_PADRAO, filtrar_pool
from .identity import atribuir_pessoas, descobrir_lacunas, exigir_convocados
from .imputacao import CAMPOS_MOTOR, COLUNA_IMPUTADOS, imputar, treinar_imputacao
from .io import carregar_convocacoes
from .registry import aplicar_registry
from .validation import validar_catalogo

COLUNA_CONVOCADO = "is_convocado_2024"
COLUNA_PESSOA = "person_key"


@dataclass
class Catalogo:
    jogadores: pd.DataFrame
    convocacoes: pd.DataFrame
    erros: list[str] = field(default_factory=list)


def carregar_todas_convocacoes(diretorio: Path, selecoes: tuple[str, ...] = SELECOES_COPA_AMERICA_2024) -> pd.DataFrame:
    """Uma convocação por seleção: `<diretorio>/<slug do país>.csv`."""
    return pd.concat(
        [carregar_convocacoes(diretorio / f"{slug(pais)}.csv") for pais in selecoes],
        ignore_index=True,
    )


def construir_catalogo(
    pool: pd.DataFrame,
    base: pd.DataFrame,
    convocacoes: pd.DataFrame,
    registry: Path,
    aliases: dict[str, str] | None = None,
    cotas: dict[str, int] | None = None,
    correcoes: pd.DataFrame | None = None,
) -> Catalogo:
    selecoes = list(SELECOES_COPA_AMERICA_2024)
    df = pool[pool["nationality_name"].isin(selecoes)].reset_index(drop=True)
    df = aplicar_registry(df, registry)
    if correcoes is not None:  # depois do registro: a chave dele inclui a data
        df = aplicar_datas_nascimento(df, correcoes)

    lacunas = descobrir_lacunas(convocacoes, df, aliases)
    exigir_convocados(lacunas)
    casados = {int(indice) for indice in lacunas["indice_base"]}
    df[COLUNA_CONVOCADO] = df.index.isin(casados)
    df[COLUNA_PESSOA] = atribuir_pessoas(df)

    filtrado = filtrar_pool(df, cotas or COTAS_PADRAO, selecoes)
    filtrado = imputar(filtrado, treinar_imputacao(base))
    for campo in CAMPOS_MOTOR:  # inteiros, sem o ".0" das colunas com vazios
        filtrado[campo] = pd.to_numeric(filtrado[campo]).round().astype("Int64")
    filtrado = filtrado[[*df.columns, COLUNA_IMPUTADOS]]
    return Catalogo(filtrado, convocacoes, validar_catalogo(filtrado, convocacoes, CAMPOS_MOTOR))


def resumo_catalogo(catalogo: pd.DataFrame) -> pd.DataFrame:
    """Por seleção: convocados, lendas, total e pessoas distintas por setor."""
    df = catalogo.assign(_setor=catalogo["player_positions"].map(grupo_posicao))
    linhas = []
    for pais, recorte in df.groupby("nationality_name"):
        linha = {
            "pais": pais,
            "convocados": int(recorte[COLUNA_CONVOCADO].sum()),
            "lendas": int(recorte["camada"].eq("historico").sum()),
            "total": len(recorte),
        }
        for setor in ("GK", "DEF", "MID", "ATT"):
            linha[setor] = int(recorte.loc[recorte["_setor"].eq(setor), COLUNA_PESSOA].nunique())
        linhas.append(linha)
    return pd.DataFrame(linhas)
