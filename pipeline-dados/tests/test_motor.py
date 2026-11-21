import unittest

import numpy as np
import pandas as pd

from pipeline.motor import (
    ATRIBUTOS_LINHA,
    COLUNAS_EXTRA,
    COLUNAS_MOTOR,
    SUB_ATRIBUTOS,
    exportar_jogadores,
    treinar_sub_atributos,
)


def _base(n=80):
    """Base sintética: jogadores de linha com tudo preenchido + 4 goleiros."""
    rng = np.random.default_rng(0)
    linhas = []
    for i in range(n):
        base = 60 + (i % 30)
        linha = {
            "short_name": f"Linha {i}", "long_name": f"Linha {i}", "player_positions": "CM",
            "overall": base, "potential": base, "nationality_name": "Brazil",
            "pace": base, "shooting": base - 5, "passing": base - 2, "dribbling": base - 3,
            "defending": base - 8, "physic": base - 4, "goalkeeping_reflexes": 20,
        }
        for atributo in SUB_ATRIBUTOS:
            linha[atributo] = base - 6
        linhas.append(linha)
    for i in range(4):
        linha = {"short_name": f"Goleiro {i}", "long_name": f"Goleiro {i}", "player_positions": "GK",
                 "overall": 80, "potential": 80, "nationality_name": "Brazil", "goalkeeping_reflexes": 88}
        for atributo in ATRIBUTOS_LINHA:
            linha[atributo] = None
        for atributo in SUB_ATRIBUTOS:
            linha[atributo] = None
        linhas.append(linha)
    return pd.DataFrame(linhas)


class MotorTest(unittest.TestCase):
    def setUp(self):
        self.base = _base()

    def test_treina_um_modelo_por_sub_atributo(self):
        modelo = treinar_sub_atributos(self.base)
        self.assertEqual(set(modelo), set(SUB_ATRIBUTOS))
        # os 7 coeficientes dos atributos + intercepto
        for coeficientes in modelo.values():
            self.assertEqual(len(coeficientes), 8)

    def test_saida_tem_o_contrato_do_motor(self):
        saida = exportar_jogadores(self.base, self.base)
        self.assertEqual(list(saida.columns), [*COLUNAS_MOTOR, *COLUNAS_EXTRA])
        for coluna in COLUNAS_MOTOR[2:]:  # todas as numéricas
            self.assertFalse(saida[coluna].isna().any(), f"{coluna} ficou vazia")
            self.assertTrue(((saida[coluna] >= 0) & (saida[coluna] <= 100)).all(), f"{coluna} fora de [0,100]")

    def test_goleiro_fica_com_zeros_nos_campos_inertes(self):
        saida = exportar_jogadores(self.base, self.base)
        goleiro = saida[saida.pos == "GK"].iloc[0]
        for coluna in ATRIBUTOS_LINHA:
            self.assertEqual(goleiro[coluna], 0, f"GK deveria ter {coluna} zerado")
        for coluna in SUB_ATRIBUTOS:
            self.assertEqual(goleiro[coluna], 0)
        # a nota que o motor realmente lê para goleiro é preservada
        self.assertEqual(goleiro["goalkeeping_reflexes"], 88)

    def test_jogador_de_linha_nao_recebe_atributo_de_goleiro(self):
        saida = exportar_jogadores(self.base, self.base)
        linha = saida[saida.pos != "GK"].iloc[0]
        self.assertEqual(linha["goalkeeping_reflexes"], 0)
        self.assertEqual(linha["pace"], 60)  # veio do pool, não foi derivado

    def test_usa_o_valor_real_quando_o_pool_ja_tem(self):
        # jogador com os 9 sub-atributos preenchidos: não deve ser sobrescrito pelo derivado
        pool = self.base.copy()
        pool.loc[0, "short_name"] = "Completo"
        for atributo in SUB_ATRIBUTOS:
            pool.loc[0, atributo] = 99
        saida = exportar_jogadores(pool, self.base)
        for atributo in SUB_ATRIBUTOS:
            self.assertEqual(int(saida[saida.name == "Completo"].iloc[0][atributo]), 99)

    def test_deriva_quando_o_pool_nao_tem(self):
        pool = self.base.copy()
        pool.loc[0, "short_name"] = "SemDado"
        for atributo in SUB_ATRIBUTOS:
            pool.loc[0, atributo] = None
        saida = exportar_jogadores(pool, self.base).set_index("name")
        for atributo in SUB_ATRIBUTOS:
            valor = int(saida.loc["SemDado", atributo])
            self.assertTrue(1 <= valor <= 99, f"{atributo} derivado fora da faixa: {valor}")

    def test_posicao_usa_o_primeiro_codigo(self):
        pool = self.base.copy()
        pool.loc[0, "player_positions"] = "CAM, CF"
        self.assertEqual(exportar_jogadores(pool, self.base).iloc[0]["pos"], "CAM")


if __name__ == "__main__":
    unittest.main()
