import random

import pytest
import copy
import math

from python_prototype.collective_attributes import Player
from python_prototype.match import (
    HALFTIME_MINUTE,
    FULL_TIME_MINUTE,
    MODIFIER_KEYS,
    CYCLE_MINUTES,
    CYCLES_PER_MATCH,
    MatchEventType,
    MatchPhase,
    PendingControlBonus,
    change_lineup,
    create_match,
    play_match,
    run_cycle,
    start_second_half,
)

from python_prototype.tests.helpers import (
    FORMATION_433,
    FORMATION_442,
    POSITIONS_442,
    squad,
    ScriptedRandom,
)


def new_match(rating_a: int = 75, rating_b: int = 65):
    return create_match(squad("A", rating_a), FORMATION_433, squad("B", rating_b), FORMATION_433)


def count(state, event_type):
    return sum(1 for e in state.events if e.type is event_type)


def test_each_cycle_advances_clock_by_exactly_15_minutes():
    state = new_match()
    rng = random.Random(1)

    for expected in (15, 30, 45):
        result = run_cycle(state, rng)
        assert state.clock == expected
        assert result.end_minute - result.start_minute == CYCLE_MINUTES


@pytest.mark.parametrize("seed", range(50))
def test_regular_match_ends_after_six_cycles(seed):
    state = new_match()
    results = play_match(state, seed=seed)

    assert len(results) == CYCLES_PER_MATCH
    assert state.cycle_index == 6
    assert state.clock == 90
    assert state.phase is MatchPhase.FINISHED
    assert count(state, MatchEventType.FULL_TIME) == 1


@pytest.mark.parametrize("seed", range(50))
def test_score_is_updated_once_per_goal(seed):
    state = new_match()
    results = play_match(state, seed=seed)

    goals = [r for r in results if r.is_goal]
    assert sum(state.score.values()) == len(goals)
    assert count(state, MatchEventType.GOAL) == len(goals)
    for team in ("A", "B"):
        assert state.score[team] == sum(1 for r in goals if r.scorer == team)


@pytest.mark.parametrize("seed", range(30))
def test_only_md3_winner_can_score(seed):
    state = new_match()
    for result in play_match(state, seed=seed):
        assert result.attacking_team == result.md3.winner
        assert result.scorer in (None, result.md3.winner)


def test_cannot_run_cycles_after_match_ends():
    state = new_match()
    play_match(state, seed=3)
    score = dict(state.score)
    events = len(state.events)

    with pytest.raises(ValueError, match="encerrada"):
        run_cycle(state, seed=1)

    assert state.clock == 90
    assert state.score == score
    assert len(state.events) == events


def test_halftime_is_recognized_after_45_minutes():
    state = new_match()
    rng = random.Random(5)
    for _ in range(3):
        run_cycle(state, rng)

    assert state.phase is MatchPhase.HALFTIME
    assert state.clock == 45
    assert count(state, MatchEventType.HALFTIME) == 1
    with pytest.raises(ValueError, match="intervalo"):
        run_cycle(state, rng)


def test_lineup_change_allowed_only_at_halftime():
    state = new_match()
    with pytest.raises(ValueError, match="intervalo"):
        change_lineup(state, "A", squad("N", 80), FORMATION_442)

    rng = random.Random(9)
    for _ in range(3):
        run_cycle(state, rng)
    before = state.teams["A"].base

    change_lineup(state, "A", squad("N", 90, POSITIONS_442), FORMATION_442)
    assert state.teams["A"].base != before
    assert state.teams["A"].formation == tuple(FORMATION_442)

    start_second_half(state)
    assert state.phase is MatchPhase.SECOND_HALF
    with pytest.raises(ValueError, match="intervalo"):
        change_lineup(state, "A", squad("M", 80), FORMATION_433)


def test_lineup_change_affects_following_cycles_through_attributes():
    state = new_match(rating_a=70, rating_b=70)
    rng = random.Random(0)
    for _ in range(3):
        run_cycle(state, rng)
    change_lineup(state, "A", squad("N", 100), FORMATION_433)
    start_second_half(state)

    assert state.teams["A"].effective().control > state.teams["B"].effective().control
    for _ in range(3):
        run_cycle(state, rng)
    assert state.is_finished


def test_invalid_lineup_change_does_not_alter_state():
    state = new_match()
    rng = random.Random(2)
    for _ in range(3):
        run_cycle(state, rng)
    original = state.teams["A"]

    with pytest.raises(ValueError):
        change_lineup(state, "A", squad("N", 80)[:-1], FORMATION_433)

    assert state.teams["A"] is original


def test_cycles_do_not_alter_team_state_without_explicit_effects():
    state = new_match()
    before = {t: (s.base, dict(s.modifiers)) for t, s in state.teams.items()}
    play_match(state, seed=11)

    assert {t: (s.base, dict(s.modifiers)) for t, s in state.teams.items()} == before


def test_modifiers_are_the_explicit_channel_between_cycles():
    state = new_match(70, 70)
    state.teams["A"].modifiers["control"] = 30.0

    assert state.teams["A"].effective().control == pytest.approx(100.0)  # clamp
    assert state.teams["B"].effective().control == pytest.approx(
        state.teams["B"].base.control
    )


def test_match_is_reproducible_with_seed():
    first, second = new_match(), new_match()
    play_match(first, seed=42)
    play_match(second, seed=42)

    assert first.score == second.score
    assert first.events == second.events


def test_rng_and_seed_cannot_be_used_together():
    state = new_match()
    with pytest.raises(ValueError):
        run_cycle(state, random.Random(1), seed=1)
    assert state.clock == 0


def test_stronger_team_scores_more_over_many_matches():
    totals = {"A": 0, "B": 0}
    for seed in range(200):
        state = new_match(90, 40)
        play_match(state, seed=seed)
        totals["A"] += state.score["A"]
        totals["B"] += state.score["B"]

    assert totals["A"] > totals["B"]

def _snapshot(state):
    return (
        state.clock, state.cycle_index, state.phase,
        dict(state.score), list(state.events),
        {t: dict(s.modifiers) for t, s in state.teams.items()},
    )


def test_failed_attack_simulation_leaves_state_unchanged(monkeypatch):
    state = new_match()
    before = _snapshot(state)

    def boom(*args, **kwargs):
        raise ValueError("falha simulada")

    monkeypatch.setattr("python_prototype.match.simulate_attack_sequence", boom)

    with pytest.raises(ValueError, match="falha simulada"):
        run_cycle(state, seed=1)

    assert _snapshot(state) == before


def test_failed_cycle_mid_match_leaves_state_unchanged(monkeypatch):
    state = new_match()
    rng = random.Random(7)
    run_cycle(state, rng)
    run_cycle(state, rng)          # clock = 30, próximo ciclo cruza o intervalo
    before = copy.deepcopy(_snapshot(state))

    monkeypatch.setattr(
        "python_prototype.match.simulate_attack_sequence",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("falha simulada")),
    )

    with pytest.raises(ValueError):
        run_cycle(state, rng)

    assert _snapshot(state) == before
    assert state.phase is MatchPhase.FIRST_HALF   # HALFTIME não foi registrado


def test_cycle_event_order_is_stable():
    state = new_match()
    run_cycle(state, random.Random(3))

    types = [e.type for e in state.events]
    assert types[:2] == [MatchEventType.MD3_RESULT, MatchEventType.ATTACK_SEQUENCE]
    assert types[2] in (MatchEventType.GOAL, MatchEventType.POSSESSION_LOST)

def test_change_lineup_with_mismatched_formation_does_not_alter_state():
    state = new_match()
    rng = random.Random(2)
    for _ in range(3):
        run_cycle(state, rng)
    original = state.teams["A"]
    events = len(state.events)

    with pytest.raises(ValueError, match="não corresponde à formação"):
        change_lineup(state, "A", squad("N", 80), FORMATION_442)   # jogadores 4-3-3

    assert state.teams["A"] is original
    assert len(state.events) == events
    assert state.phase is MatchPhase.HALFTIME


def test_create_match_rejects_lineup_not_matching_formation():
    with pytest.raises(ValueError, match="não corresponde à formação"):
        create_match(squad("A", 70), FORMATION_442, squad("B", 70), FORMATION_433)

def test_play_match_rng_and_seed_cannot_be_used_together():
    state = new_match()
    with pytest.raises(ValueError):
        play_match(state, random.Random(1), seed=1)
    assert state.clock == 0

def test_time_constants_are_derived_from_cycles():
    assert HALFTIME_MINUTE == 45
    assert FULL_TIME_MINUTE == 90


def test_clock_is_derived_from_cycle_index():
    state = new_match()
    assert state.clock == 0

    run_cycle(state, random.Random(1))

    assert state.cycle_index == 1
    assert state.clock == CYCLE_MINUTES
    with pytest.raises(AttributeError):
        state.clock = 30


def test_play_match_on_finished_match_raises_and_keeps_state():
    state = new_match()
    play_match(state, seed=3)
    score, events = dict(state.score), len(state.events)

    with pytest.raises(ValueError, match="encerrada"):
        play_match(state, seed=4)

    assert state.score == score
    assert len(state.events) == events


def test_play_match_resumes_from_halftime():
    state = new_match()
    rng = random.Random(5)
    for _ in range(3):
        run_cycle(state, rng)

    results = play_match(state, rng)

    assert len(results) == 3
    assert state.is_finished
    assert count(state, MatchEventType.SECOND_HALF_START) == 1


def test_events_carry_structured_data_and_derived_detail():
    state = new_match()
    result = run_cycle(state, random.Random(3))
    md3_event, attack_event = state.events[0], state.events[1]

    assert md3_event.data == {"wins_a": result.md3.wins_a, "wins_b": result.md3.wins_b}
    assert attack_event.data == {"attempts": result.attack.attempts}
    assert md3_event.detail == f"MD3 {result.md3.wins_a}x{result.md3.wins_b}"
    assert attack_event.detail == f"{result.attack.attempts} tentativa(s)"


def test_outcome_events_have_no_data_and_empty_detail():
    state = new_match()
    run_cycle(state, random.Random(3))
    outcome = state.events[2]

    assert outcome.type in (MatchEventType.GOAL, MatchEventType.POSSESSION_LOST)
    assert outcome.data == {}
    assert outcome.detail == ""

def test_default_modifiers_use_the_declared_keys():
    state = new_match()
    assert set(state.teams["A"].modifiers) == set(MODIFIER_KEYS)


def test_unknown_modifier_key_is_rejected_without_altering_state():
    state = new_match()
    state.teams["A"].modifiers["atack"] = 5.0
    before = _snapshot(state)

    with pytest.raises(ValueError, match="atack"):
        run_cycle(state, seed=1)

    assert _snapshot(state) == before


def test_missing_modifier_key_is_rejected():
    state = new_match()
    del state.teams["B"].modifiers["control"]

    with pytest.raises(ValueError, match="control"):
        run_cycle(state, seed=1)

    assert state.clock == 0


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_modifier_is_rejected(bad):
    state = new_match()
    state.teams["A"].modifiers["attack"] = bad

    with pytest.raises(ValueError, match="finito"):
        run_cycle(state, seed=1)

    assert state.clock == 0

def test_cycle_runs_when_all_effective_attributes_are_zero():
    state = new_match()
    for team in state.teams.values():
        team.modifiers.update(attack=-100.0, defense=-100.0, control=-100.0)

    assert all(
        (e.attack, e.defense, e.control) == (0.0, 0.0, 0.0)
        for e in (t.effective() for t in state.teams.values())
    )

    results = play_match(state, seed=1)

    assert len(results) == CYCLES_PER_MATCH
    assert state.is_finished

@pytest.mark.parametrize("seed", range(20))
def test_event_log_invariants_for_complete_match(seed):
    state = new_match()
    play_match(state, seed=seed)
    types = [e.type for e in state.events]

    assert types.count(MatchEventType.MD3_RESULT) == CYCLES_PER_MATCH
    assert types.count(MatchEventType.ATTACK_SEQUENCE) == CYCLES_PER_MATCH
    assert (
        types.count(MatchEventType.GOAL) + types.count(MatchEventType.POSSESSION_LOST)
        == CYCLES_PER_MATCH
    )
    for once in (
        MatchEventType.HALFTIME,
        MatchEventType.SECOND_HALF_START,
        MatchEventType.FULL_TIME,
    ):
        assert types.count(once) == 1
    assert (
        types.index(MatchEventType.HALFTIME)
        < types.index(MatchEventType.SECOND_HALF_START)
        < types.index(MatchEventType.FULL_TIME)
    )
    assert types[-1] is MatchEventType.FULL_TIME
    minutes = [e.minute for e in state.events]
    assert minutes == sorted(minutes)


# --- Ciclo completo com RNG roteirizado (times iguais: MD3 e ataque com q = 0.5) ---
# Sorteios: 6 da MD3 (3 duelos x 2 séries), depois 1 por tentativa de ataque.
# q = 0.5 => P_G = 0.15, P_C(1) = 0.25 (continuação para sorteio em [0.15, 0.40)).

def test_scripted_cycle_ending_in_goal():
    state = new_match(70, 70)
    rng = ScriptedRandom([0.1] * 6 + [0.01])

    result = run_cycle(state, rng)

    assert result.attacking_team == "A"
    assert result.scorer == "A"
    assert result.attack.attempts == 1
    assert state.score == {"A": 1, "B": 0}
    assert [e.type for e in state.events] == [
        MatchEventType.MD3_RESULT,
        MatchEventType.ATTACK_SEQUENCE,
        MatchEventType.GOAL,
    ]
    assert state.events[0].data == {"wins_a": 2, "wins_b": 0}
    assert rng.remaining == 0


def test_scripted_cycle_ending_in_possession_lost():
    state = new_match(70, 70)
    rng = ScriptedRandom([0.9] * 6 + [0.99])

    result = run_cycle(state, rng)

    assert result.attacking_team == "B"
    assert result.scorer is None
    assert state.score == {"A": 0, "B": 0}
    assert state.events[0].data == {"wins_a": 0, "wins_b": 2}
    assert state.events[-1].type is MatchEventType.POSSESSION_LOST
    assert state.events[-1].team == "B"
    assert rng.remaining == 0


def test_scripted_cycle_with_continuation_then_goal():
    state = new_match(70, 70)
    rng = ScriptedRandom([0.1] * 6 + [0.20, 0.01])

    result = run_cycle(state, rng)

    assert result.attack.attempts == 2
    assert result.scorer == "A"
    assert state.events[1].data == {"attempts": 2}
    assert rng.remaining == 0

# Times 70x70: Controle igual. Com bônus 5 para A na 1ª MD5, p(A) = 75/145 ≈ 0.517,
# então o sorteio 0.51 dá vitória a A só nessa MD5 (sem bônus, 0.51 >= 0.5 => B).

def test_possession_loss_grants_bonus_to_the_opponent_only():
    state = new_match(70, 70)
    rng = ScriptedRandom([0.1] * 6 + [0.99])      # A ataca e perde a posse

    result = run_cycle(state, rng)

    assert state.pending_control_bonus == PendingControlBonus("B", 5.0)
    assert result.granted_control_bonus == state.pending_control_bonus
    assert result.applied_control_bonus is None


def test_goal_does_not_grant_bonus():
    state = new_match(70, 70)
    run_cycle(state, ScriptedRandom([0.1] * 6 + [0.01]))

    assert state.pending_control_bonus is None


def test_bonus_applies_to_first_md5_only_and_is_then_consumed():
    state = new_match(70, 70)
    run_cycle(state, ScriptedRandom([0.9] * 6 + [0.99]))   # B ataca e perde => A ganha bônus
    assert state.pending_control_bonus == PendingControlBonus("A", 5.0)

    # 2º ciclo: 1ª MD5 com bônus (A vence), demais sem (B vence); B marca.
    rng = ScriptedRandom([0.51] * 9 + [0.01])
    result = run_cycle(state, rng)

    assert result.applied_control_bonus == PendingControlBonus("A", 5.0)
    assert tuple(s.winner for s in result.md3.series) == ("A", "B", "B")
    assert result.scorer == "B"
    assert state.pending_control_bonus is None
    assert rng.remaining == 0

    # 3º ciclo: sem bônus, 0.51 => B em todos os duelos.
    rng = ScriptedRandom([0.51] * 6 + [0.01])
    result = run_cycle(state, rng)

    assert result.applied_control_bonus is None
    assert (result.md3.wins_a, result.md3.wins_b) == (0, 2)


def test_new_possession_loss_generates_a_new_bonus_without_accumulating():
    state = new_match(70, 70)
    run_cycle(state, ScriptedRandom([0.9] * 6 + [0.99]))       # A recebe 5
    result = run_cycle(state, ScriptedRandom([0.51] * 9 + [0.99]))  # B ataca e perde

    assert result.applied_control_bonus == PendingControlBonus("A", 5.0)
    assert state.pending_control_bonus == PendingControlBonus("A", 5.0)  # novo, não 10


def test_bonus_does_not_change_base_or_modifiers():
    state = new_match(70, 70)
    before = {t: (s.base, dict(s.modifiers)) for t, s in state.teams.items()}

    run_cycle(state, ScriptedRandom([0.9] * 6 + [0.99]))
    assert state.pending_control_bonus is not None
    run_cycle(state, ScriptedRandom([0.51] * 9 + [0.99]))

    assert {t: (s.base, dict(s.modifiers)) for t, s in state.teams.items()} == before
    assert state.teams["A"].effective().control == pytest.approx(state.teams["A"].base.control)


def test_bonus_survives_halftime_and_lineup_change():
    state = new_match(70, 70)
    rng = random.Random(0)
    run_cycle(state, ScriptedRandom([0.9] * 6 + [0.01]))        # B marca
    run_cycle(state, ScriptedRandom([0.9] * 6 + [0.01]))        # B marca
    run_cycle(state, ScriptedRandom([0.9] * 6 + [0.99]))        # B perde => A ganha bônus
    assert state.phase is MatchPhase.HALFTIME

    change_lineup(state, "A", squad("N", 70), FORMATION_433)
    start_second_half(state)

    assert state.pending_control_bonus == PendingControlBonus("A", 5.0)


def test_no_bonus_is_left_pending_when_match_ends():
    for seed in range(50):
        state = new_match()
        play_match(state, seed=seed)
        assert state.pending_control_bonus is None


def test_failed_cycle_does_not_consume_pending_bonus(monkeypatch):
    state = new_match(70, 70)
    run_cycle(state, ScriptedRandom([0.9] * 6 + [0.99]))
    pending = state.pending_control_bonus

    monkeypatch.setattr(
        "python_prototype.match.simulate_attack_sequence",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("falha simulada")),
    )
    with pytest.raises(ValueError, match="falha simulada"):
        run_cycle(state, seed=1)

    assert state.pending_control_bonus == pending


def test_configurable_bonus_value_and_validation():
    state = new_match(70, 70)
    run_cycle(state, ScriptedRandom([0.1] * 6 + [0.99]), recovery_control_bonus=12.0)
    assert state.pending_control_bonus == PendingControlBonus("B", 12.0)

    for bad in (-1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            run_cycle(state, seed=1, recovery_control_bonus=bad)
    assert state.cycle_index == 1


def test_zero_bonus_disables_the_mechanic():
    state = new_match(70, 70)
    run_cycle(state, ScriptedRandom([0.1] * 6 + [0.99]), recovery_control_bonus=0.0)

    assert state.pending_control_bonus is None
