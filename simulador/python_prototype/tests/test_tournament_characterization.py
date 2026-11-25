"""
Teste de caracterização do campeonato completo (Issue #36): congela o
resultado final (placares, pênaltis, tabelas e chaves) com seeds fixas, com e
sem usuário e com alterações de escalação. Falha se a ordem de consumo do RNG,
as sementes derivadas ou qualquer fórmula mudar, mesmo de forma sutil.

Para regenerar o snapshot (só após mudança INTENCIONAL de regra, já registrada
na spec):  defina UPDATE_GOLDEN = 1 e rode este arquivo uma vez.
"""
import json
from pathlib import Path

from python_prototype.game import TournamentGame
from python_prototype.match import MatchPhase
from python_prototype.tournament import (
    TournamentConfig,
    build_default_lineup,
    synthetic_teams,
)

UPDATE_GOLDEN = 0  # Defina para 1 quando quiser salvar o gabarito
GOLDEN = Path(__file__).parent / "golden" / "tournament_seeds.json"

FORMATION_442 = ("GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "CM", "ST", "ST")
# Ratings heterogêneos e fora de ordem, para gerar grupos e chaves variados.
RATINGS = [74, 61, 88, 67, 80, 70, 63, 85, 72, 90, 66, 78, 69, 83, 60, 76]

SCENARIOS = {
    "machine_only_seed_2026": dict(seed=2026, user=None, mode="auto"),
    "user_autoplay_seed_7": dict(seed=7, user="Brazil", mode="auto"),
    "user_halftime_changes_seed_42": dict(seed=42, user="Chile", mode="halftime"),
}


def _run(seed, user, mode):
    config = TournamentConfig(seed=seed)
    game = TournamentGame.create(config, synthetic_teams(config, RATINGS), user)
    while game.advance_to_user_match() is not None:
        session = game.start_user_match()
        if mode == "halftime":
            team = game.state.teams[user]
            session.change_lineup(*_alt(team))            # antes do início
            session.play_until_stop()
            if session.phase is MatchPhase.HALFTIME:
                session.change_lineup(team.lineup, team.formation)  # volta no intervalo
        session.play_to_end()
    game.simulate_to_end()
    return game.final_result()


def _alt(team):
    return build_default_lineup(team.name, team.squad, FORMATION_442), FORMATION_442


def test_full_tournament_matches_golden_snapshot():
    current = {name: _run(**spec) for name, spec in SCENARIOS.items()}

    if UPDATE_GOLDEN == 1:
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    assert GOLDEN.exists(), "Snapshot ausente: gere com UPDATE_GOLDEN = 1 e versione o arquivo."
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert json.loads(json.dumps(current)) == expected
