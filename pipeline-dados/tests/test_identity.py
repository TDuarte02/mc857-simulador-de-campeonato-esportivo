import unittest

import pandas as pd

from pipeline.identity import atribuir_pessoas, descobrir_lacunas, encontrar_candidatos, exigir_convocados


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


class PoolCombinadoTest(unittest.TestCase):
    """Matching contra o pool com camadas (base_22, convocado_2024, historico)."""

    def setUp(self):
        linhas = [
            # Cubas: a lenda homônima tem outra data; o convocado é "Adrián Andrés Cubas" da base.
            (222429, "A. Cubas", "Adrián Andrés Cubas", "1996-05-22", "Paraguay", "base_22"),
            (-448, "Andres Cubas", "Andres Cubas", "1996-05-11", "Paraguay", "historico"),
            # Turner: versão 2024 pesquisada e versão lenda com o mesmo nome e a mesma data.
            (-75, "Matt Turner", "Matt Turner", "1994-06-24", "United States", "convocado_2024"),
            (-635, "Matt Turner", "Matt Turner", "1994-06-24", "United States", "historico"),
            # Isla: idem, com o nome da lenda sem acento.
            (-121, "Mauricio Isla", "Mauricio Isla", "1988-06-12", "Chile", "convocado_2024"),
            (-626, "Mauricio Isla", "Mauricio Isla", "1988-06-12", "Chile", "historico"),
            # Homônimo na base FIFA 22: a pesquisa de 2024 tem preferência.
            (1001, "M. Isla", "Mauricio Isla", "1988-06-12", "Chile", "base_22"),
        ]
        self.pool = pd.DataFrame(
            [dict(zip(("sofifa_id", "short_name", "long_name", "dob", "nationality_name", "camada"), l)) for l in linhas]
        )

    def _casar(self, pais, nome, dob):
        convocacoes = pd.DataFrame([{"pais": pais, "nome": nome, "posicao": "x", "fonte_url": "x", "dob": dob}])
        return descobrir_lacunas(convocacoes, self.pool).iloc[0]

    def test_cubas_cai_no_fallback_quando_o_nome_exato_e_de_outra_data(self):
        self.assertEqual(encontrar_candidatos("Andrés Cubas", self.pool, dob="1996-05-22"), [0])
        resultado = self._casar("Paraguay", "Andrés Cubas", "1996-05-22")
        self.assertEqual((resultado["status"], resultado["indice_base"]), ("present", "0"))

    def test_lenda_nunca_e_o_convocado(self):
        resultado = self._casar("United States", "Matt Turner", "1994-06-24")
        self.assertEqual((resultado["status"], resultado["indice_base"]), ("present", "2"))

    def test_pesquisa_2024_vence_a_base(self):
        resultado = self._casar("Chile", "Mauricio Isla", "1988-06-12")
        self.assertEqual((resultado["status"], resultado["indice_base"]), ("present", "4"))

    def test_ambiguo_ou_ausente_interrompe_com_relatorio(self):
        convocacoes = pd.DataFrame([
            {"pais": "Chile", "nome": "Fulano de Tal", "posicao": "x", "fonte_url": "x", "dob": "2000-01-01"},
            {"pais": "Chile", "nome": "Mauricio Isla", "posicao": "x", "fonte_url": "x", "dob": "1988-06-12"},
        ])
        with self.assertRaisesRegex(ValueError, "missing: Chile: Fulano de Tal"):
            exigir_convocados(descobrir_lacunas(convocacoes, self.pool))
        exigir_convocados(descobrir_lacunas(convocacoes.iloc[[1]], self.pool))  # só presentes: passa

    def test_dois_convocados_na_mesma_linha_interrompem(self):
        convocacoes = pd.DataFrame([
            {"pais": "Chile", "nome": "Mauricio Isla", "posicao": "x", "fonte_url": "x", "dob": "1988-06-12"},
            {"pais": "Chile", "nome": "Isla", "posicao": "x", "fonte_url": "x", "dob": "1988-06-12"},
        ])
        with self.assertRaisesRegex(ValueError, "mesma linha"):
            exigir_convocados(descobrir_lacunas(convocacoes, self.pool))

    def test_person_key_une_as_versoes_2024_e_lenda(self):
        chaves = atribuir_pessoas(self.pool).tolist()
        self.assertEqual(chaves[3], "-75")      # Turner lenda -> versão 2024
        self.assertEqual(chaves[5], "-121")     # Isla lenda -> versão 2024 (preferida à base)
        self.assertEqual(chaves[1], "-448")     # Cubas lenda: data diferente, pessoa própria
        self.assertEqual(chaves[0], "222429")


if __name__ == "__main__":
    unittest.main()
