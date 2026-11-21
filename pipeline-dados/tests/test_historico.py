import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pipeline.historico import (
    IDADE_PICO,
    carregar_atributos_reais,
    marcar_arquivo,
    marcar_propostas,
)
from pipeline.materialize import materializar


class HistoricoTest(unittest.TestCase):
    def _proposta(self, nome: str = "Diego Maradona") -> dict:
        return {
            "nome": nome,
            "pais": "Argentina",
            "posicao": "AM",
            "dob": "1960-10-30",
            "percentis": {"overall": 0.99, "pace": 0.9, "shooting": 0.95, "passing": 0.98, "dribbling": 0.99, "defending": 0.4, "physic": 0.7},
            "fontes": [{"url": "https://www.wikidata.org/wiki/Q17515", "afirmacao": "Lenda argentina."}],
            "observacao": "Campeão de 1986.",
            "confianca": 0.7,
            "status": "approved",
        }

    def test_marcar_propostas_aplica_metadados(self):
        propostas = marcar_propostas([self._proposta()])
        p = propostas[0]
        self.assertTrue(p["is_historico"])
        self.assertEqual(p["origem_registro"], "historico_estimado")
        self.assertEqual(p["validacao_via"], "wikidata")
        self.assertEqual(p["age"], IDADE_PICO)

    def test_marcar_e_idempotente_e_respeita_age_existente(self):
        propostas = [self._proposta()]
        marcar_propostas(propostas, idade_pico=24)
        marcar_propostas(propostas)  # segunda passada não deve sobrescrever
        self.assertEqual(propostas[0]["age"], 24)

    def test_marcar_arquivo_le_e_regrava(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "resposta_bruta.json"
            caminho.write_text(json.dumps([self._proposta()]), encoding="utf-8")
            total = marcar_arquivo(caminho)
            self.assertEqual(total, 1)
            self.assertTrue(json.loads(caminho.read_text())[0]["is_historico"])

    def test_materializacao_historica_usa_pico_e_nao_idade_de_2024(self):
        dataset = pd.DataFrame([
            {"sofifa_id": 1, "short_name": "A. Meia", "long_name": "Algum Meia", "player_positions": "AM", "overall": 80, "nationality_name": "Argentina", "dob": "1995-01-01", "age": 26,
             "pace": 80, "shooting": 80, "passing": 80, "dribbling": 80, "defending": 80, "physic": 80,
             "goalkeeping_diving": None, "goalkeeping_handling": None, "goalkeeping_kicking": None, "goalkeeping_positioning": None, "goalkeeping_reflexes": None, "goalkeeping_speed": None},
        ])
        with tempfile.TemporaryDirectory() as tmp:
            propostas = marcar_propostas([self._proposta()])
            out = materializar(propostas, dataset, "2024-07-14", Path(tmp) / "ids.csv")
        linha = out.iloc[0]
        self.assertEqual(linha["age"], IDADE_PICO)
        self.assertTrue(bool(linha["is_historico"]))
        self.assertEqual(linha["origem_registro"], "historico_estimado")


    def test_carregar_atributos_reais_le_somente_icons(self):
        with tempfile.TemporaryDirectory() as tmp:
            antigo = Path(tmp) / "historicos_panama.csv"
            pd.DataFrame([
                {"nationality_name": "Panama", "short_name": "Lenda Real", "dob": "1960-10-30", "fonte_atributos": "ea_fc_icon",
                 "overall": "97", "pace": "90", "shooting": "88", "passing": "90", "dribbling": "96", "defending": "46", "physic": "76"},
                {"nationality_name": "Panama", "short_name": "Jogador Estimado", "dob": "1970-01-01", "fonte_atributos": "estimado",
                 "overall": "99", "pace": "99", "shooting": "99", "passing": "99", "dribbling": "99", "defending": "99", "physic": "99"},
            ]).to_csv(antigo, index=False)
            reais = carregar_atributos_reais([antigo])
        self.assertEqual(len(reais), 1)
        valores = list(reais.values())[0]
        self.assertEqual(valores["overall"], 97)
        self.assertEqual(valores["dribbling"], 96)

    def test_override_tem_precedencia_sobre_percentil(self):
        dataset = pd.DataFrame([
            {"sofifa_id": 1, "short_name": "A. Meia", "long_name": "Algum Meia", "player_positions": "AM", "overall": 70, "nationality_name": "Panama", "dob": "1995-01-01", "age": 26,
             "pace": 70, "shooting": 70, "passing": 70, "dribbling": 70, "defending": 70, "physic": 70,
             "goalkeeping_diving": None, "goalkeeping_handling": None, "goalkeeping_kicking": None, "goalkeeping_positioning": None, "goalkeeping_reflexes": None, "goalkeeping_speed": None},
        ])
        proposta = self._proposta("Lenda Real")
        proposta["pais"] = "Panama"
        proposta["percentis"] = {"overall": 0.5, "pace": 0.5, "shooting": 0.5, "passing": 0.5, "dribbling": 0.5, "defending": 0.5, "physic": 0.5}
        marcar_propostas([proposta], atributos_reais={"panama|lenda real|1960-10-30": {"overall": 97, "pace": 90, "dribbling": 96}})
        with tempfile.TemporaryDirectory() as tmp:
            out = materializar([proposta], dataset, "2024-07-14", Path(tmp) / "ids.csv")
        linha = out.iloc[0]
        self.assertEqual(linha["overall"], 97)
        self.assertEqual(linha["dribbling"], 96)
        # coluna não sobrescrita continua vindo do percentil
        self.assertEqual(linha["shooting"], 70)

    def test_historico_usa_banda_de_lenda_e_convocado_usa_o_pool_do_pais(self):
        # O pool do Panamá é fraco; mesmo o topo global (92) não representa uma lenda.
        # Um histórico vai para a banda de lenda; um convocado fica no teto do país.
        dataset = pd.DataFrame([
            {"sofifa_id": 1, "short_name": "P. Fraco", "long_name": "Panamenho Fraco", "player_positions": "AM", "overall": 60, "nationality_name": "Panama", "dob": "1995-01-01", "age": 26,
             "pace": 60, "shooting": 60, "passing": 60, "dribbling": 60, "defending": 60, "physic": 60,
             "goalkeeping_diving": None, "goalkeeping_handling": None, "goalkeeping_kicking": None, "goalkeeping_positioning": None, "goalkeeping_reflexes": None, "goalkeeping_speed": None},
            {"sofifa_id": 2, "short_name": "B. Craque", "long_name": "Brasileiro Craque", "player_positions": "AM", "overall": 92, "nationality_name": "Brazil", "dob": "1995-01-01", "age": 26,
             "pace": 92, "shooting": 92, "passing": 92, "dribbling": 92, "defending": 92, "physic": 92,
             "goalkeeping_diving": None, "goalkeeping_handling": None, "goalkeeping_kicking": None, "goalkeeping_positioning": None, "goalkeeping_reflexes": None, "goalkeeping_speed": None},
        ])
        proposta = self._proposta("Lenda Panamenha")
        proposta["pais"] = "Panama"
        proposta["percentis"] = {"overall": 0.99, "pace": 0.99, "shooting": 0.99, "passing": 0.99, "dribbling": 0.99, "defending": 0.99, "physic": 0.99}
        with tempfile.TemporaryDirectory() as tmp:
            como_convocado = materializar([dict(proposta)], dataset, "2024-07-14", Path(tmp) / "a.csv").iloc[0]
            historico = marcar_propostas([dict(proposta)])
            como_historico = materializar(historico, dataset, "2024-07-14", Path(tmp) / "b.csv").iloc[0]
        self.assertEqual(como_convocado["overall"], 60)   # teto do Panamá
        self.assertEqual(como_historico["overall"], 96)   # banda de lenda

    def test_banda_lenda_ancora_os_tiers(self):
        from pipeline.calibration import banda_lenda
        self.assertEqual(banda_lenda(0.99), 96)
        self.assertEqual(banda_lenda(0.97), 93)
        self.assertEqual(banda_lenda(0.95), 90)
        self.assertEqual(banda_lenda(0.90), 86)
        self.assertEqual(banda_lenda(0.50), 74)
        self.assertEqual(banda_lenda(None), None)
        self.assertGreater(banda_lenda(0.96), banda_lenda(0.91))  # monótona

    def test_banda_preserva_o_perfil_do_jogador(self):
        # Escalar proporcionalmente não deve achatar o perfil: quem defendia pouco
        # continua defendendo pouco depois de virar lenda.
        dataset = pd.DataFrame([
            {"sofifa_id": 1, "short_name": "A. Atac", "long_name": "Atacante Comum", "player_positions": "ST", "overall": 70, "nationality_name": "Panama", "dob": "1995-01-01", "age": 26,
             "pace": 80, "shooting": 75, "passing": 60, "dribbling": 72, "defending": 25, "physic": 70,
             "goalkeeping_diving": None, "goalkeeping_handling": None, "goalkeeping_kicking": None, "goalkeeping_positioning": None, "goalkeeping_reflexes": None, "goalkeeping_speed": None},
        ])
        proposta = self._proposta("Lenda Atacante")
        proposta["pais"] = "Panama"
        proposta["posicao"] = "ST"
        proposta["percentis"] = {"overall": 0.98, "pace": 0.98, "shooting": 0.98, "passing": 0.5, "dribbling": 0.9, "defending": 0.1, "physic": 0.8}
        with tempfile.TemporaryDirectory() as tmp:
            linha = materializar(marcar_propostas([proposta]), dataset, "2024-07-14", Path(tmp) / "ids.csv").iloc[0]
        self.assertEqual(linha["overall"], 94)
        self.assertGreater(linha["pace"], linha["defending"])
        self.assertLess(linha["defending"], 40)


if __name__ == "__main__":
    unittest.main()
