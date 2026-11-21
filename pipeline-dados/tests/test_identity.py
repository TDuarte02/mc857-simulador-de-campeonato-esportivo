import unittest

import pandas as pd

from pipeline.identity import descobrir_lacunas, encontrar_candidatos


class IdentityTest(unittest.TestCase):
    def setUp(self):
        # Espelha o formato real: short_name abreviado, long_name completo e dob em ISO.
        self.dataset = pd.DataFrame([
            {"sofifa_id": 1, "short_name": "A. Sánchez", "long_name": "Alexis Alejandro Sánchez Sánchez", "dob": "1988-12-19", "nationality_name": "Chile", "player_positions": "CF, ST", "overall": 80},
            {"sofifa_id": 2, "short_name": "C. Bravo", "long_name": "Claudio Andrés Bravo Muñoz", "dob": "1983-04-13", "nationality_name": "Chile", "player_positions": "GK", "overall": 78},
            {"sofifa_id": 3, "short_name": "Thales", "long_name": "Thales Bento Oleques", "dob": "1994-01-02", "nationality_name": "Chile", "player_positions": "RB", "overall": 70},
        ])

    def test_nome_exato_tem_prioridade(self):
        self.assertEqual(encontrar_candidatos("Thales", self.dataset), [2])

    def test_subconjunto_de_tokens_casa_nome_comum(self):
        # "Alexis Sánchez" não é short_name nem long_name exato, mas todos os tokens
        # aparecem no long_name.
        self.assertEqual(encontrar_candidatos("Alexis Sánchez", self.dataset), [0])
        self.assertEqual(encontrar_candidatos("Claudio Bravo", self.dataset), [1])

    def test_dob_impede_casar_homonimo(self):
        # "Bento" (goleiro de 1999) não pode casar por engano com "Thales Bento Oleques".
        self.assertEqual(encontrar_candidatos("Bento", self.dataset, dob="1999-06-10"), [])

    def test_dob_confirma_o_candidato_certo(self):
        self.assertEqual(encontrar_candidatos("Thales Bento", self.dataset, dob="1994-01-02"), [2])

    def test_sem_dob_o_candidato_e_ambiguo(self):
        ambiguo = pd.DataFrame([
            {"sofifa_id": 1, "short_name": "A. Sánchez", "long_name": "Alexis Alejandro Sánchez Sánchez", "dob": "1988-12-19", "nationality_name": "Chile", "player_positions": "CF, ST", "overall": 80},
            {"sofifa_id": 5, "short_name": "A. Sánchez R.", "long_name": "Alexis Sánchez Ruiz", "dob": "1995-01-01", "nationality_name": "Chile", "player_positions": "ST", "overall": 70},
        ])
        # sem dob, "Alexis Sánchez" casa com os dois -> o pipeline marca como ambíguo, não escolhe
        self.assertEqual(len(encontrar_candidatos("Alexis Sánchez", ambiguo)), 2)
        self.assertEqual(encontrar_candidatos("Alexis Sánchez", ambiguo, dob="1988-12-19"), [0])

    def test_nome_exato_tem_prioridade_sobre_subconjunto(self):
        # "Bento" é short_name exato do jogador 4; o casamento exato vence o subconjunto.
        com_exato = pd.concat([self.dataset, pd.DataFrame([
            {"sofifa_id": 4, "short_name": "Bento", "long_name": "Bento Matheus Krepski", "dob": "1999-06-10", "nationality_name": "Chile", "player_positions": "GK", "overall": 77},
        ])], ignore_index=True)
        self.assertEqual(encontrar_candidatos("Bento", com_exato), [3])

    def test_matching_ignora_acento_e_caixa(self):
        self.assertEqual(encontrar_candidatos("alexis sanchez", self.dataset), [0])

    def test_lacunas_usam_dob_para_evitar_falso_positivo(self):
        convocacoes = pd.DataFrame([
            {"pais": "Chile", "nome": "Bento", "posicao": "GK", "fonte_url": "x", "dob": "1999-06-10"},
            {"pais": "Chile", "nome": "Claudio Bravo", "posicao": "GK", "fonte_url": "x", "dob": "1983-04-13"},
        ])
        resultado = descobrir_lacunas(convocacoes, self.dataset)
        self.assertEqual(resultado["status"].tolist(), ["missing", "present"])


if __name__ == "__main__":
    unittest.main()
