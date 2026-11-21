import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pipeline.calibration import converter_percentil, grupo_da_proposta
from pipeline.identity import descobrir_lacunas
from pipeline.materialize import materializar
from pipeline.validation import validar_proposta


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.dataset = pd.DataFrame([
            {"sofifa_id": 1, "short_name": "A. Goleiro", "long_name": "Alisson", "player_positions": "GK", "overall": 89, "nationality_name": "Brazil", "pace": None, "shooting": None, "passing": None, "dribbling": None, "defending": None, "physic": None, "goalkeeping_reflexes": 91, "goalkeeping_diving": 88, "goalkeeping_handling": 85, "goalkeeping_kicking": 80, "goalkeeping_positioning": 89, "goalkeeping_speed": 50},
            {"sofifa_id": 2, "short_name": "Vini Jr.", "long_name": "Vinicius Junior", "player_positions": "LW, ST", "overall": 84, "nationality_name": "Brazil", "pace": 95, "shooting": 80, "passing": 78, "dribbling": 90, "defending": 29, "physic": 75, "goalkeeping_reflexes": None, "goalkeeping_diving": None, "goalkeeping_handling": None, "goalkeeping_kicking": None, "goalkeeping_positioning": None, "goalkeeping_speed": None},
        ])

    def test_matching_classifica_ausente_e_presente(self):
        convocacoes = pd.DataFrame([
            {"pais": "Brazil", "nome": "Alisson", "posicao": "GK", "fonte_url": "x"},
            {"pais": "Brazil", "nome": "Bento", "posicao": "GK", "fonte_url": "x"},
        ])
        resultado = descobrir_lacunas(convocacoes, self.dataset)
        self.assertEqual(resultado["status"].tolist(), ["present", "missing"])

    def test_grupo_e_percentil(self):
        self.assertEqual(grupo_da_proposta("LW"), "ATT")
        self.assertEqual(converter_percentil(self.dataset.iloc[[1]], "pace", 0.5), 95)

    def test_goleiro_rejeita_atributo_de_linha(self):
        proposta = {
            "nome": "Bento", "pais": "Brazil", "posicao": "GK", "percentis": {"overall": 0.5, "pace": 0.5, "goalkeeping_reflexes": 0.5},
            "fontes": [{"url": "https://example.com"}], "observacao": "x",
        }
        self.assertTrue(any("atributos de linha" in erro for erro in validar_proposta(proposta, "Brazil")))

    def test_materializacao_aloca_id_e_mantem_gk_valido(self):
        proposta = {
            "nome": "Bento", "pais": "Brazil", "posicao": "GK", "dob": "1999-06-10", "percentis": {"overall": 0.5, "goalkeeping_reflexes": 0.5},
            "fontes": [{"url": "https://example.com"}], "observacao": "x", "status": "approved",
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = materializar([proposta], self.dataset, "2024-07-14", Path(tmp) / "ids.csv")
        self.assertLess(output.iloc[0]["sofifa_id"], 0)
        self.assertTrue(pd.isna(output.iloc[0]["pace"]))
        self.assertFalse(pd.isna(output.iloc[0]["goalkeeping_reflexes"]))


if __name__ == "__main__":
    unittest.main()
