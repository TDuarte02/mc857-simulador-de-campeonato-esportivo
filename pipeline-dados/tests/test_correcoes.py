from pathlib import Path

import pandas as pd
import pytest

from pipeline.correcoes import CORRECOES_PADRAO, aplicar_datas_nascimento, carregar_correcoes

ARTEFATOS = Path(__file__).resolve().parents[1] / "artefatos"


def _pool():
    return pd.DataFrame(
        {
            "sofifa_id": [222429, -448, -71],
            "short_name": ["A. Cubas", "Andres Cubas", "Edison Flores"],
            "dob": ["1996-05-22", "1996-05-11", "1994-05-15"],
        }
    )


def _correcoes(**colunas):
    base = {"sofifa_id": ["222429"], "dob": ["1996-05-11"], "fonte_url": ["https://x"], "observacao": [""]}
    return pd.DataFrame({**base, **colunas})


def test_corrige_so_a_linha_indicada():
    corrigido = aplicar_datas_nascimento(_pool(), _correcoes())

    assert corrigido["dob"].tolist() == ["1996-05-11", "1996-05-11", "1994-05-15"]


def test_nao_altera_o_pool_original():
    pool = _pool()
    aplicar_datas_nascimento(pool, _correcoes())

    assert pool.loc[0, "dob"] == "1996-05-22"


def test_id_inexistente_interrompe():
    with pytest.raises(ValueError, match="0 linha"):
        aplicar_datas_nascimento(_pool(), _correcoes(sofifa_id=["999"]))


def test_correcao_sem_fonte_e_recusada(tmp_path):
    arquivo = tmp_path / "datas.csv"
    _correcoes(fonte_url=[""]).to_csv(arquivo, index=False)

    with pytest.raises(ValueError, match="sem fonte"):
        carregar_correcoes(arquivo)


def test_sem_arquivo_nao_ha_correcoes(tmp_path):
    assert carregar_correcoes(tmp_path / "nao_existe.csv").empty


def test_arquivo_versionado_tem_fonte_para_cada_correcao():
    correcoes = carregar_correcoes(CORRECOES_PADRAO)

    assert set(correcoes["sofifa_id"]) == {"222429", "-71"}


def test_catalogo_real_liga_cubas_e_flores_as_suas_lendas():
    catalogo = pd.read_csv(ARTEFATOS / "jogadores_copa_america_2024_filtrado.csv", dtype=str)

    for atual, lenda in (("222429", "-448"), ("-71", "-484")):
        chaves = catalogo.set_index("sofifa_id").loc[[atual, lenda], "person_key"]
        assert chaves.nunique() == 1, (atual, lenda, chaves.tolist())
