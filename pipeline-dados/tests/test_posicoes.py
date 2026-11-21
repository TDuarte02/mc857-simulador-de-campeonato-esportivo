import unittest

import numpy as np
import pandas as pd

from pipeline.posicoes import (
    COLUNAS_POSICAO,
    CODIGOS_VALIDOS,
    formatar_posicoes,
    injetar_secundarias,
    normalizar_codigo,
    parse_valor,
    posicoes_plausiveis,
    prever_colunas,
    treinar_modelo,
    validar_secundarias,
)


class PosicoesTest(unittest.TestCase):
    def test_parse_valor_do_formato_fifa(self):
        self.assertEqual(parse_valor("90+2"), 92)
        self.assertEqual(parse_valor("85"), 85)
        self.assertIsNone(parse_valor(""))
        self.assertIsNone(parse_valor(None))
        self.assertIsNone(parse_valor("abc"))

    def test_normalizacao_da_curadoria(self):
        self.assertEqual(normalizar_codigo("AM"), "CAM")
        self.assertEqual(normalizar_codigo("dm"), "CDM")
        self.assertEqual(normalizar_codigo("CB"), "CB")     # já válido, não muda

    def test_todos_os_codigos_validos_existem_como_coluna(self):
        for codigo in CODIGOS_VALIDOS:
            self.assertIn(codigo.lower(), COLUNAS_POSICAO)

    def test_validar_secundarias_rejeita_invalido_repetido_e_excesso(self):
        _, erros = validar_secundarias("ST", ["XX"])
        self.assertTrue(any("inválido" in e for e in erros))
        _, erros = validar_secundarias("ST", ["ST"])
        self.assertTrue(any("repete a principal" in e for e in erros))
        limpas, erros = validar_secundarias("ST", ["CF", "LW", "RW"])
        self.assertEqual(limpas, ["CF", "LW"])
        self.assertTrue(any("mais de 2" in e for e in erros))

    def test_goleiro_nunca_tem_secundaria(self):
        limpas, erros = validar_secundarias("GK", ["CB"])
        self.assertEqual(limpas, [])
        self.assertTrue(any("goleiro" in e for e in erros))

    def test_posicoes_plausiveis_normaliza_a_principal(self):
        self.assertEqual(posicoes_plausiveis("AM", ["ST"]), ["CAM", "ST"])
        self.assertEqual(formatar_posicoes("ST", ["CF", "LW"]), "ST, CF, LW")

    def _dataset(self):
        # 200 jogadores sintéticos: ST com st alto, cb baixo; e um CB.
        rng = np.random.default_rng(0)
        linhas = []
        for i in range(120):
            ov = 70 + (i % 20)
            linhas.append({"overall": ov, "pace": ov, "shooting": ov, "passing": ov - 5, "dribbling": ov, "defending": ov - 30, "physic": ov - 5,
                           "st": str(ov), "cb": str(ov - 25), "cam": str(ov - 5), "gk": str(ov - 50), "cm": str(ov - 8), "lw": str(ov - 2),
                           "cf": str(ov - 1), "rw": str(ov - 2), "ls": None, "rs": None, "lf": None, "rf": None, "lam": None, "ram": None, "lm": None,
                           "lcm": None, "rcm": None, "rm": None, "lwb": None, "ldm": None, "cdm": None, "rdm": None, "rwb": None,
                           "lb": None, "lcb": None, "rcb": None, "rb": None})
        for i in range(120):
            ov = 65 + (i % 25)
            linhas.append({"overall": ov, "pace": ov - 15, "shooting": ov - 25, "passing": ov - 10, "dribbling": ov - 15, "defending": ov, "physic": ov,
                           "cb": str(ov), "st": str(ov - 25), "cam": str(ov - 12), "gk": str(ov - 50), "cm": str(ov - 6), "lw": str(ov - 20),
                           "cf": str(ov - 22), "rw": str(ov - 22), "ls": None, "rs": None, "lf": None, "rf": None, "lam": None, "ram": None, "lm": None,
                           "lcm": None, "rcm": None, "rm": None, "lwb": None, "ldm": None, "cdm": None, "rdm": None, "rwb": None,
                           "lb": None, "lcb": None, "rcb": None, "rb": None})
        return pd.DataFrame(linhas)

    def test_prever_preenche_so_as_posicoes_plausiveis(self):
        modelo = treinar_modelo(self._dataset())
        atributos = {"overall": 90, "pace": 90, "shooting": 90, "passing": 85, "dribbling": 90, "defending": 60, "physic": 85}
        previsoes = prever_colunas(modelo, atributos, "ST", ["CF"])
        self.assertIsNotNone(previsoes["st"])
        self.assertIsNotNone(previsoes["cf"])
        for coluna in COLUNAS_POSICAO:
            if coluna not in {"st", "cf"}:
                self.assertIsNone(previsoes[coluna], f"{coluna} deveria ficar vazio")

    def test_um_jogador_com_tres_posicoes_tem_tres_colunas(self):
        modelo = treinar_modelo(self._dataset())
        atributos = {"overall": 80, "pace": 80, "shooting": 80, "passing": 80, "dribbling": 80, "defending": 80, "physic": 80}
        previsoes = prever_colunas(modelo, atributos, "ST", ["CF", "LW"])
        preenchidas = [c for c, v in previsoes.items() if v is not None]
        self.assertEqual(sorted(preenchidas), ["cf", "lw", "st"])

    def test_previsao_respeita_a_faixa_e_ordena_corretamente(self):
        modelo = treinar_modelo(self._dataset())
        craque = {"overall": 92, "pace": 92, "shooting": 92, "passing": 87, "dribbling": 92, "defending": 62, "physic": 87}
        fraco = {"overall": 70, "pace": 70, "shooting": 70, "passing": 65, "dribbling": 70, "defending": 40, "physic": 65}
        alto = prever_colunas(modelo, craque, "ST")["st"]
        baixo = prever_colunas(modelo, fraco, "ST")["st"]
        self.assertGreater(alto, baixo)          # monótono em relação ao nível
        self.assertTrue(1 <= alto <= 99)

    def test_injetar_secundarias_descarta_repeticao_da_principal(self):
        propostas = [{"nome": "X", "dob": "1990-01-01", "posicao": "ST"}]
        respostas = [{"nome": "X", "dob": "1990-01-01", "posicoes_secundarias": ["CF", "ST"]}]
        self.assertEqual(injetar_secundarias(propostas, respostas), 1)
        self.assertEqual(propostas[0]["posicoes_secundarias"], ["CF"])

    def test_injetar_secundarias_nao_marca_quem_nao_tem(self):
        propostas = [{"nome": "Y", "dob": "1990-01-01", "posicao": "ST"}]
        self.assertEqual(injetar_secundarias(propostas, [{"nome": "Y", "dob": "1990-01-01", "posicoes_secundarias": []}]), 0)
        self.assertNotIn("posicoes_secundarias", propostas[0])

    def test_injetar_secundarias_ignora_jogador_desconhecido(self):
        propostas = [{"nome": "Z", "dob": "1990-01-01", "posicao": "ST"}]
        self.assertEqual(injetar_secundarias(propostas, [{"nome": "Outro", "dob": "1990-01-01", "posicoes_secundarias": ["CF"]}]), 0)

    def test_goleiro_so_tem_a_coluna_gk(self):
        modelo = treinar_modelo(self._dataset())
        atributos = {"overall": 85, "pace": 0, "shooting": 0, "passing": 0, "dribbling": 0, "defending": 0, "physic": 0}
        previsoes = prever_colunas(modelo, atributos, "GK", ["CB"])   # secundária de GK deve ser ignorada
        self.assertIsNotNone(previsoes["gk"])
        self.assertIsNone(previsoes["cb"])


if __name__ == "__main__":
    unittest.main()
