import unittest

import pandas as pd

from pipeline.filtro import COTAS_PADRAO, filtrar_pool, parse_cotas, resumo_por_selecao


class FiltroTest(unittest.TestCase):
    def _pool(self):
        linhas = []
        # Panamá: poucos de cada grupo, todos da base
        for i in range(4):
            linhas.append({"nationality_name": "Panama", "player_positions": "GK", "overall": 70 + i, "camada": "base_22", "sofifa_id": 100 + i})
        for i in range(20):
            linhas.append({"nationality_name": "Panama", "player_positions": "CB", "overall": 60 + i, "camada": "base_22", "sofifa_id": 200 + i})
        # Argentina: muitos enriquecidos (mais que a cota) em MID
        for i in range(9):
            linhas.append({"nationality_name": "Argentina", "player_positions": "GK", "overall": 70, "camada": "base_22", "sofifa_id": 300 + i})
        for i in range(30):
            linhas.append({"nationality_name": "Argentina", "player_positions": "CAM", "overall": 60 + (i % 30), "camada": "base_22", "sofifa_id": 400 + i})
        for i in range(20):
            linhas.append({"nationality_name": "Argentina", "player_positions": "CAM", "overall": 62, "camada": "historico", "sofifa_id": -1 - i})
        return pd.DataFrame(linhas)

    def test_parse_cotas(self):
        self.assertEqual(parse_cotas("GK=3,DEF=8,MID=8,ATT=7"), {"GK": 3, "DEF": 8, "MID": 8, "ATT": 7})
        with self.assertRaises(ValueError):
            parse_cotas("GK=3,DEF=8")          # faltam grupos
        with self.assertRaises(ValueError):
            parse_cotas("XX=3,DEF=8,MID=8,ATT=7")  # grupo inválido

    def test_cota_e_piso_para_a_base(self):
        filtrado = filtrar_pool(self._pool())
        pan = filtrado[filtrado.nationality_name == "Panama"]
        # GK: só havia 4 na base, então não inventa o quinto
        self.assertEqual(len(pan[pan.player_positions == "GK"]), 4)
        # DEF: havia 20, corta em 12
        self.assertEqual(len(pan[pan.player_positions == "CB"]), 12)

    def test_enriquecidos_nunca_sao_cortados(self):
        filtrado = filtrar_pool(self._pool())
        arg_hist = filtrado[(filtrado.nationality_name == "Argentina") & (filtrado.camada == "historico")]
        self.assertEqual(len(arg_hist), 20)   # acima da cota de 12, e mesmo assim ficam todos
        # e nada de base é somado por cima quando os enriquecidos já estouram a cota
        arg_mid = filtrado[(filtrado.nationality_name == "Argentina") & (filtrado.player_positions == "CAM")]
        self.assertEqual(len(arg_mid), 20)

    def test_base_escolhe_os_melhores_por_overall(self):
        filtrado = filtrar_pool(self._pool())
        pan_cb = filtrado[(filtrado.nationality_name == "Panama") & (filtrado.player_positions == "CB")]
        self.assertEqual(pan_cb.overall.min(), 68)   # dos 20 (60..79), ficam os 12 melhores

    def test_preserva_colunas_originais(self):
        pool = self._pool()
        filtrado = filtrar_pool(pool)
        self.assertEqual(list(filtrado.columns), list(pool.columns))

    def test_resumo_por_selecao(self):
        resumo = resumo_por_selecao(filtrar_pool(self._pool()))
        self.assertEqual(resumo.loc["Panama", "GK"], 4)
        self.assertEqual(resumo.loc["Argentina", "MID"], 20)

    def test_respeita_cotas_customizadas(self):
        filtrado = filtrar_pool(self._pool(), cotas={"GK": 2, "DEF": 3, "MID": 3, "ATT": 3})
        pan = filtrado[filtrado.nationality_name == "Panama"]
        self.assertEqual(len(pan[pan.player_positions == "CB"]), 3)
        self.assertEqual(COTAS_PADRAO["MID"], 12)  # o padrão não foi mutado


if __name__ == "__main__":
    unittest.main()
