import os
import subprocess
import sys
from itertools import combinations
from pathlib import Path

import pytest

from copa_engine.rules import (
    GROUP_ROUNDS,
    KNOCKOUT_BRACKET,
    KNOCKOUT_ORDER,
    GroupGame,
    compute_standings,
    derive_seed,
    draw_groups,
)
from tests.helpers import NATIONS, synthetic_teams


# ------------------------------------------------------------
# Sementes
# ------------------------------------------------------------

def test_derive_seed_is_deterministic_and_label_sensitive():
    assert derive_seed(1, "a", 2) == derive_seed(1, "a", 2)
    assert derive_seed(1, "a") != derive_seed(2, "a")
    assert derive_seed(1, "a", "b") != derive_seed(1, "ab")
    assert derive_seed(1, "draw", 1) != derive_seed(1, "draw", 2)


def test_derive_seed_is_identical_across_processes():
    root = Path(__file__).resolve().parents[1]  # simulador/engine
    code = "from copa_engine.rules import derive_seed; print(derive_seed(2026, 'draw', 1))"
    outputs = {
        subprocess.run(
            [sys.executable, "-c", code], cwd=root, capture_output=True, text=True, check=True,
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
        ).stdout.strip()
        for hash_seed in ("1", "2", "random")
    }
    assert outputs == {str(derive_seed(2026, "draw", 1))}


@pytest.mark.parametrize("bad", ["x", 1.5, True, None])
def test_derive_seed_rejects_non_int_seed(bad):
    with pytest.raises(ValueError):
        derive_seed(bad, "x")


# ------------------------------------------------------------
# Sorteio
# ------------------------------------------------------------

def test_draw_gives_each_group_one_team_per_pot():
    draw = draw_groups(synthetic_teams(), seed=1)

    assert [g.name for g in draw.groups] == ["A", "B", "C", "D"]
    assert all(len(pot) == 4 for pot in draw.pots)
    for group in draw.groups:
        assert len(group.teams) == 4
        for position, team in enumerate(group.teams, start=1):
            assert team in draw.pots[position - 1]
            assert group.position_of(team.name) == position
    names = [t.name for g in draw.groups for t in g.teams]
    assert len(names) == 16 and len(set(names)) == 16


def test_pots_are_ordered_by_strength_with_name_tie_break():
    teams = synthetic_teams(ratings=[70] * 16)    # todos empatados: ordem alfabética

    draw = draw_groups(teams, seed=0)

    flat = [t.name for pot in draw.pots for t in pot]
    assert flat == sorted(NATIONS)

    strong = synthetic_teams()
    pots = draw_groups(strong, seed=0).pots
    assert min(t.strength for t in pots[0]) > max(t.strength for t in pots[1])


def test_draw_is_reproducible_and_respects_pots_for_any_seed():
    teams = synthetic_teams()

    assert draw_groups(teams, 7) == draw_groups(teams, 7)
    layouts = set()
    for seed in range(20):
        draw = draw_groups(teams, seed)
        layouts.add(tuple(tuple(t.name for t in g.teams) for g in draw.groups))
        for group in draw.groups:
            assert all(t in draw.pots[i] for i, t in enumerate(group.teams))
    assert len(layouts) > 1


def test_draw_rejects_wrong_number_of_teams_or_repeated_names():
    teams = synthetic_teams()
    with pytest.raises(ValueError):
        draw_groups(teams[:15], seed=1)
    with pytest.raises(ValueError):
        draw_groups((*teams[:15], teams[0]), seed=1)


# ------------------------------------------------------------
# Tabela de jogos
# ------------------------------------------------------------

def test_each_position_meets_the_other_three_once_two_matches_a_round():
    pairs = [frozenset(pair) for round_pairs in GROUP_ROUNDS for pair in round_pairs]

    assert len(GROUP_ROUNDS) == 3 and all(len(r) == 2 for r in GROUP_ROUNDS)
    assert set(pairs) == {frozenset(p) for p in combinations(range(1, 5), 2)}
    for round_pairs in GROUP_ROUNDS:
        assert sorted(p for pair in round_pairs for p in pair) == [1, 2, 3, 4]


def test_rounds_follow_group_positions():
    assert GROUP_ROUNDS == (((1, 2), (3, 4)), ((1, 3), (2, 4)), ((1, 4), (2, 3)))


# ------------------------------------------------------------
# Classificação
# ------------------------------------------------------------

TEAMS = ["A1", "A2", "A3", "A4"]


def test_standings_count_results_and_order_by_points_difference_and_goals():
    games = [GroupGame("A1", "A2", 2, 0), GroupGame("A3", "A4", 1, 1), GroupGame("A1", "A3", 0, 0)]

    rows = compute_standings("A", TEAMS, games, seed=1)

    assert [r.team for r in rows][0] == "A1"
    a1 = rows[0]
    assert (a1.played, a1.wins, a1.draws, a1.losses, a1.points, a1.goal_diff) == (2, 1, 1, 0, 4, 2)
    assert rows[-1].team == "A2" and rows[-1].points == 0


def test_head_to_head_breaks_ties_on_the_first_three_criteria():
    # A2 e A3: 3 pontos, saldo 0, 2 gols; A2 venceu A3.
    games = [GroupGame("A2", "A3", 2, 1), GroupGame("A1", "A2", 1, 0), GroupGame("A3", "A4", 1, 0)]

    for seed in range(10):
        rows = compute_standings("A", TEAMS, games, seed)
        assert [r.team for r in rows] == ["A1", "A2", "A3", "A4"]


def test_final_tiebreak_lottery_is_reproducible_and_seed_dependent():
    games = [GroupGame(a, b, 1, 1) for a, b in combinations(TEAMS, 2)]   # todos empatados em tudo

    def order(seed):
        return tuple(r.team for r in compute_standings("A", TEAMS, games, seed))

    assert order(3) == order(3)
    orders = {order(seed) for seed in range(30)}
    assert len(orders) > 1
    assert all(sorted(o) == TEAMS for o in orders)


def test_games_outside_the_group_are_rejected():
    with pytest.raises(ValueError):
        compute_standings("A", TEAMS, [GroupGame("A1", "B1", 1, 0)], seed=1)


# ------------------------------------------------------------
# Chaves do mata-mata
# ------------------------------------------------------------

def test_quarterfinals_cross_groups_and_the_bracket_closes():
    def describe(source):
        return (source.kind, source.ref, source.position)

    assert {m: tuple(describe(s) for s in KNOCKOUT_BRACKET[m]) for m in ("QF1", "QF2", "QF3", "QF4")} == {
        "QF1": (("group", "A", 1), ("group", "B", 2)),
        "QF2": (("group", "B", 1), ("group", "A", 2)),
        "QF3": (("group", "D", 1), ("group", "C", 2)),
        "QF4": (("group", "C", 1), ("group", "D", 2)),
    }
    assert [s.label for s in KNOCKOUT_BRACKET["SF1"]] == ["Vencedor QF1", "Vencedor QF2"]
    assert [s.label for s in KNOCKOUT_BRACKET["THIRD"]] == ["Perdedor SF1", "Perdedor SF2"]
    assert [s.label for s in KNOCKOUT_BRACKET["FINAL"]] == ["Vencedor SF1", "Vencedor SF2"]


def test_knockout_order_only_depends_on_earlier_matches():
    seen = set()
    for match_id in KNOCKOUT_ORDER:
        for source in KNOCKOUT_BRACKET[match_id]:
            if source.kind != "group":
                assert source.ref in seen
        seen.add(match_id)
    assert KNOCKOUT_ORDER == ("QF1", "QF2", "QF3", "QF4", "SF1", "SF2", "THIRD", "FINAL")
