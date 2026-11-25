"""
Disputa de pênaltis (Issue #35): configuração, probabilidade de conversão,
ordem dos cobradores e a disputa (encerramento antecipado e morte súbita).

Este módulo não depende de `tournament` nem de `group_stage`, para que
`TournamentConfig` possa importar `PenaltyConfig` sem ciclos.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from python_prototype.collective_attributes import Player, canonical_position
from python_prototype.common import TeamId, clamp, other_team, resolve_rng

REGULATION_KICKS = 5


def _finite_number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} deve ser um número finito; recebido: {value!r}")
    return float(value)


# ============================================================
# Configuração
# ============================================================

@dataclass(frozen=True)
class PenaltyConfig:
    """
    p = clamp(p_base + s * (S - G) / 100, p_min, p_max).

    Validada na criação: valores finitos, probabilidades em [0, 1],
    p_min <= p_base <= p_max e s >= 0.

    Além disso, exige-se 0 < p_min e p_max < 1. Sem isso (p. ex. todas as
    probabilidades iguais a 1), a morte súbita nunca teria diferença ao fim
    de um par e a disputa não terminaria.
    """

    p_base: float = 0.75
    s: float = 0.25
    p_min: float = 0.50
    p_max: float = 0.95

    def __post_init__(self) -> None:
        p_base = _finite_number(self.p_base, "p_base")
        p_min = _finite_number(self.p_min, "p_min")
        p_max = _finite_number(self.p_max, "p_max")
        s = _finite_number(self.s, "s")

        for label, value in (("p_base", p_base), ("p_min", p_min), ("p_max", p_max)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{label} deve estar em [0, 1]; recebido: {value!r}")
        if s < 0:
            raise ValueError(f"s não pode ser negativo; recebido: {s!r}")
        if not p_min <= p_base <= p_max:
            raise ValueError(
                "Exige-se p_min <= p_base <= p_max; "
                f"recebido: {p_min!r}, {p_base!r}, {p_max!r}"
            )
        if p_min <= 0.0 or p_max >= 1.0:
            raise ValueError(
                "Exige-se 0 < p_min e p_max < 1 para a morte súbita terminar com "
                f"probabilidade 1; recebido: p_min={p_min!r}, p_max={p_max!r}"
            )


DEFAULT_PENALTY_CONFIG = PenaltyConfig()


# ============================================================
# Resultado
# ============================================================

@dataclass(frozen=True)
class PenaltyKick:
    team: TeamId
    player: str
    scored: bool


@dataclass(frozen=True)
class PenaltyShootout:
    """Os pênaltis não contam como gols da partida: ficam registrados à parte."""

    first_team: TeamId
    kicks: tuple[PenaltyKick, ...]
    goals_a: int
    goals_b: int
    winner: TeamId

    @property
    def sudden_death(self) -> bool:
        return len(self.kicks) > 2 * REGULATION_KICKS

    def kicks_by(self, team: TeamId) -> tuple[PenaltyKick, ...]:
        return tuple(k for k in self.kicks if k.team == team)


# ============================================================
# Probabilidade e ordem dos cobradores
# ============================================================

def penalty_score(player: Player) -> float:
    """S = (mentality_penalties + shooting) / 2."""
    return (player.mentality_penalties + player.shooting) / 2


def conversion_probability(
    taker: Player,
    goalkeeper: Player,
    config: PenaltyConfig = DEFAULT_PENALTY_CONFIG,
) -> float:
    """p = clamp(p_base + s * (S - G) / 100, p_min, p_max); G = reflexos do goleiro."""
    s_value = penalty_score(taker)
    g_value = float(goalkeeper.goalkeeping_reflexes)
    return clamp(
        config.p_base + config.s * (s_value - g_value) / 100.0,
        config.p_min,
        config.p_max,
    )


def goalkeeper_of(lineup: Sequence[Player]) -> Player:
    goalkeepers = [p for p in lineup if canonical_position(p.pos) == "GK"]
    if len(goalkeepers) != 1:
        raise ValueError(
            f"A escalação deve ter exatamente um goleiro; encontrados: {len(goalkeepers)}"
        )
    return goalkeepers[0]


def penalty_taker_order(lineup: Sequence[Player]) -> tuple[Player, ...]:
    """
    Titulares de linha por S decrescente (desempate pela ordem da escalação,
    graças à estabilidade de `sorted`) e o goleiro por último.
    """
    keeper = goalkeeper_of(lineup)
    outfield = [p for p in lineup if canonical_position(p.pos) != "GK"]
    ranked = sorted(outfield, key=lambda p: -penalty_score(p))
    return (*ranked, keeper)


# ============================================================
# Disputa
# ============================================================

def simulate_penalty_shootout(
    lineup_a: Sequence[Player],
    lineup_b: Sequence[Player],
    config: PenaltyConfig = DEFAULT_PENALTY_CONFIG,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
) -> PenaltyShootout:
    """
    Simula a disputa. Ordem dos sorteios: 1º define quem cobra primeiro
    (< 0.5 => A); depois, um por cobrança (convertida se sorteio < p).

    - As cobranças são alternadas; depois do 11º cobrador a ordem recomeça.
    - Nas 5 primeiras cobranças de cada time, a disputa termina assim que um
      time tem mais gols do que o outro poderia alcançar com as cobranças
      restantes.
    - Persistindo o empate, segue em morte súbita, em pares de cobranças, até
      haver diferença ao fim do par (o segundo time sempre cobra o seu).
    """
    generator = resolve_rng(rng, seed)
    orders = {"A": penalty_taker_order(lineup_a), "B": penalty_taker_order(lineup_b)}
    keepers = {"A": orders["A"][-1], "B": orders["B"][-1]}

    first: TeamId = "A" if generator.random() < 0.5 else "B"
    second = other_team(first)

    goals = {"A": 0, "B": 0}
    taken = {"A": 0, "B": 0}
    kicks: list[PenaltyKick] = []

    def kick(team: TeamId) -> None:
        order = orders[team]
        taker = order[taken[team] % len(order)]
        p = conversion_probability(taker, keepers[other_team(team)], config)
        scored = generator.random() < p
        taken[team] += 1
        goals[team] += scored
        kicks.append(PenaltyKick(team, taker.name, scored))

    def clinched() -> TeamId | None:
        for team in ("A", "B"):
            opponent = other_team(team)
            if goals[team] > goals[opponent] + (REGULATION_KICKS - taken[opponent]):
                return team
        return None

    def result(winner: TeamId) -> PenaltyShootout:
        return PenaltyShootout(first, tuple(kicks), goals["A"], goals["B"], winner)

    for _ in range(REGULATION_KICKS):
        for team in (first, second):
            kick(team)
            winner = clinched()
            if winner is not None:
                return result(winner)

    # 5 x 5 cobranças e nenhum time na frente: morte súbita.
    while True:
        kick(first)
        kick(second)
        if goals["A"] != goals["B"]:
            return result("A" if goals["A"] > goals["B"] else "B")
