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
    change_lineup,
    create_match,
    play_match,
    run_cycle,
    start_second_half,
)

POSITIONS = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "RW", "ST", "LW"]
FORMATION_433 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]
FORMATION_442 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "CM", "ST", "ST"]
POSITIONS_442 = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "CM", "ST", "ST"]


def make_player(name: str, pos: str, rating: int) -> Player:
    return Player(
        name=name, pos=pos, overall=rating, potential=rating, pace=rating,
        shooting=rating, passing=rating, dribbling=rating, defending=rating,
        physic=rating, attacking_heading_accuracy=rating, movement_agility=rating,
        movement_reactions=rating, movement_balance=rating, power_jumping=rating,
        power_stamina=rating, mentality_aggression=rating,
        mentality_penalties=rating, mentality_composure=rating,
        goalkeeping_reflexes=rating,
    )


def squad(prefix: str, rating: int, positions=POSITIONS):
    return [make_player(f"{prefix}{i}", pos, rating) for i, pos in enumerate(positions)]


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
