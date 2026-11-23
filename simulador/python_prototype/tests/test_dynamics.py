import math
import random

import pytest

from python_prototype.attack import AttackParameters, calculate_attack_probabilities
from python_prototype.dispute import FoulRecord, simulate_md3, simulate_md5
from python_prototype.dynamics import (
    DynamicsConfig,
    DynamicsRuntime,
    FoulConfig,
    InjuryConfig,
    MoraleConfig,
    effective_attack_params,
    morale_value,
)
from python_prototype.match import MatchEventType, create_match, play_match, run_cycle
from python_prototype.tests.helpers import FORMATION_433, ScriptedRandom, squad

BASE = AttackParameters()
MORALE_ONLY = DynamicsConfig(
    morale=MoraleConfig(), fouls=FoulConfig(enabled=False), injuries=InjuryConfig(enabled=False)
)


def new_match(rating_a: int = 70, rating_b: int = 70):
    return create_match(squad("A", rating_a), FORMATION_433, squad("B", rating_b), FORMATION_433)


def count(state, event_type):
    return sum(1 for e in state.events if e.type is event_type)


# ------------------------------------------------------------
# Configuração
# ------------------------------------------------------------

@pytest.mark.parametrize("bad", [-0.1, 1.1, math.nan, math.inf, "x", True])
def test_invalid_probabilities_are_rejected(bad):
    with pytest.raises(ValueError):
        FoulConfig(probability=bad)
    with pytest.raises(ValueError):
        InjuryConfig(probability=bad)


@pytest.mark.parametrize("kwargs", [{"limit": -1}, {"beta": -0.1}, {"beta": math.nan}, {"limit": math.inf}])
def test_invalid_morale_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        MoraleConfig(**kwargs)


def test_runtime_requires_seed_when_random_mechanics_are_enabled():
    with pytest.raises(ValueError, match="semente"):
        DynamicsRuntime.create(DynamicsConfig(), seed=None)
    DynamicsRuntime.create(DynamicsConfig.disabled(), seed=None)  # não sorteia nada


# ------------------------------------------------------------
# Moral
# ------------------------------------------------------------

def test_zero_morale_uses_base_parameters():
    assert effective_attack_params(BASE, 0, MoraleConfig()) == BASE


def test_disabled_morale_ignores_goal_difference():
    assert effective_attack_params(BASE, 5, MoraleConfig(enabled=False)) is BASE


def test_morale_is_clamped_to_limit():
    config = MoraleConfig()
    assert morale_value(7, config) == 2 and morale_value(-7, config) == -2
    assert effective_attack_params(BASE, 7, config) == effective_attack_params(BASE, 2, config)


def test_effective_parameters_follow_formulas():
    ef = effective_attack_params(BASE, 2, MoraleConfig())      # v = 0.1

    assert ef.g_max == pytest.approx(0.33)
    assert ef.c_max == pytest.approx(0.45)
    assert ef.r == BASE.r


def test_morale_is_recomputed_not_accumulated():
    config = MoraleConfig()
    first = effective_attack_params(BASE, 1, config)
    second = effective_attack_params(BASE, 1, config)

    assert first == second
    assert BASE == AttackParameters()


@pytest.mark.parametrize("attempt", [1, 2])
def test_winning_team_is_more_volatile(attempt):
    # Obs.: P_L só sobe com m>0 enquanto c_max*r^(k-1) > g_max (k = 1, 2 com
    # os valores iniciais); a partir de k = 3 a fórmula da spec o inverte.
    base = calculate_attack_probabilities(60, 60, attempt, BASE)
    ahead = calculate_attack_probabilities(60, 60, attempt, effective_attack_params(BASE, 2, MoraleConfig()))

    assert ahead.goal > base.goal
    assert ahead.loss > base.loss
    assert ahead.continuation < base.continuation


@pytest.mark.parametrize("attempt", [1, 2])
def test_losing_team_is_more_conservative(attempt):
    base = calculate_attack_probabilities(60, 60, attempt, BASE)
    behind = calculate_attack_probabilities(60, 60, attempt, effective_attack_params(BASE, -2, MoraleConfig()))

    assert behind.goal < base.goal
    assert behind.loss < base.loss
    assert behind.continuation > base.continuation


@pytest.mark.parametrize("goal_diff", range(-5, 6))
@pytest.mark.parametrize("attempt", [1, 2, 3, 6])
def test_probabilities_stay_valid_under_morale(goal_diff, attempt):
    params = effective_attack_params(BASE, goal_diff, MoraleConfig())
    p = calculate_attack_probabilities(80, 30, attempt, params)

    for value in (p.goal, p.continuation, p.loss):
        assert 0.0 <= value <= 1.0
    assert p.goal + p.continuation + p.loss == pytest.approx(1.0)


def test_worst_case_sum_with_initial_values_is_082():
    config = MoraleConfig()
    sums = []
    for edge in (-config.limit, config.limit):
        ef = effective_attack_params(BASE, edge, config)
        sums.append(ef.g_max + ef.c_max)

    assert max(sums) == pytest.approx(0.82)
    DynamicsConfig().validate(BASE)


def test_config_that_breaks_probabilities_is_rejected_on_load():
    with pytest.raises(ValueError, match="pior caso"):
        DynamicsConfig().validate(AttackParameters(g_max=0.2, c_max=0.8))
    with pytest.raises(ValueError, match="excede 1"):
        DynamicsConfig(morale=MoraleConfig(beta=0.6)).validate(BASE)
    # Moral desligada não é validada.
    DynamicsConfig(morale=MoraleConfig(enabled=False, beta=0.6)).validate(BASE)


def test_leading_team_uses_volatile_parameters_in_cycle():
    # Placar 2x0 para A: g_ef = 0.33, c_ef = 0.45 => P_G = 0.165 (q = 0.5).
    # Sorteio 0.16: gol com moral; continuação (0.16 >= 0.15) sem moral.
    draws = [0.1] * 6 + [0.16]
    state = new_match()
    state.score["A"] = 2
    rng = ScriptedRandom(draws)

    result = run_cycle(state, rng, dynamics=DynamicsRuntime.create(MORALE_ONLY, seed=1))

    assert result.scorer == "A" and result.attack.attempts == 1
    assert state.score["A"] == 3
    assert rng.remaining == 0

    plain = new_match()
    plain.score["A"] = 2
    with pytest.raises(AssertionError, match="esgotada"):   # continuou: precisou de outro sorteio
        run_cycle(plain, ScriptedRandom(draws))


def test_trailing_team_uses_conservative_parameters_in_cycle():
    # Placar 0x2: g_ef = 0.27 => P_G = 0.135; 0.14 deixa de ser gol e continua.
    state = new_match()
    state.score["B"] = 2
    rng = ScriptedRandom([0.1] * 6 + [0.14, 0.99])

    result = run_cycle(state, rng, dynamics=DynamicsRuntime.create(MORALE_ONLY, seed=1))

    assert result.attack.attempts == 2
    assert result.scorer is None
    assert state.score == {"A": 0, "B": 2}
    assert rng.remaining == 0


# ------------------------------------------------------------
# Faltas (nível MD5/MD3)
# ------------------------------------------------------------

def test_foul_gives_the_duel_to_the_opponent():
    rng = ScriptedRandom([0.1] * 3)                 # A venceria os 3 duelos
    fouls = ScriptedRandom([0.0] * 3)               # e cometeria falta em todos

    result = simulate_md5(50, 50, rng=rng, foul_rng=fouls, foul_probability=0.5)

    assert result.duels == ("B", "B", "B") and result.winner == "B"
    assert result.fouls == tuple(FoulRecord(i, "A") for i in (1, 2, 3))
    assert rng.used == 3 and fouls.used == 3


def test_no_foul_when_draw_is_not_below_probability():
    rng = ScriptedRandom([0.1] * 3)
    fouls = ScriptedRandom([0.5] * 3)               # estritamente menor que p => falta

    result = simulate_md5(50, 50, rng=rng, foul_rng=fouls, foul_probability=0.5)

    assert result.duels == ("A", "A", "A") and result.fouls == ()
    assert fouls.used == 3


def test_foul_draws_never_touch_the_main_rng_and_zero_probability_draws_nothing():
    rng = ScriptedRandom([0.1, 0.9, 0.1, 0.9, 0.1])
    fouls = ScriptedRandom([])

    result = simulate_md5(50, 50, rng=rng, foul_rng=fouls, foul_probability=0.0)

    assert rng.used == len(result.duels) == 5 and fouls.used == 0


@pytest.mark.parametrize("bad", [-0.1, 1.5, math.nan, True])
def test_invalid_foul_probability_is_rejected(bad):
    with pytest.raises(ValueError):
        simulate_md5(50, 50, seed=1, foul_probability=bad)
    with pytest.raises(ValueError):
        simulate_md3(50, 50, seed=1, foul_probability=bad)


@pytest.mark.parametrize("seed", range(50))
def test_every_duel_has_exactly_one_winner_with_fouls(seed):
    result = simulate_md5(
        60, 40, rng=random.Random(seed), foul_rng=random.Random(seed + 1000), foul_probability=0.4
    )

    assert result.wins_a + result.wins_b == len(result.duels)
    assert max(result.wins_a, result.wins_b) == 3 and 3 <= len(result.duels) <= 5
    assert len(result.fouls) <= len(result.duels)
    for foul in result.fouls:
        # o infrator é quem NÃO ficou com o confronto
        assert result.duels[foul.duel - 1] != foul.fouling_team


def test_zero_probability_md3_is_unchanged():
    assert simulate_md3(70, 60, seed=42) == simulate_md3(
        70, 60, seed=42, foul_rng=random.Random(1), foul_probability=0.0
    )


def test_fouls_do_not_alter_the_first_md5_bonus():
    # Bônus 50 só na 1ª MD5 (p(A) ≈ 0.667). Sorteio 0.6: raw A na 1ª MD5, raw B nas demais.
    # Com falta em todo duelo, tudo se inverte: B, A, A. O bônus continua só na 1ª.
    rng = ScriptedRandom([0.6] * 9)
    fouls = ScriptedRandom([0.0] * 9)

    result = simulate_md3(50, 50, rng=rng, first_md5_bonus_a=50, foul_rng=fouls, foul_probability=1.0)

    assert tuple(s.winner for s in result.series) == ("B", "A", "A")
    assert rng.remaining == 0 and fouls.remaining == 0


# ------------------------------------------------------------
# Faltas e lesões no ciclo
# ------------------------------------------------------------

def test_scripted_cycle_with_foul_and_injury():
    config = DynamicsConfig(
        morale=MoraleConfig(enabled=False),
        fouls=FoulConfig(probability=0.5),
        injuries=InjuryConfig(probability=0.5),
    )
    # MD5 #1: duelo 1 raw A com falta de A => B; depois A vence 3 => A (4 duelos).
    # MD5 #2: A 3x0. MD3 2x0 para A. Ataque: 0.01 => gol.
    main = ScriptedRandom([0.1] * 7 + [0.01])
    foul_rng = ScriptedRandom([0.0] + [0.9] * 6)
    injury_rng = ScriptedRandom([0.0, 0.0])         # há lesão; jogador de índice 0
    state = new_match()

    run_cycle(state, main, dynamics=DynamicsRuntime(config, foul_rng, injury_rng))

    assert [e.type for e in state.events] == [
        MatchEventType.FALTA,
        MatchEventType.LESAO,
        MatchEventType.MD3_RESULT,
        MatchEventType.ATTACK_SEQUENCE,
        MatchEventType.GOAL,
    ]
    foul, injury = state.events[0], state.events[1]
    assert foul.team == "A" and foul.minute == 0
    assert foul.data == {"cycle": 1, "possession": 1, "md5": 1, "duel": 1}
    assert injury.team == "B"                       # quem sofreu a falta
    assert injury.data == {"player": "B0", "cycle": 1, "foul_event": 0, "effect": {}}
    assert state.score == {"A": 1, "B": 0}
    assert main.remaining == 0 and foul_rng.remaining == 0 and injury_rng.remaining == 0


def test_injury_only_happens_after_a_foul():
    config = DynamicsConfig(
        morale=MoraleConfig(enabled=False),
        fouls=FoulConfig(enabled=False),
        injuries=InjuryConfig(probability=1.0),
    )
    injury_rng = ScriptedRandom([])
    state = new_match()

    run_cycle(
        state, ScriptedRandom([0.1] * 6 + [0.01]),
        dynamics=DynamicsRuntime(config, ScriptedRandom([]), injury_rng),
    )

    assert count(state, MatchEventType.FALTA) == 0
    assert count(state, MatchEventType.LESAO) == 0
    assert injury_rng.used == 0


def test_foul_without_injury_generates_only_the_foul_event():
    config = DynamicsConfig(
        morale=MoraleConfig(enabled=False),
        fouls=FoulConfig(probability=0.5),
        injuries=InjuryConfig(enabled=False),
    )
    state = new_match()

    run_cycle(
        state, ScriptedRandom([0.1] * 7 + [0.01]),
        dynamics=DynamicsRuntime(config, ScriptedRandom([0.0] + [0.9] * 6), ScriptedRandom([])),
    )

    assert count(state, MatchEventType.FALTA) == 1
    assert count(state, MatchEventType.LESAO) == 0


@pytest.mark.parametrize("seed", range(10))
def test_foul_and_injury_invariants_over_a_match(seed):
    config = DynamicsConfig(fouls=FoulConfig(probability=0.3), injuries=InjuryConfig(probability=1.0))
    state = new_match()
    before = {t: (s.players, s.base, dict(s.modifiers)) for t, s in state.teams.items()}

    results = play_match(state, seed=seed, dynamics=config)

    mds = [md5 for r in results for p in r.possessions for md5 in p.md3.series]
    total_fouls = sum(len(md5.fouls) for md5 in mds)
    assert count(state, MatchEventType.FALTA) == total_fouls > 0
    assert count(state, MatchEventType.LESAO) == total_fouls      # p_lesão = 1

    refs = []
    for event in state.events:
        if event.type is MatchEventType.LESAO:
            origin = state.events[event.data["foul_event"]]
            assert origin.type is MatchEventType.FALTA
            assert origin.team != event.team                       # lesão é de quem sofreu
            assert event.data["player"] in {p.name for p in state.teams[event.team].players}
            assert event.data["effect"] == {}
            refs.append(event.data["foul_event"])
    assert len(refs) == len(set(refs))                             # 1 lesão por falta

    for md5 in mds:
        assert md5.wins_a + md5.wins_b == len(md5.duels)
        assert max(md5.wins_a, md5.wins_b) == 3
    minutes = [e.minute for e in state.events]
    assert minutes == sorted(minutes)

    # Escalação, atributos-base e modificadores intocados (moral ligada inclusive).
    assert {t: (s.players, s.base, dict(s.modifiers)) for t, s in state.teams.items()} == before
    assert state.pending_control_bonus is None


# ------------------------------------------------------------
# Equivalência e reprodutibilidade
# ------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 42, 2026])
def test_all_disabled_matches_previous_version(seed):
    plain, off = new_match(75, 65), new_match(75, 65)
    play_match(plain, seed=seed)
    play_match(off, seed=seed, dynamics=DynamicsConfig.disabled())

    assert plain.events == off.events and plain.score == off.score


def test_same_seed_and_config_is_reproducible():
    a, b = new_match(), new_match()
    play_match(a, seed=7, dynamics=DynamicsConfig())
    play_match(b, seed=7, dynamics=DynamicsConfig())

    assert a.events == b.events and a.score == b.score


def test_dynamics_seed_overrides_match_seed_for_fouls_only():
    a, b = new_match(), new_match()
    play_match(a, seed=7, dynamics=DynamicsConfig(), dynamics_seed=1)
    play_match(b, seed=7, dynamics=DynamicsConfig(), dynamics_seed=2)

    assert [e for e in a.events if e.type is MatchEventType.FALTA] != [
        e for e in b.events if e.type is MatchEventType.FALTA
    ]


def test_rng_without_dynamics_seed_is_rejected_when_random_mechanics_are_on():
    state = new_match()
    with pytest.raises(ValueError, match="semente"):
        play_match(state, random.Random(1), dynamics=DynamicsConfig())
    assert state.clock == 0
