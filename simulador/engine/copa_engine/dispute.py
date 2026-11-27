from __future__ import annotations

import math
import random
from dataclasses import dataclass

from copa_engine.common import (
    ATTRIBUTE_MAX,
    TeamId,
    ensure_finite_non_negative,
    other_team,
    resolve_rng,
)
from copa_engine.control import simulate_control_duel


@dataclass(frozen=True)
class FoulRecord:
    """Falta num confronto: `duel` é o nº (a partir de 1) dentro da MD5."""

    duel: int
    fouling_team: TeamId


@dataclass(frozen=True)
class MD5Result:
    winner: TeamId
    wins_a: int
    wins_b: int
    duels: tuple[TeamId, ...]
    fouls: tuple[FoulRecord, ...] = ()


@dataclass(frozen=True)
class MD3Result:
    winner: TeamId
    wins_a: int
    wins_b: int
    series: tuple[MD5Result, ...]


def _boosted_control(control: float, bonus: float, label: str) -> float:
    """Controle da primeira MD5: base + bônus, limitado a ATTRIBUTE_MAX."""
    bonus = ensure_finite_non_negative(bonus, f"Bônus de Controle do time {label}")
    if bonus == 0:
        return control
    base = ensure_finite_non_negative(control, f"Controle do time {label}")
    if base > ATTRIBUTE_MAX:
        raise ValueError(
            f"Os atributos de Controle devem estar em [0, {ATTRIBUTE_MAX:g}]."
        )
    return min(ATTRIBUTE_MAX, base + bonus)


def _validate_foul_probability(p: float) -> float:
    if (
        isinstance(p, bool)
        or not isinstance(p, (int, float))
        or not math.isfinite(p)
        or not 0.0 <= p <= 1.0
    ):
        raise ValueError(f"foul_probability deve estar em [0, 1]; recebido: {p!r}")
    return float(p)


def simulate_md5(
    control_a,
    control_b,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
    foul_rng: random.Random | None = None,
    foul_probability: float = 0.0,
) -> MD5Result:
    """
    Simula uma série MD5 (melhor de cinco).

    A série termina quando um time alcança três vitórias.

    Faltas (Issue #15): se `foul_rng` e `foul_probability > 0`, cada confronto
    sorteia (com `foul_rng`, nunca com `rng`) se houve falta. Havendo falta,
    ela é do vencedor do sorteio normal e o confronto vai para o adversário.
    O confronto segue com exatamente um vencedor.
    """
    foul_probability = _validate_foul_probability(foul_probability)
    random_generator = resolve_rng(rng, seed)

    wins = {"A": 0, "B": 0}
    duels: list[TeamId] = []
    fouls: list[FoulRecord] = []

    while max(wins.values()) < 3:
        duel_winner = simulate_control_duel(
            control_a,
            control_b,
            rng=random_generator,
        )

        if (
            foul_rng is not None
            and foul_probability > 0.0
            and foul_rng.random() < foul_probability
        ):
            fouls.append(FoulRecord(duel=len(duels) + 1, fouling_team=duel_winner))
            duel_winner = other_team(duel_winner)

        wins[duel_winner] += 1
        duels.append(duel_winner)

    winner = "A" if wins["A"] == 3 else "B"

    return MD5Result(
        winner=winner,
        wins_a=wins["A"],
        wins_b=wins["B"],
        duels=tuple(duels),
        fouls=tuple(fouls),
    )


def simulate_md3(
    control_a,
    control_b,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
    first_md5_bonus_a: float = 0.0,
    first_md5_bonus_b: float = 0.0,
    foul_rng: random.Random | None = None,
    foul_probability: float = 0.0,
) -> MD3Result:
    """
    Simula uma MD3 (melhor de três séries MD5).

    A disputa termina quando um time vence duas séries MD5.
    O vencedor da MD3 recebe o direito de iniciar o ataque.

    `first_md5_bonus_*` são bônus aditivos de Controle aplicados APENAS
    à primeira MD5; as demais usam os Controles normais. Faltas não
    afetam esse bônus.
    """
    foul_probability = _validate_foul_probability(foul_probability)
    random_generator = resolve_rng(rng, seed)

    first_a = _boosted_control(control_a, first_md5_bonus_a, "A")
    first_b = _boosted_control(control_b, first_md5_bonus_b, "B")

    wins = {"A": 0, "B": 0}
    series = []

    while max(wins.values()) < 2:
        ca, cb = (first_a, first_b) if not series else (control_a, control_b)
        md5_result = simulate_md5(
            ca,
            cb,
            rng=random_generator,
            foul_rng=foul_rng,
            foul_probability=foul_probability,
        )

        wins[md5_result.winner] += 1
        series.append(md5_result)

    winner = "A" if wins["A"] == 2 else "B"

    return MD3Result(
        winner=winner,
        wins_a=wins["A"],
        wins_b=wins["B"],
        series=tuple(series),
    )


if __name__ == "__main__":
    # Exemplo de uso
    result = simulate_md3(control_a=75, control_b=65, seed=42)

    print(f"Vencedor da MD3: {result.winner}")
    print(f"Placar: {result.wins_a} x {result.wins_b}")

    for i, md5 in enumerate(result.series, start=1):
        print(f"MD5 {i}: {md5.winner} ({md5.wins_a} x {md5.wins_b})")
