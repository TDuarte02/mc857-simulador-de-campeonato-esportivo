import unittest

import numpy as np
import pandas as pd

from pipeline.config import ATRIBUTOS_GK, ATRIBUTOS_LINHA
from pipeline.imputacao import (
    ATRIBUTOS_DETALHADOS,
    COLUNA_IMPUTADOS,
    avaliar_imputacao,
    imputar,
    treinar_imputacao,
)


def _base(n=600, semente=1):
    """Base sintética em que cada atributo detalhado é uma função linear conhecida."""
    rng = np.random.default_rng(semente)
    linhas = []
    for i in range(n):
        goleiro = i % 5 == 0
        overall = int(rng.integers(50, 90))
        linha = {"player_positions": "GK" if goleiro else ("CB", "CM", "ST")[i % 3], "overall": overall}
        for c in ATRIBUTOS_LINHA:
            linha[c] = None if goleiro else int(rng.integers(30, 95))
        for c in ATRIBUTOS_GK:
            linha[c] = int(rng.integers(40, 90)) if goleiro else int(rng.integers(5, 15))
        for c in ATRIBUTOS_DETALHADOS:
            linha[c] = round(0.5 * overall + 20) if goleiro else round(0.3 * linha["pace"] + 0.4 * overall + 10)
        linhas.append(linha)
    return pd.DataFrame(linhas)


class ImputacaoTest(unittest.TestCase):
    def setUp(self):
        self.modelo = treinar_imputacao(_base())

    def test_so_os_vazios_sao_imputados_e_ficam_registrados(self):
        alvo = pd.DataFrame([
            {"player_positions": "ST", "overall": 80, **{c: 70 for c in ATRIBUTOS_LINHA}, **{c: None for c in ATRIBUTOS_GK},
             **{c: None for c in ATRIBUTOS_DETALHADOS}},
            {"player_positions": "GK", "overall": 80, **{c: None for c in ATRIBUTOS_LINHA}, **{c: 70 for c in ATRIBUTOS_GK},
             **{c: 55 for c in ATRIBUTOS_DETALHADOS}, "movement_agility": None},
        ])

        resultado = imputar(alvo, self.modelo)

        linha, goleiro = resultado.iloc[0], resultado.iloc[1]
        self.assertEqual(linha["movement_reactions"], round(0.3 * 70 + 0.4 * 80 + 10))
        self.assertEqual(linha[COLUNA_IMPUTADOS], ",".join((*ATRIBUTOS_DETALHADOS, "goalkeeping_reflexes")))
        self.assertEqual(goleiro["movement_agility"], 60)                   # 0.5 * 80 + 20
        self.assertEqual(goleiro["movement_reactions"], 55)                 # já existia: intocado
        self.assertEqual(goleiro[COLUNA_IMPUTADOS], "movement_agility")
        self.assertTrue(pd.isna(goleiro["pace"]))                          # linha do goleiro fica vazia

    def test_valores_ficam_em_0_a_99(self):
        alvo = pd.DataFrame([
            {"player_positions": "ST", "overall": 400, **{c: 400 for c in ATRIBUTOS_LINHA}, **{c: None for c in ATRIBUTOS_GK},
             **{c: None for c in ATRIBUTOS_DETALHADOS}},
        ])
        resultado = imputar(alvo, self.modelo)
        self.assertTrue(all(0 <= resultado.iloc[0][c] <= 99 for c in ATRIBUTOS_DETALHADOS))

    def test_erro_por_atributo_no_corte_de_validacao(self):
        erros = avaliar_imputacao(_base(n=900), n_treino=700)
        self.assertEqual(set(erros["tipo"]), {"goleiro", "linha"})
        lineares = erros[erros["atributo"].isin(ATRIBUTOS_DETALHADOS)]
        self.assertLess(lineares["erro_medio"].max(), 1.0)  # a relação sintética é linear


if __name__ == "__main__":
    unittest.main()
