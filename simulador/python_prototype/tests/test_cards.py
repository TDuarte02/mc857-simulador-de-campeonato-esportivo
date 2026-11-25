import random

import pytest

from simulador.python_prototype.cards import CardConfig, derive_cards, red_card_players
from python_prototype.match import MatchEvent, MatchEventType as T
from python_prototype.tests.helpers import ScriptedRandom, squad

LINEUPS = {"A": squad("A", 70), "B": squad("B", 70)}


def lineup_at(team, minute):
    return LINEUPS[team]


def foul(team="A", minute=0):
    return MatchEvent(minute, T.FALTA, team, {"cycle": 1, "possession": 1, "md5": 1, "duel": 1})


@pytest.mark.parametrize("kwargs", [
    {"p_yellow": -0.1}, {"p_red": 1.1}, {"p_yellow": float("nan")}, {"p_red": True},
    {"p_yellow": 0.7, "p_red": 0.4},
])
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        CardConfig(**kwargs)


def test_default_config():
    c = CardConfig()
    assert (c.p_yellow, c.p_red) == (0.35, 0.02)


def test_red_when_u1_below_p_red_and_player_from_u2():
    rng = ScriptedRandom([0.0, 0.0])
    [card] = derive_cards([foul("A")], lineup_at, rng=rng)
    assert card.type is T.CARTAO_VERMELHO and card.team == "A"
    assert card.data == {"player": "A1", "foul_event": 0}      # A0 é o goleiro
    assert rng.used == 2


def test_yellow_and_u2_selects_outfield_index():
    [card] = derive_cards([foul("B")], lineup_at, rng=ScriptedRandom([0.1, 0.5]))
    assert card.type is T.CARTAO_AMARELO and card.data["player"] == "B6"  # int(0.5*10)=5 -> B6


def test_no_card_still_consumes_two_draws():
    rng = ScriptedRandom([0.99, 0.0])
    assert derive_cards([foul()], lineup_at, rng=rng) == ()
    assert rng.used == 2


def test_second_yellow_becomes_red_and_no_more_cards_afterwards():
    rng = ScriptedRandom([0.1, 0.0] * 3)
    cards = derive_cards([foul(), foul(), foul()], lineup_at, rng=rng)
    assert [c.type for c in cards] == [T.CARTAO_AMARELO, T.CARTAO_VERMELHO]
    assert cards[0].data["player"] == cards[1].data["player"]
    assert cards[1].data["foul_event"] == 1
    assert rng.used == 6
    assert red_card_players(cards, "A") == {"A1"}
    assert red_card_players(cards, "B") == frozenset()


def test_foul_event_is_the_index_in_the_log():
    events = [MatchEvent(0, T.MD3_RESULT, "A", {"wins_a": 2, "wins_b": 0}), foul()]
    [card] = derive_cards(events, lineup_at, rng=ScriptedRandom([0.1, 0.0]))
    assert card.data["foul_event"] == 1


def test_goalkeeper_is_never_carded_and_result_is_reproducible():
    events = [foul("A") for _ in range(200)]
    first = derive_cards(events, lineup_at, CardConfig(0.5, 0.5), seed=3)
    assert first == derive_cards(events, lineup_at, CardConfig(0.5, 0.5), seed=3)
    assert all(c.data["player"] != "A0" for c in first)


def test_rng_and_seed_are_exclusive():
    with pytest.raises(ValueError):
        derive_cards([], lineup_at, rng=random.Random(1), seed=1)
