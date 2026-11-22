from dataclasses import replace

import pytest

from python_prototype.attack import AttackOutcome, AttackParameters
from python_prototype.experiments import (
    ExperimentConfig,
    compare_configs,
    compare_setups,
    format_report,
    run_experiment,
    standard_error,
    uniform_setup,
    with_modifiers,
)
from python_prototype.match import CYCLES_PER_MATCH, play_match

N = 400
CONFIG = ExperimentConfig(n_matches=N, base_seed=0)


@pytest.fixture(scope="module")
def baseline():
    return run_experiment(uniform_setup(70, 70), CONFIG)


# --- Configuração ---

@pytest.mark.parametrize("kwargs", [
    {"n_matches": 0}, {"n_matches": -5}, {"n_matches": 2.5}, {"base_seed": "x"},
    {"recovery_control_bonus": -1.0}, {"recovery_control_bonus": float("nan")},
])
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        ExperimentConfig(**kwargs)


# --- Consistência das métricas ---

def test_counts_are_consistent(baseline):
    r = baseline

    assert r.matches == N
    assert r.a_wins + r.draws + r.b_wins == N
    assert r.a_win_rate + r.draw_rate + r.b_win_rate == pytest.approx(1.0)
    assert r.mean_goals_per_match == pytest.approx((r.goals_a + r.goals_b) / N)
    assert r.sequences == N * CYCLES_PER_MATCH
    assert sum(r.goals_by_team.values()) == r.goals_a + r.goals_b
    assert sum(r.sequences_by_team.values()) == r.sequences
    assert sum(r.attempts_by_team.values()) == r.total_attempts


def test_attempt_outcomes_are_consistent(baseline):
    r = baseline
    goals = r.attempt_outcomes.get(AttackOutcome.GOAL, 0)
    losses = r.attempt_outcomes.get(AttackOutcome.POSSESSION_LOST, 0)
    continues = r.attempt_outcomes.get(AttackOutcome.CONTINUE, 0)

    # Toda sequência termina em exatamente um gol ou uma perda.
    assert goals + losses == r.sequences
    assert goals == r.goals_a + r.goals_b
    assert continues == r.total_attempts - r.sequences
    assert r.continuation_rate + r.goal_rate_per_attempt + r.loss_rate_per_attempt == pytest.approx(1.0)
    assert min(r.attempts_histogram) >= 1
    assert r.mean_attempts_per_sequence >= 1.0


def test_matches_engine_when_replayed_directly(baseline):
    # Replicar a 1ª partida diretamente no motor dá o mesmo placar que o lote usou.
    state = uniform_setup(70, 70).build()
    play_match(state, seed=CONFIG.base_seed)
    single = run_experiment(uniform_setup(70, 70), replace(CONFIG, n_matches=1))

    assert (single.goals_a, single.goals_b) == (state.score["A"], state.score["B"])


# --- Reprodutibilidade ---

def test_experiment_is_reproducible_with_fixed_seed(baseline):
    assert run_experiment(uniform_setup(70, 70), CONFIG) == baseline


def test_different_base_seed_changes_the_sample(baseline):
    other = run_experiment(uniform_setup(70, 70), replace(CONFIG, base_seed=10_000))

    assert other != baseline


# --- Comparação de configurações ---

def test_compare_configs_runs_each_configuration():
    results = compare_configs(
        uniform_setup(70, 70),
        {
            "padrão": CONFIG,
            "gol fácil": replace(CONFIG, attack_params=AttackParameters(g_max=0.45, c_max=0.50)),
        },
    )

    assert set(results) == {"padrão", "gol fácil"}
    assert results["gol fácil"].mean_goals_per_match > results["padrão"].mean_goals_per_match
    assert results["gol fácil"].config.attack_params.g_max == 0.45


def test_slower_decay_gives_longer_sequences():
    results = compare_configs(
        uniform_setup(70, 70),
        {
            "r baixo": replace(CONFIG, attack_params=AttackParameters(r=0.30)),
            "r alto": replace(CONFIG, attack_params=AttackParameters(r=0.90)),
        },
    )

    assert (
        results["r alto"].mean_attempts_per_sequence
        > results["r baixo"].mean_attempts_per_sequence
    )


def test_compare_setups_orders_win_rate_by_strength():
    results = compare_setups(
        {"equilibrado": uniform_setup(70, 70), "forte": uniform_setup(90, 40)}, CONFIG
    )

    assert results["forte"].a_win_rate > results["equilibrado"].a_win_rate
    assert results["forte"].mean_goal_difference > results["equilibrado"].mean_goal_difference


# --- Critérios da issue ---

def test_higher_control_raises_individual_duel_win_rate(baseline):
    boosted = run_experiment(
        with_modifiers(uniform_setup(70, 70), a={"control": 30.0}), CONFIG
    )

    assert baseline.duel_win_rate_a == pytest.approx(0.5, abs=0.03)
    assert boosted.duel_win_rate_a > 0.55
    assert boosted.duel_win_rate_a > baseline.duel_win_rate_a
    assert boosted.md3_win_rate_a > baseline.md3_win_rate_a


def test_higher_attack_relative_to_defense_raises_goal_rate_per_attempt():
    # Controle igual => cada time ataca ~metade das vezes; só ataque/defesa diferem.
    setup = uniform_setup(
        70, 70, modifiers_a={"attack": 30.0}, modifiers_b={"defense": -40.0}
    )
    r = run_experiment(setup, replace(CONFIG, n_matches=600))

    # A ataca com 100 contra defesa 30; B ataca com 70 contra defesa 70.
    assert r.goal_rate_per_attempt_of("A") > r.goal_rate_per_attempt_of("B") + 0.03


def test_with_modifiers_does_not_mutate_the_original_setup():
    setup = uniform_setup(70, 70)
    with_modifiers(setup, a={"attack": 10.0})

    assert dict(setup.modifiers_a) == {}


# --- Relatório ---

def test_report_lists_scenarios_and_parameters(baseline):
    text = format_report({"70 x 70": baseline}, "Teste")

    assert "# Teste" in text
    assert "| 70 x 70 |" in text
    assert "g_max=0.3" in text and "seed_base=0" in text


def test_standard_error():
    assert standard_error(0.5, 100) == pytest.approx(0.05)
    assert standard_error(0.0, 100) == 0.0
