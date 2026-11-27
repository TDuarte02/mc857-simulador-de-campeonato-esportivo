import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pipeline.registry import (
    alocar_id,
    aplicar_registry,
    carregar_registry,
    chave_registro,
    reconstruir_registry,
)


def _linha(sofifa_id, nome, pais="Chile", dob="1988-06-12", camada="convocado_2024"):
    return {"sofifa_id": sofifa_id, "short_name": nome, "nationality_name": pais, "dob": dob, "camada": camada}


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.caminho = Path(self.tmp.name) / "registry" / "player_ids.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_camada_faz_parte_da_chave(self):
        atual = alocar_id(self.caminho, {"pais": "Chile", "nome": "Mauricio Isla", "dob": "1988-06-12"})
        lenda = alocar_id(self.caminho, {"pais": "Chile", "nome": "Mauricio Isla", "dob": "1988-06-12", "is_historico": True})
        self.assertEqual((atual, lenda), (-1, -2))
        # a mesma chave devolve o mesmo id
        self.assertEqual(alocar_id(self.caminho, {"pais": "Chile", "nome": "Mauricio Isla", "dob": "1988-06-12"}), -1)
        self.assertEqual(
            carregar_registry(self.caminho)["player_key"].tolist(),
            [chave_registro("convocado_2024", "Chile", "Mauricio Isla", "1988-06-12"),
             chave_registro("historico", "Chile", "Mauricio Isla", "1988-06-12")],
        )

    def test_reconstrucao_preserva_ids_e_deixa_a_lenda_duplicada_sem_registro(self):
        convocados = pd.DataFrame([_linha(-1, "Endrick", "Brazil", "2006-07-21"), _linha(-2, "Mauricio Isla")])
        historicos = pd.DataFrame([_linha(-3, "Pelé", "Brazil", "1940-10-23"), _linha(-2, "Mauricio Isla")])

        pendentes = reconstruir_registry([("convocado_2024", convocados), ("historico", historicos)], self.caminho)

        registry = carregar_registry(self.caminho)
        self.assertEqual(sorted(registry["sofifa_id"].tolist()), [-3, -2, -1])
        self.assertEqual(pendentes[["camada", "sofifa_id"]].values.tolist(), [["historico", -2]])
        # a lenda pendente ganha o próximo id livre; a versão 2024 mantém o seu
        self.assertEqual(alocar_id(self.caminho, {"pais": "Chile", "nome": "Mauricio Isla", "dob": "1988-06-12", "is_historico": True}), -4)
        self.assertEqual(alocar_id(self.caminho, {"pais": "Chile", "nome": "Mauricio Isla", "dob": "1988-06-12"}), -2)

    def test_aplicar_registry_reescreve_so_as_linhas_enriquecidas(self):
        reconstruir_registry([("convocado_2024", pd.DataFrame([_linha(-2, "Mauricio Isla")]))], self.caminho)
        pool = pd.DataFrame([
            _linha(-2, "Mauricio Isla"),
            _linha(-2, "Mauricio Isla", camada="historico"),
            _linha(12345, "M. Isla", camada="base_22"),
        ])

        resultado = aplicar_registry(pool, self.caminho)

        self.assertEqual(resultado["sofifa_id"].tolist(), [-2, -3, 12345])
        self.assertEqual(aplicar_registry(pool, self.caminho)["sofifa_id"].tolist(), [-2, -3, 12345])


if __name__ == "__main__":
    unittest.main()
