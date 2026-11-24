"""Testes do mata-mata (Issue #35): chaves, pênaltis no torneio e torneio completo."""
import random
from functools import lru_cache

import pytest

from python_prototype.group_stage import (
    MatchResult,
    MatchStatus,
    TournamentPhase,
    TournamentState,
    play_machine_match,
    simulate_group_stage,
    simulate_machine_match,
)
from python_prototype.knockout import (
    KNOCKOUT_ORDER,
    build_knockout_schedule,
    final_ranking,
    match_loser,
    match_winner,
    play_knockout_match,
    simulate_knockout,
    start_knockout,
    update_knockout_slots,
)
from python_prototype.match import MatchEventType
from python_prototype.penalties import PenaltyConfig, simulate_penalty_shootout
from python_prototype.tournament import (
    TournamentConfig,
    derive_seed,
    setup_tournament,
    synthetic_teams,
)

EQUAL = [70] * 16


def make_state(seed=2026, ratings=None, **config_kwargs):
    config = TournamentConfig(seed=seed, **config_kwargs)
    teams = synthetic_teams(config, ratings)
    return TournamentState.from_setup(setup_tournament(config, teams))


def finish(state, match_id, goals_a, goals_b):
    record = state.matches[match_id]
    record.result = MatchResult(goals_a, goals_b, ())
    record.status = MatchStatus.ENCERRADA


def finish_group(state, name):
    """Posição menor sempre vence (team_a tem a posição menor): ordem = 1, 2, 3, 4."""
    for record in state.group_matches(name):
        finish(state, record.match_id, 1, 0)


def finish_all_groups(state):
    for group in state.groups:
        finish_group(state, group.name)


def team_at(state, group, position):
    return state.group(group).teams[position - 1].name


def snapshot(state):
    return (
        state.phase,
        {m: (r.team_a, r.team_b, r.status, r.result) for m, r in state.matches.items()},
    )


def goal_count(result, team):
    return sum(e.type is MatchEventType.GOAL and e.team == team for e in result.events)


# ------------------------------------------------------------
# Chaves
# ------------------------------------------------------------

def test_schedule_has_8_matches_with_slot_descriptions_and_no_teams():
    records = build_knockout_schedule()

    assert [r.match_id for r in records] == [
        "QF1", "QF2", "QF3", "QF4", "SF1", "SF2", "THIRD", "FINAL",
    ]
    assert all(
        r.phase is TournamentPhase.MATA_MATA and r.team_a is None and r.team_b is None
        and r.status is MatchStatus.PENDENTE
        for r in records
    )
    slots = {r.match_id: (r.slot_a, r.slot_b) for r in records}
    assert slots == {
        "QF1": ("1º A", "2º B"), "QF2": ("1º B", "2º A"),
        "QF3": ("1º D", "2º C"), "QF4": ("1º C", "2º D"),
        "SF1": ("Vencedor QF1", "Vencedor QF2"),
        "SF2": ("Vencedor QF3", "Vencedor QF4"),
        "THIRD": ("Perdedor SF1", "Perdedor SF2"),
        "FINAL": ("Vencedor SF1", "Vencedor SF2"),
    }


def test_quarterfinal_slots_follow_group_standings():
    state = make_state()
    finish_all_groups(state)

    update_knockout_slots(state)

    def pair(match_id):
        r = state.matches[match_id]
        return r.team_a, r.team_b

    assert pair("QF1") == (team_at(state, "A", 1), team_at(state, "B", 2))
    assert pair("QF2") == (team_at(state, "B", 1), team_at(state, "A", 2))
    assert pair("QF3") == (team_at(state, "D", 1), team_at(state, "C", 2))
    assert pair("QF4") == (team_at(state, "C", 1), team_at(state, "D", 2))
    assert pair("SF1") == pair("SF2") == pair("THIRD") == pair("FINAL") == (None, None)


def test_slots_are_filled_as_each_group_finishes():
    state = make_state()
    finish_group(state, "A")

    update_knockout_slots(state)

    qf1, qf2, qf3 = (state.matches[m] for m in ("QF1", "QF2", "QF3"))
    assert (qf1.team_a, qf1.team_b) == (team_at(state, "A", 1), None)
    assert (qf2.team_a, qf2.team_b) == (None, team_at(state, "A", 2))
    assert (qf3.team_a, qf3.team_b) == (None, None)

    finish_group(state, "B")
    update_knockout_slots(state)
    assert qf1.team_b == team_at(state, "B", 2)
    assert qf2.team_a == team_at(state, "B", 1)


def test_start_knockout_requires_finished_group_stage():
    state = make_state()
    before = snapshot(state)

    with pytest.raises(ValueError, match="grupos"):
        start_knockout(state)

    assert snapshot(state) == before and len(state.matches) == 24


def test_start_knockout_creates_the_bracket_and_changes_phase():
    state = make_state()
    finish_all_groups(state)

    start_knockout(state)

    assert state.phase is TournamentPhase.MATA_MATA
    assert len(state.matches) == 32
    with pytest.raises(ValueError):
        start_knockout(state)


# ------------------------------------------------------------
# Partidas
# ------------------------------------------------------------

def test_match_with_undefined_slot_cannot_be_played():
    state = make_state()
    finish_all_groups(state)
    start_knockout(state)
    before = snapshot(state)

    for match_id in ("SF1", "THIRD", "FINAL"):
        with pytest.raises(ValueError, match="indefinida"):
            play_knockout_match(state, match_id)

    assert snapshot(state) == before


def test_match_cannot_be_played_before_the_knockout_phase_or_twice():
    state = make_state()
    finish_all_groups(state)
    update_knockout_slots(state)                       # QF1 definida, mas ainda em GRUPOS
    with pytest.raises(ValueError, match="mata-mata"):
        play_knockout_match(state, "QF1")

    start_knockout(state)
    play_knockout_match(state, "QF1")
    before = snapshot(state)
    with pytest.raises(ValueError, match="já foi jogada"):
        play_knockout_match(state, "QF1")
    assert snapshot(state) == before


def test_group_match_api_rejects_knockout_matches_and_vice_versa():
    state = make_state()
    finish_all_groups(state)
    start_knockout(state)

    with pytest.raises(ValueError):
        play_machine_match(state, "QF1")
    with pytest.raises(ValueError, match="não é do mata-mata"):
        play_knockout_match(state, "G-A-R1-1")


def test_winners_and_losers_fill_semifinals_third_place_and_final():
    state = make_state()
    finish_all_groups(state)
    start_knockout(state)

    for match_id in ("QF1", "QF2", "QF3", "QF4"):
        play_knockout_match(state, match_id)
    m = state.matches
    assert (m["SF1"].team_a, m["SF1"].team_b) == (match_winner(m["QF1"]), match_winner(m["QF2"]))
    assert (m["SF2"].team_a, m["SF2"].team_b) == (match_winner(m["QF3"]), match_winner(m["QF4"]))

    play_knockout_match(state, "SF1")
    assert m["THIRD"].team_a == match_loser(m["SF1"]) and m["THIRD"].team_b is None
    play_knockout_match(state, "SF2")
    assert m["THIRD"].team_b == match_loser(m["SF2"])
    assert (m["FINAL"].team_a, m["FINAL"].team_b) == (
        match_winner(m["SF1"]), match_winner(m["SF2"]),
    )
    assert state.phase is TournamentPhase.MATA_MATA


def test_quarterfinal_results_do_not_depend_on_simulation_order():
    forward, backward = make_state(), make_state()
    for s in (forward, backward):
        finish_all_groups(s)
        start_knockout(s)

    for match_id in ("QF1", "QF2", "QF3", "QF4"):
        play_knockout_match(forward, match_id)
    for match_id in ("QF4", "QF3", "QF2", "QF1"):
        play_knockout_match(backward, match_id)

    assert snapshot(forward) == snapshot(backward)


def test_penalty_config_does_not_change_90_minute_results():
    default = make_state()
    other = make_state(penalties=PenaltyConfig(p_base=0.6, s=0.1, p_min=0.3, p_max=0.8))
    for s in (default, other):
        finish_all_groups(s)
        start_knockout(s)
        for match_id in ("QF1", "QF2", "QF3", "QF4"):
            play_knockout_match(s, match_id)

    for match_id in ("QF1", "QF2", "QF3", "QF4"):
        a, b = default.matches[match_id].result, other.matches[match_id].result
        assert (a.goals_a, a.goals_b, a.events) == (b.goals_a, b.goals_b, b.events)


def test_invalid_penalty_config_type_is_rejected():
    with pytest.raises(ValueError):
        TournamentConfig(penalties="x")


# ------------------------------------------------------------
# Pênaltis no torneio
# ------------------------------------------------------------

@lru_cache(maxsize=None)
def _finished_tournament(seed):
    state = make_state(seed, EQUAL)
    simulate_group_stage(state)
    simulate_knockout(state)
    return state


def _tied_matches():
    found = []
    for seed in range(8):
        state = _finished_tournament(seed)
        found += [
            (state, m) for m in KNOCKOUT_ORDER
            if state.matches[m].result.goals_a == state.matches[m].result.goals_b
        ]
    return found


@pytest.mark.parametrize("seed", range(5))
def test_no_knockout_match_ends_without_a_winner(seed):
    state = _finished_tournament(seed)

    for match_id in KNOCKOUT_ORDER:
        record = state.matches[match_id]
        result = record.result
        assert match_winner(record) in (record.team_a, record.team_b)
        # o placar dos 90 minutos é exatamente o dos gols nos eventos
        assert result.goals_a == goal_count(result, "A")
        assert result.goals_b == goal_count(result, "B")
        if result.goals_a == result.goals_b:
            assert result.penalties is not None
            assert result.penalties.goals_a != result.penalties.goals_b
        else:
            assert result.penalties is None


def test_tied_matches_keep_the_90_minute_score_and_use_their_own_generator():
    tied = _tied_matches()
    assert tied, "esperava ao menos um empate em 8 torneios de times iguais"

    for state, match_id in tied:
        record = state.matches[match_id]
        plain = simulate_machine_match(state, record.team_a, record.team_b, match_id)
        assert (record.result.goals_a, record.result.goals_b) == (plain.goals_a, plain.goals_b)
        assert record.result.events == plain.events

        a, b = state.teams[record.team_a], state.teams[record.team_b]
        expected = simulate_penalty_shootout(
            a.lineup, b.lineup, state.config.penalties,
            rng=random.Random(derive_seed(state.config.seed, match_id, "penalties")),
        )
        assert record.result.penalties == expected


# ------------------------------------------------------------
# Torneio completo
# ------------------------------------------------------------

def test_full_machine_tournament_has_32_matches_and_a_champion():
    state = make_state()
    simulate_group_stage(state)

    ranking = simulate_knockout(state)

    assert len(state.matches) == 32
    assert all(r.status is MatchStatus.ENCERRADA for r in state.matches.values())
    assert state.phase is TournamentPhase.ENCERRADO
    assert len({ranking.champion, ranking.runner_up, ranking.third, ranking.fourth}) == 4
    assert ranking.champion == match_winner(state.matches["FINAL"])
    assert ranking.runner_up == match_loser(state.matches["FINAL"])
    assert ranking == final_ranking(state)


def test_final_ranking_requires_finished_tournament():
    with pytest.raises(ValueError, match="não terminou"):
        final_ranking(make_state())


def test_simulate_knockout_requires_finished_group_stage():
    state = make_state()
    before = snapshot(state)

    with pytest.raises(ValueError, match="grupos"):
        simulate_knockout(state)

    assert snapshot(state) == before


def test_simulating_the_knockout_again_changes_nothing():
    state = make_state()
    simulate_group_stage(state)
    first = simulate_knockout(state)
    before = snapshot(state)

    assert simulate_knockout(state) == first
    assert snapshot(state) == before


def test_finished_tournament_rejects_new_matches():
    state = make_state()
    simulate_group_stage(state)
    simulate_knockout(state)
    before = snapshot(state)

    with pytest.raises(ValueError, match="já foi jogada"):
        play_knockout_match(state, "FINAL")
    with pytest.raises(ValueError, match="já foi jogada"):
        play_machine_match(state, "G-A-R1-1")

    assert snapshot(state) == before


def test_tournament_is_reproducible_with_same_seed():
    def run(seed):
        state = make_state(seed)
        simulate_group_stage(state)
        simulate_knockout(state)
        return state

    a, b, other = run(7), run(7), run(8)

    assert snapshot(a) == snapshot(b)
    assert snapshot(a) != snapshot(other)
