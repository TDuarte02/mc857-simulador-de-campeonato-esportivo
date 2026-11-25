"""
Cartões (Issue #41): camada derivada, calculada DEPOIS da partida a partir do
log de eventos. Não toca o RNG principal, o placar nem o jogador em campo.

Para cada FALTA do log há sempre dois sorteios, nesta ordem:
  u1: < p_red => vermelho; < p_red + p_yellow => amarelo; senão nada;
  u2: escolhe o jogador de linha do time infrator, `int(u2 * n)`.
O 2º amarelo do mesmo jogador na partida vira vermelho.

Este módulo não importa `tournament` (que importa `CardConfig`): a semente
`derive_seed(seed, match_id, "cards")` é calculada pelo chamador.
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from python_prototype.collective_attributes import Player, canonical_position
from python_prototype.common import TeamId, resolve_rng
from python_prototype.match import MatchEvent, MatchEventType


def _probability(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0.0 <= value <= 1.0
    ):
        raise ValueError(f"{label} deve estar em [0, 1]; recebido: {value!r}")
    return float(value)


@dataclass(frozen=True)
class CardConfig:
    """Probabilidades de cartão por falta. Exige p_yellow + p_red <= 1."""

    p_yellow: float = 0.35
    p_red: float = 0.02

    def __post_init__(self) -> None:
        y = _probability(self.p_yellow, "p_yellow")
        r = _probability(self.p_red, "p_red")
        if y + r > 1.0 + 1e-12:
            raise ValueError(f"p_yellow + p_red não pode exceder 1; recebido: {y + r!r}")


DEFAULT_CARD_CONFIG = CardConfig()

# (time, minuto de início do ciclo) -> jogadores em campo naquele momento.
LineupLookup = Callable[[TeamId, int], Sequence[Player]]


def derive_cards(
    events: Sequence[MatchEvent],
    lineup_at: LineupLookup,
    config: CardConfig = DEFAULT_CARD_CONFIG,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
) -> tuple[MatchEvent, ...]:
    """
    Devolve os eventos CARTAO_AMARELO / CARTAO_VERMELHO (em ordem do log).

    `team` é o time infrator; `data = {player, foul_event}`, onde `foul_event`
    é o índice da FALTA de origem em `events`. Quem já tem vermelho na partida
    ainda consome os 2 sorteios, mas não gera novo cartão.
    """
    generator = resolve_rng(rng, seed)
    yellows: set[tuple[str, str]] = set()
    reds: set[tuple[str, str]] = set()
    cards: list[MatchEvent] = []

    for index, event in enumerate(events):
        if event.type is not MatchEventType.FALTA:
            continue
        u1 = generator.random()
        u2 = generator.random()

        outfield = [
            p for p in lineup_at(event.team, event.minute)
            if canonical_position(p.pos) != "GK"
        ]
        if not outfield:
            continue
        player = outfield[int(u2 * len(outfield))]
        key = (event.team, player.name)
        if key in reds:
            continue

        if u1 < config.p_red:
            kind = MatchEventType.CARTAO_VERMELHO
        elif u1 < config.p_red + config.p_yellow:
            kind = (
                MatchEventType.CARTAO_VERMELHO
                if key in yellows
                else MatchEventType.CARTAO_AMARELO
            )
        else:
            continue

        (reds if kind is MatchEventType.CARTAO_VERMELHO else yellows).add(key)
        cards.append(
            MatchEvent(
                event.minute, kind, event.team,
                {"player": player.name, "foul_event": index},
            )
        )
    return tuple(cards)


def red_card_players(cards: Sequence[MatchEvent], team: TeamId) -> frozenset[str]:
    return frozenset(
        c.data["player"]
        for c in cards
        if c.type is MatchEventType.CARTAO_VERMELHO and c.team == team
    )
