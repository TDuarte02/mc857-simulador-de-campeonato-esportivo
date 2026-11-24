"""Testes de integração da fase de grupos (Issue #34)."""
from dataclasses import replace
from itertools import combinations

import pytest

from python_prototype.dynamics import DynamicsConfig
from python_prototype.group_stage import (
    MatchResult,
    MatchStatus,
    TournamentPhase,
    TournamentState,
    group_standings,
    play_machine_match,
    simulate_group_stage,
    simulate_machine_match,
)
from python_prototype.match import MatchEventType, create_match, play_match
from python_prototype.tournament import (
    TournamentConfig,
    derive_seed,
    setup_tournament,
    synthetic_teams,
)


def make_state(seed=2026, **config_kwargs):
    config = TournamentConfig(seed=seed, **config_kwargs)
    return TournamentState.from_setup(setup_tournament(config, synthetic_teams(config)))


def finish(state, match_id, goals_a, goals_b):
    """Registra um placar manual (para testar a classificação isoladamente)."""
    record = state.matches[match_id]
    record.result = MatchResult(goals_a, goals_b, ())
    record.status = MatchStatus.ENCERRADA


def snapshot(state):
    return {
        mid: (r.status, None if r.result is None else (r.result.goals_a, r.result.goals_b, r.result.events))
        for mid, r in state.matches.items()
    }


# ------------------------------------------------------------
# Tabela de jogos
# ------------------------------------------------------------

def test_schedule_has_24_group_and_8_knockout_matches_all_pending():
    state = make_state()

    assert state.phase is TournamentPhase.GRUPOS
    assert len(state.matches) == 32
    assert all(r.status is MatchStatus.PENDENTE and r.result is None for r in state.matches.values())

    group_records = [r for r in state.matches.values() if r.phase is TournamentPhase.GRUPOS]
    knockout_records = [r for r in state.matches.values() if r.phase is TournamentPhase.MATA_MATA]
    assert len(group_records) == 24
    assert len(knockout_records) == 8
    assert all(r.team_a is None and r.team_b is None for r in knockout_records)

    assert [m for m in state.matches if m.startswith("G-A-")] == [
        "G-A-R1-1", "G-A-R1-2", "G-A-R2-1", "G-A-R2-2", "G-A-R3-1", "G-A-R3-2",
    ]


def test_each_team_meets_the_other_three_exactly_once():
    state = make_state()

    for group in state.groups:
        names = [t.name for t in group.teams]
        pairs = [frozenset((r.team_a, r.team_b)) for r in state.group_matches(group.name)]
        assert len(pairs) == 6
        assert set(pairs) == {frozenset(p) for p in combinations(names, 2)}


def test_rounds_follow_group_positions():
    state = make_state()
    group = state.group("B")
    t = [team.name for team in group.teams]   # índice 0..3 = posições 1..4

    got = {(r.round_number, r.match_id[-1]): (r.team_a, r.team_b) for r in state.group_matches("B")}

    assert got == {
        (1, "1"): (t[0], t[1]), (1, "2"): (t[2], t[3]),
        (2, "1"): (t[0], t[2]), (2, "2"): (t[1], t[3]),
        (3, "1"): (t[0], t[3]), (3, "2"): (t[1], t[2]),
    }


# ------------------------------------------------------------
# Partida de máquina
# ------------------------------------------------------------

def test_playing_a_match_records_the_result_once():
    state = make_state()

    record = play_machine_match(state, "G-A-R1-1")

    assert record.status is MatchStatus.ENCERRADA
    result = record.result
    goal_events = [e for e in result.events if e.type is MatchEventType.GOAL]
    assert result.goals_a == sum(e.team == "A" for e in goal_events)
    assert result.goals_b == sum(e.team == "B" for e in goal_events)


def test_playing_again_is_rejected_without_changing_the_state():
    state = make_state()
    play_machine_match(state, "G-A-R1-1")
    before = snapshot(state)

    with pytest.raises(ValueError, match="já foi jogada"):
        play_machine_match(state, "G-A-R1-1")

    assert snapshot(state) == before


def test_unknown_match_and_wrong_phase_are_rejected():
    state = make_state()
    with pytest.raises(ValueError, match="desconhecida"):
        play_machine_match(state, "G-Z-R9-9")

    state.phase = TournamentPhase.MATA_MATA
    before = snapshot(state)
    with pytest.raises(ValueError):
        play_machine_match(state, "G-A-R1-1")
    with pytest.raises(ValueError, match="fase de grupos"):
        simulate_group_stage(state)
    assert snapshot(state) == before


def test_match_result_does_not_depend_on_simulation_order():
    forward, backward = make_state(), make_state()
    ids = [
        mid for mid, r in forward.matches.items()
        if r.phase is TournamentPhase.GRUPOS
    ]

    for match_id in ids:
        play_machine_match(forward, match_id)
    for match_id in reversed(ids):
        play_machine_match(backward, match_id)

    assert snapshot(forward) == snapshot(backward)


def test_simulating_a_match_does_not_touch_the_state_and_is_repeatable():
    state = make_state()
    record = state.matches["G-C-R2-1"]
    before = snapshot(state)

    first = simulate_machine_match(state, record.team_a, record.team_b, record.match_id)
    second = simulate_machine_match(state, record.team_a, record.team_b, record.match_id)

    assert first == second
    assert snapshot(state) == before


def test_disabled_dynamics_matches_the_plain_match_engine():
    config = TournamentConfig(dynamics=DynamicsConfig.disabled())
    state = TournamentState.from_setup(setup_tournament(config, synthetic_teams(config)))

    for match_id in ("G-A-R1-1", "G-B-R2-2", "G-D-R3-1"):
        record = state.matches[match_id]
        a, b = state.teams[record.team_a], state.teams[record.team_b]
        plain = create_match(a.lineup, a.formation, b.lineup, b.formation)
        play_match(
            plain,
            seed=derive_seed(config.seed, match_id),
            attack_params=config.attack_params,
            recovery_control_bonus=config.recovery_control_bonus,
            possessions_per_cycle=config.possessions_per_cycle,
        )

        result = simulate_machine_match(state, record.team_a, record.team_b, match_id)

        assert (result.goals_a, result.goals_b) == (plain.score["A"], plain.score["B"])
        assert list(result.events) == plain.events


# ------------------------------------------------------------
# Fase de grupos completa
# ------------------------------------------------------------

def test_full_group_stage_is_consistent():
    state = make_state()

    tables = simulate_group_stage(state)

    assert all(
        r.status is MatchStatus.ENCERRADA
        for r in state.matches.values() if r.phase is TournamentPhase.GRUPOS
    )
    assert set(tables) == {"A", "B", "C", "D"}
    for name, table in tables.items():
        games = state.group_matches(name)
        decisive = sum(g.result.goals_a != g.result.goals_b for g in games)
        draws = len(games) - decisive
        assert table.is_final
        assert [row.played for row in table.rows] == [3, 3, 3, 3]
        assert sum(row.points for row in table.rows) == 3 * decisive + 2 * draws
        assert sum(row.goals_for for row in table.rows) == sum(row.goals_against for row in table.rows)
        points = [row.points for row in table.rows]
        assert points == sorted(points, reverse=True)


def test_simulating_the_group_stage_again_changes_nothing():
    state = make_state()
    first = simulate_group_stage(state)
    before = snapshot(state)

    assert simulate_group_stage(state) == first
    assert snapshot(state) == before


def test_same_seed_and_config_give_identical_scores_and_other_seed_differs():
    a, b, other = make_state(7), make_state(7), make_state(8)
    for s in (a, b, other):
        simulate_group_stage(s)

    assert snapshot(a) == snapshot(b)
    assert snapshot(a) != snapshot(other)


# ------------------------------------------------------------
# Classificação parcial e sorteio final no estado
# ------------------------------------------------------------

def test_standings_are_final_only_after_six_matches():
    state = make_state()
    ids = [m.match_id for m in state.group_matches("A")]

    for match_id in ids[:-1]:
        play_machine_match(state, match_id)
        assert not group_standings(state, "A").is_final

    play_machine_match(state, ids[-1])
    assert group_standings(state, "A").is_final


def test_final_tiebreak_lottery_is_reproducible_and_seed_dependent():
    state = make_state()
    for record in state.group_matches("A"):
        finish(state, record.match_id, 1, 1)        # todos empatados em tudo

    def order(s):
        return tuple(r.team for r in group_standings(s, "A").rows)

    assert order(state) == order(state)
    orders = {
        order(replace(state, config=replace(state.config, seed=seed))) for seed in range(30)
    }
    assert len(orders) > 1
    assert all(sorted(o) == sorted(order(state)) for o in orders)

