import unittest
from pathlib import Path

import pandas as pd

from pipeline.catalogo import carregar_todas_convocacoes, resumo_catalogo
from pipeline.config import SELECOES_COPA_AMERICA_2024
from pipeline.imputacao import CAMPOS_MOTOR
from pipeline.validation import validar_catalogo

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / "artefatos/jogadores_copa_america_2024_filtrado.csv"
CONVOCACOES = RAIZ / "artefatos/convocacoes"
COTAS = {"GK": 3, "CB": 8, "CM": 8, "ST": 7}


def _catalogo(pais="Chile"):
    """Um catálogo mínimo válido: 3 GK, 8 DEF, 8 MID e 7 ATT, todos convocados."""
    linhas = []
    for posicao, n in COTAS.items():
        for _ in range(n):
            sofifa_id = len(linhas) + 1
            linha = {c: 70 for c in CAMPOS_MOTOR}
            if posicao == "GK":
                linha.update(pace=None, shooting=None, passing=None, dribbling=None, defending=None, physic=None)
            linha.update(
                sofifa_id=sofifa_id, short_name=f"J{sofifa_id}", nationality_name=pais, player_positions=posicao,
                person_key=str(sofifa_id), is_convocado_2024=True,
            )
            linhas.append(linha)
    convocacoes = pd.DataFrame([{"pais": pais, "nome": f"J{i + 1}"} for i in range(len(linhas))])
    return pd.DataFrame(linhas), convocacoes


class ValidarCatalogoTest(unittest.TestCase):
    def test_catalogo_valido(self):
        catalogo, convocacoes = _catalogo()
        self.assertEqual(validar_catalogo(catalogo, convocacoes, CAMPOS_MOTOR), [])

    def test_campo_do_motor_vazio_ou_fora_da_escala(self):
        catalogo, convocacoes = _catalogo()
        catalogo.loc[5, "movement_agility"] = None
        catalogo.loc[6, "power_stamina"] = 101
        erros = validar_catalogo(catalogo, convocacoes, CAMPOS_MOTOR)
        self.assertEqual(len(erros), 2)
        self.assertIn("movement_agility vazio", erros[0])
        self.assertIn("power_stamina fora de [0, 100]", erros[1])

    def test_ids_repetidos(self):
        catalogo, convocacoes = _catalogo()
        catalogo.loc[1, "sofifa_id"] = 1
        self.assertTrue(any("id repetido 1" in e for e in validar_catalogo(catalogo, convocacoes, CAMPOS_MOTOR)))

    def test_cota_conta_pessoas_distintas(self):
        catalogo, convocacoes = _catalogo()
        # duas versões da mesma pessoa no ataque: 6 pessoas, abaixo do mínimo de 7
        catalogo.loc[catalogo.player_positions.eq("ST").idxmax(), "person_key"] = catalogo["person_key"].iloc[-1]
        erros = validar_catalogo(catalogo, convocacoes, CAMPOS_MOTOR)
        self.assertEqual(erros, ["Chile: 6 pessoa(s) em ATT, mínimo 7"])

    def test_todo_convocado_listado_esta_presente(self):
        catalogo, convocacoes = _catalogo()
        catalogo.loc[0, "is_convocado_2024"] = False
        erros = validar_catalogo(catalogo, convocacoes, CAMPOS_MOTOR)
        self.assertEqual(erros, ["Chile: 25 convocado(s) no catálogo, 26 listado(s)"])


class CatalogoPublicadoTest(unittest.TestCase):
    """O arquivo regenerado (`build-catalog`) e versionado passa nas validações."""

    @classmethod
    def setUpClass(cls):
        cls.catalogo = pd.read_csv(CATALOGO, low_memory=False)
        cls.convocacoes = carregar_todas_convocacoes(CONVOCACOES)

    def test_passa_em_todas_as_validacoes(self):
        self.assertEqual(validar_catalogo(self.catalogo, self.convocacoes, CAMPOS_MOTOR), [])

    def test_todas_as_selecoes_e_convocados(self):
        resumo = resumo_catalogo(self.catalogo).set_index("pais")
        self.assertEqual(set(resumo.index), set(SELECOES_COPA_AMERICA_2024))
        self.assertEqual(resumo.loc["Jamaica", "convocados"], 25)
        self.assertEqual(resumo.loc["Panama", "convocados"], 25)
        self.assertEqual(int(resumo["convocados"].sum()), 16 * 26 - 2)

    def test_messi_e_convocado_da_argentina(self):
        messi = self.catalogo[self.catalogo.short_name.eq("L. Messi")]
        self.assertEqual(messi[["nationality_name", "is_convocado_2024"]].values.tolist(), [["Argentina", True]])

    def test_versoes_2024_e_lenda_dividem_a_pessoa_mas_nao_o_id(self):
        turner = self.catalogo[self.catalogo.short_name.eq("Matt Turner")]
        self.assertEqual(len(turner), 2)
        self.assertEqual(turner["person_key"].nunique(), 1)
        self.assertEqual(turner["sofifa_id"].nunique(), 2)

    def test_linhas_estimadas_sao_marcadas(self):
        enriquecidas = self.catalogo["camada"].ne("base_22")
        marcadas = self.catalogo["atributos_imputados"].fillna("").ne("")
        self.assertTrue((enriquecidas == marcadas).all())


if __name__ == "__main__":
    unittest.main()
