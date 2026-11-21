import tempfile
import unittest
from pathlib import Path

from pipeline.runner import iniciar_manifesto, preparar_pais, proximo_passo
from pipeline.state import STATUS_PENDING, STATUS_RESEARCHING, carregar_manifesto, salvar_manifesto, resumo_manifesto


class StateTest(unittest.TestCase):
    def test_manifesto_persiste_e_retorna_proximo_pais(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "manifest.json"
            manifesto = iniciar_manifesto(caminho, "Copa América", 2024, "2024-07-14", ["Brazil", "Argentina"])
            self.assertEqual(resumo_manifesto(manifesto), {STATUS_PENDING: 2})
            manifesto["paises"]["Brazil"]["status"] = "published"
            salvar_manifesto(manifesto, caminho)
            carregado = carregar_manifesto(caminho)
            self.assertEqual(proximo_passo(carregado, Path(tmp))["pais"], "Argentina")

    def test_preparar_pais_salva_artefatos_e_estado(self):
        raiz = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifesto = iniciar_manifesto(tmp_path / "manifest.json", "Copa América", 2024, "2024-07-14", ["Brazil"])
            pacote = preparar_pais(
                manifesto,
                "Brazil",
                raiz / "players_22.csv",
                raiz / "dados/templates/convocacoes_copa_america_2024.csv",
                raiz / "dados/templates/aliases.csv",
                tmp_path,
            )
            self.assertTrue(pacote.exists())
            self.assertEqual(manifesto["paises"]["Brazil"]["status"], STATUS_RESEARCHING)
            self.assertTrue((pacote.parent / "lacunas.csv").exists())


if __name__ == "__main__":
    unittest.main()
