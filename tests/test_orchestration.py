import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pipeline.report import consolidar_resumo, mesclar_publicados
from pipeline.runner import (
    diretorio_pais,
    iniciar_manifesto,
    nome_snapshot,
    preparar_pais,
    publicar_pais,
    validar_resposta_pais,
)
from pipeline.state import (
    STATUS_PENDING,
    STATUS_PUBLISHED,
    STATUS_REVIEW_REQUIRED,
    carregar_manifesto,
    salvar_manifesto,
)

RAIZ = Path(__file__).resolve().parents[1]
CONVOCACOES = RAIZ / "dados/templates/convocacoes_copa_america_2024.csv"
ALIASES = RAIZ / "dados/templates/aliases.csv"


def _resposta_valida(nome: str, posicao: str = "GK") -> dict:
    return {
        "nome": nome,
        "pais": "Brazil",
        "posicao": posicao,
        "dob": "1999-06-10",
        "club_name": "Clube",
        "percentis": {"overall": 0.6, "goalkeeping_reflexes": 0.6},
        "fontes": [{"url": "https://example.com/perfil", "afirmacao": "Perfil oficial."}],
        "observacao": "Jogador convocado.",
        "confianca": 0.8,
        "status": "approved",
    }


class OrquestracaoTest(unittest.TestCase):
    def _manifesto(self, tmp: Path, *, max_attempts: int = 3, allow_partial: bool = False) -> dict:
        manifesto = iniciar_manifesto(
            tmp / "manifest.json", "Copa América", 2024, "2024-07-14", ["Brazil"],
            max_attempts=max_attempts, allow_partial_publish=allow_partial,
        )
        return manifesto

    def test_ciclo_completo_publica_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifesto = self._manifesto(tmp_path)
            preparar_pais(manifesto, "Brazil", RAIZ / "players_22.csv", CONVOCACOES, ALIASES, tmp_path)
            resposta = diretorio_pais(tmp_path, "Brazil") / "resposta_bruta.json"
            resposta.write_text(json.dumps([_resposta_valida("Bento")]), encoding="utf-8")

            validacao = validar_resposta_pais(manifesto, "Brazil", tmp_path)
            self.assertTrue((validacao["status"] == "approved").all())

            registry = tmp_path / "registry" / "player_ids.csv"
            saida = publicar_pais(manifesto, "Brazil", RAIZ / "players_22.csv", tmp_path, registry)
            self.assertEqual(manifesto["paises"]["Brazil"]["status"], STATUS_PUBLISHED)
            self.assertTrue(saida.exists())
            publicado = pd.read_csv(saida, low_memory=False)
            self.assertGreaterEqual(len(publicado.columns), 110)
            self.assertLess(publicado.iloc[0]["sofifa_id"], 0)
            self.assertTrue(registry.exists())

    def test_tentativas_esgotadas_movem_para_revisao_manual(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifesto = self._manifesto(tmp_path, max_attempts=1)
            preparar_pais(manifesto, "Brazil", RAIZ / "players_22.csv", CONVOCACOES, ALIASES, tmp_path)
            invalida = _resposta_valida("Bento", posicao="GK")
            invalida["fontes"] = []
            (diretorio_pais(tmp_path, "Brazil") / "resposta_bruta.json").write_text(
                json.dumps([invalida]), encoding="utf-8"
            )
            resultado = validar_resposta_pais(manifesto, "Brazil", tmp_path)
            self.assertTrue((resultado["status"] != "approved").any())
            self.assertEqual(manifesto["paises"]["Brazil"]["status"], STATUS_REVIEW_REQUIRED)

    def test_publicacao_parcial_bloqueada_por_padrao(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifesto = self._manifesto(tmp_path, allow_partial=False)
            preparar_pais(manifesto, "Brazil", RAIZ / "players_22.csv", CONVOCACOES, ALIASES, tmp_path)
            (diretorio_pais(tmp_path, "Brazil") / "resposta_bruta.json").write_text(
                json.dumps([_resposta_valida("Bento")]), encoding="utf-8"
            )
            validar_resposta_pais(manifesto, "Brazil", tmp_path)
            # simula uma proposta pendente de revisão
            manifesto["paises"]["Brazil"]["review_required"] = 1
            with self.assertRaises(ValueError):
                publicar_pais(
                    manifesto, "Brazil", RAIZ / "players_22.csv", tmp_path,
                    tmp_path / "registry" / "player_ids.csv", allow_partial=True,
                )

    def test_resumo_conta_convocados_e_presentes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifesto = self._manifesto(tmp_path)
            preparar_pais(manifesto, "Brazil", RAIZ / "players_22.csv", CONVOCACOES, ALIASES, tmp_path)
            resumo = consolidar_resumo(manifesto, tmp_path).iloc[0]
            self.assertEqual(resumo["pais"], "Brazil")
            self.assertEqual(resumo["convocados"], 3)
            self.assertGreaterEqual(resumo["presentes"], 1)

    def test_manifesto_cria_diretorio_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            iniciar_manifesto(tmp_path / "manifest.json", "Copa América", 2024, "2024-07-14", ["Brazil"])
            self.assertTrue((tmp_path / "registry").is_dir())

    def test_merge_final_agrega_publicados(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifesto = self._manifesto(tmp_path)
            preparar_pais(manifesto, "Brazil", RAIZ / "players_22.csv", CONVOCACOES, ALIASES, tmp_path)
            (diretorio_pais(tmp_path, "Brazil") / "resposta_bruta.json").write_text(
                json.dumps([_resposta_valida("Bento")]), encoding="utf-8"
            )
            validar_resposta_pais(manifesto, "Brazil", tmp_path)
            publicar_pais(
                manifesto, "Brazil", RAIZ / "players_22.csv", tmp_path,
                tmp_path / "registry" / "player_ids.csv",
            )
            self.assertEqual(manifesto["paises"]["Brazil"]["status"], STATUS_PUBLISHED)
            self.assertTrue(
                (diretorio_pais(tmp_path, "Brazil") / nome_snapshot("Brazil", 2024)).exists()
            )
            merged = mesclar_publicados(manifesto, tmp_path)
            self.assertEqual(len(merged), 1)

    def test_merge_final_sem_publicados_e_vazio(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifesto = iniciar_manifesto(
                tmp_path / "manifest.json", "Copa América", 2024, "2024-07-14", ["Brazil"]
            )
            self.assertEqual(manifesto["paises"]["Brazil"]["status"], STATUS_PENDING)
            self.assertTrue(mesclar_publicados(manifesto, tmp_path).empty)


if __name__ == "__main__":
    unittest.main()
