import unittest

import pandas as pd

from pipeline.ancoragem import (
    ANCORA_TOPO_K,
    BANDA_TOPO,
    BONUS_PADRAO,
    calcular_ancoras,
    calcular_deslocamento,
    deslocamentos_por_pais,
    reescalar_lendas,
)


def _base():
    """Base sintética: Brasil forte, Bolívia fraca."""
    linhas = []
    for i, ov in enumerate([91, 89, 88, 70, 68]):          # Brasil: top3 = 89.33
        linhas.append({"nationality_name": "Brazil", "overall": ov, "short_name": f"B{i}", "player_positions": "CM"})
    for i, ov in enumerate([71, 70, 70, 60]):              # Bolívia: top3 = 70.33
        linhas.append({"nationality_name": "Bolivia", "overall": ov, "short_name": f"V{i}", "player_positions": "CM"})
    return pd.DataFrame(linhas)


def _pool():
    return pd.DataFrame([
        {"nationality_name": "Brazil", "camada": "historico", "fonte_atributos": "inferencia",
         "short_name": "Lenda BR", "overall": 96, "pace": 90, "goalkeeping_reflexes": 50, "sofifa_id": -1, "age": 27, "confianca": 0.7},
        {"nationality_name": "Bolivia", "camada": "historico", "fonte_atributos": "inferencia",
         "short_name": "Lenda BO", "overall": 96, "pace": 90, "goalkeeping_reflexes": 50, "sofifa_id": -2, "age": 27, "confianca": 0.7},
        {"nationality_name": "Brazil", "camada": "historico", "fonte_atributos": "ea_fc_icon",
         "short_name": "Icone BR", "overall": 97, "pace": 91, "goalkeeping_reflexes": 50, "sofifa_id": -3, "age": 27, "confianca": 0.9},
        {"nationality_name": "Brazil", "camada": "base_22", "fonte_atributos": None,
         "short_name": "Base BR", "overall": 91, "pace": 85, "goalkeeping_reflexes": 50, "sofifa_id": 1, "age": 30, "confianca": None},
        {"nationality_name": "Brazil", "camada": "convocado_2024", "fonte_atributos": None,
         "short_name": "Convocado BR", "overall": 80, "pace": 78, "goalkeeping_reflexes": 50, "sofifa_id": -4, "age": 24, "confianca": 0.8},
    ])


class AncoragemTest(unittest.TestCase):
    def test_ancora_e_a_media_dos_k_melhores(self):
        ancoras = calcular_ancoras(_base(), k=3)
        self.assertAlmostEqual(ancoras["Brazil"], (91 + 89 + 88) / 3, places=6)
        self.assertAlmostEqual(ancoras["Bolivia"], (71 + 70 + 70) / 3, places=6)

    def test_ancora_ignora_estrela_isolada(self):
        # Uma estrela muito acima do resto não deve puxar a âncora do país.
        base = pd.concat([_base(), pd.DataFrame([
            {"nationality_name": "Costa Rica", "overall": 88, "short_name": "Estrela", "player_positions": "GK"},
            {"nationality_name": "Costa Rica", "overall": 70, "short_name": "C1", "player_positions": "CB"},
            {"nationality_name": "Costa Rica", "overall": 69, "short_name": "C2", "player_positions": "CB"},
            {"nationality_name": "Costa Rica", "overall": 68, "short_name": "C3", "player_positions": "CB"},
        ])], ignore_index=True)
        ancoras = calcular_ancoras(base, k=3)
        self.assertAlmostEqual(ancoras["Costa Rica"], (88 + 70 + 69) / 3, places=6)
        self.assertLess(ancoras["Costa Rica"], 88)

    def test_deslocamento_para_que_o_topo_caia_na_ancora_mais_bonus(self):
        # Brasil forte -> desloca pouco; Bolívia fraca -> desloca muito.
        self.assertAlmostEqual(calcular_deslocamento(89.33), BANDA_TOPO - 89.33 - BONUS_PADRAO, places=6)
        d_br = calcular_deslocamento(89.33)
        d_bo = calcular_deslocamento(70.33)
        self.assertLess(d_br, d_bo)

    def test_deslocamento_sem_ancora_e_zero(self):
        self.assertEqual(calcular_deslocamento(None), 0.0)

    def test_deslocamentos_por_pais(self):
        deslocamentos = deslocamentos_por_pais(_base(), k=3)
        self.assertIn("Brazil", deslocamentos)
        self.assertIn("Bolivia", deslocamentos)
        self.assertLess(deslocamentos["Brazil"], deslocamentos["Bolivia"])

    def test_reescala_so_as_lendas_estimadas(self):
        pool, _ = reescalar_lendas(_pool(), _base())
        por_nome = pool.set_index("short_name")

        # Lenda estimada da Bolívia: desce o deslocamento do país.
        self.assertEqual(por_nome.loc["Lenda BO", "overall"], 96 - round(calcular_deslocamento(70.33)))
        # Lenda estimada do Brasil: desce pouco.
        self.assertEqual(por_nome.loc["Lenda BR", "overall"], 96 - round(calcular_deslocamento((91 + 89 + 88) / 3)))
        # Nota real (EA FC Icon) fica intacta.
        self.assertEqual(por_nome.loc["Icone BR", "overall"], 97)
        # Outras camadas ficam intactas.
        self.assertEqual(por_nome.loc["Base BR", "overall"], 91)
        self.assertEqual(por_nome.loc["Convocado BR", "overall"], 80)

    def test_nao_desloca_colunas_de_rastreio(self):
        pool, _ = reescalar_lendas(_pool(), _base())
        por_nome = pool.set_index("short_name")
        # sofifa_id, age e confianca não são atributos.
        self.assertEqual(por_nome.loc["Lenda BO", "sofifa_id"], -2)
        self.assertEqual(por_nome.loc["Lenda BO", "age"], 27)
        self.assertAlmostEqual(por_nome.loc["Lenda BO", "confianca"], 0.7)

    def test_atributos_acompanham_o_overall(self):
        pool, _ = reescalar_lendas(_pool(), _base())
        por_nome = pool.set_index("short_name")
        # A mesma queda do overall se aplica ao pace.
        self.assertEqual(por_nome.loc["Lenda BR", "pace"], 90 - round(calcular_deslocamento((91 + 89 + 88) / 3)))

    def test_preserva_o_contrato_de_colunas(self):
        original = _pool()
        pool, _ = reescalar_lendas(original, _base())
        self.assertEqual(list(pool.columns), list(original.columns))
        self.assertEqual(len(pool), len(original))

    def test_k_invalido_levanta_erro(self):
        with self.assertRaises(ValueError):
            calcular_ancoras(_base(), k=0)

    def test_funciona_em_snapshot_sem_coluna_camada(self):
        # Os snapshots por país usam `is_historico`, não `camada`.
        snapshot = _pool().drop(columns=["camada"])
        snapshot["is_historico"] = [True, True, True, False, False]
        reescalado, _ = reescalar_lendas(snapshot, _base())
        por_nome = reescalado.set_index("short_name")

        self.assertLess(por_nome.loc["Lenda BO", "overall"], 96)     # lenda estimada desloca
        self.assertEqual(por_nome.loc["Icone BR", "overall"], 97)    # nota real intacta
        self.assertEqual(por_nome.loc["Base BR", "overall"], 91)     # não-histórico intacto
        self.assertEqual(por_nome.loc["Convocado BR", "overall"], 80)

    def test_sem_coluna_de_camada_levanta_erro(self):
        with self.assertRaises(ValueError):
            reescalar_lendas(_pool().drop(columns=["camada"]), _base())


if __name__ == "__main__":
    unittest.main()
