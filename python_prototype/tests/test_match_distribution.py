"""
Testes estatísticos sobre a distribuição de resultados de partidas completas.

Todas as simulações usam seeds fixas (0..N-1), então os testes são
determinísticos. Os limiares foram escolhidos com folga em relação às
frequências observadas, para não quebrarem por pequenas mudanças de
parâmetros, mas quebrarem se o comportamento qualitativo mudar.
"""
from functools import lru_cache

from python_prototype.collective_attributes import Player
from python_prototype.match import create_match, play_match
from python_prototype.tests.helpers import FORMATION_433, squad

N_MATCHES = 4000

# ------------------------------------------------------------
# Auxiliares
# ------------------------------------------------------------


@lru_cache(maxsize=None)
def simulate_scores(rating_a: int, rating_b: int, attack_edge: float = 0.0,
                    defense_edge: float = 0.0, n: int = N_MATCHES):
    """
    Simula `n` partidas e devolve a lista de placares (gols_a, gols_b).

    attack_edge/defense_edge são bônus aditivos aplicados ao time A via
    `modifiers`, isolando ataque e defesa sem mexer no Controle.
    """
    scores = []
    for seed in range(n):
        state = create_match(
            squad("A", rating_a), FORMATION_433, squad("B", rating_b), FORMATION_433
        )
        state.teams["A"].modifiers["attack"] = attack_edge
        state.teams["A"].modifiers["defense"] = defense_edge
        play_match(state, seed=seed)
        scores.append((state.score["A"], state.score["B"]))
    return scores


def rates(scores):
    n = len(scores)
    return {
        "a_wins": sum(a > b for a, b in scores) / n,
        "draws": sum(a == b for a, b in scores) / n,
        "b_wins": sum(a < b for a, b in scores) / n,
    }


def big_margin_rate(scores, team: str) -> float:
    """Fração das partidas em que `team` venceu por 3 ou mais gols."""
    sign = 1 if team == "A" else -1
    return sum(sign * (a - b) >= 3 for a, b in scores) / len(scores)


def mean_goal_difference(scores) -> float:
    return sum(a - b for a, b in scores) / len(scores)


# ------------------------------------------------------------
# Diferenças pequenas: tendem a empate, mas qualquer time pode vencer
# ------------------------------------------------------------

def test_small_rating_difference_tends_to_draws():
    r = rates(simulate_scores(72, 68))

    assert r["draws"] >= 0.30
    assert r["draws"] > r["a_wins"]
    assert r["draws"] > r["b_wins"]


def test_small_rating_difference_allows_either_team_to_win():
    scores = simulate_scores(72, 68)
    r = rates(scores)

    assert any(a > b for a, b in scores)
    assert any(a < b for a, b in scores)
    # Mesmo o time ligeiramente inferior vence com frequência relevante.
    assert r["b_wins"] >= 0.15
    assert r["a_wins"] >= 0.15
    # O time ligeiramente superior leva vantagem, mas pequena.
    assert r["a_wins"] > r["b_wins"]


def test_equal_teams_have_symmetric_outcomes():
    r = rates(simulate_scores(70, 70))

    assert abs(r["a_wins"] - r["b_wins"]) < 0.05
    assert r["draws"] > r["a_wins"] and r["draws"] > r["b_wins"]


def test_small_attack_and_defense_edge_alone_tends_to_draws():
    # Controle idêntico: só ataque e defesa do time A diferem (+5).
    scores = simulate_scores(70, 70, attack_edge=5.0, defense_edge=5.0)
    r = rates(scores)

    assert r["draws"] >= 0.30
    assert r["draws"] > r["a_wins"]
    assert r["draws"] > r["b_wins"]
    assert r["b_wins"] >= 0.15
    assert r["a_wins"] >= 0.15
    assert r["a_wins"] > r["b_wins"]


def test_small_difference_rarely_produces_large_margins():
    scores = simulate_scores(72, 68)

    assert big_margin_rate(scores, "A") < 0.05
    assert big_margin_rate(scores, "B") < 0.05


# ------------------------------------------------------------
# Diferenças grandes: permitem saldo de 3 ou mais gols
# ------------------------------------------------------------

def test_large_rating_difference_allows_margin_of_three_or_more_goals():
    scores = simulate_scores(90, 40)

    assert any(a - b >= 3 for a, b in scores)
    assert big_margin_rate(scores, "A") >= 0.10


def test_large_difference_margin_holds_when_stronger_team_is_b():
    scores = simulate_scores(40, 90)

    assert any(b - a >= 3 for a, b in scores)
    assert big_margin_rate(scores, "B") >= 0.10


def test_weaker_team_almost_never_wins_by_three_or_more():
    scores = simulate_scores(90, 40)

    assert big_margin_rate(scores, "B") <= 0.01
    assert big_margin_rate(scores, "B") < big_margin_rate(scores, "A")


def test_stronger_team_wins_most_matches_when_difference_is_large():
    r = rates(simulate_scores(90, 40))

    assert r["a_wins"] >= 0.70
    assert r["b_wins"] <= 0.05
    assert r["a_wins"] > r["draws"]


def test_very_large_difference_makes_big_margins_common():
    scores = simulate_scores(100, 20)

    assert big_margin_rate(scores, "A") >= 0.30


def test_large_difference_produces_far_fewer_draws_than_small_difference():
    small = rates(simulate_scores(72, 68))
    large = rates(simulate_scores(90, 40))

    assert small["draws"] > large["draws"] + 0.15


# ------------------------------------------------------------
# Monotonicidade: quanto maior a diferença, maior o saldo
# ------------------------------------------------------------

def test_margin_grows_with_strength_gap():
    gaps = [(70, 70), (72, 68), (80, 60), (90, 40), (100, 20)]
    means = [mean_goal_difference(simulate_scores(a, b)) for a, b in gaps]
    big = [big_margin_rate(simulate_scores(a, b), "A") for a, b in gaps]

    assert all(x < y for x, y in zip(means, means[1:]))
    assert all(x < y for x, y in zip(big[1:], big[2:]))
    assert big[-1] > 10 * big[1]
