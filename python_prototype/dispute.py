
from __future__ import annotations

import random
from dataclasses import dataclass

from python_prototype.common import TeamId, resolve_rng
from python_prototype.control import simulate_control_duel


@dataclass(frozen=True)
class MD5Result:
    winner: TeamId
    wins_a: int
    wins_b: int
    duels: tuple[TeamId, ...]


@dataclass(frozen=True)
class MD3Result:
    winner: TeamId
    wins_a: int
    wins_b: int
    series: tuple[MD5Result, ...]


def simulate_md5(
    control_a,
    control_b,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
) -> MD5Result:
    """
    Simula uma série MD5 (melhor de cinco).

    A série termina quando um time alcança três vitórias.
    """
    random_generator = resolve_rng(rng, seed)

    wins = {"A": 0, "B": 0}
    duels = []

    while max(wins.values()) < 3:
        duel_winner = simulate_control_duel(
            control_a,
            control_b,
            rng=random_generator,
        )

        wins[duel_winner] += 1
        duels.append(duel_winner)

    winner = "A" if wins["A"] == 3 else "B"

    return MD5Result(
        winner=winner,
        wins_a=wins["A"],
        wins_b=wins["B"],
        duels=tuple(duels),
    )


def simulate_md3(
    control_a,
    control_b,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
) -> MD3Result:
    """
    Simula uma MD3 (melhor de três séries MD5).

    A disputa termina quando um time vence duas séries MD5.
    O vencedor da MD3 recebe o direito de iniciar o ataque.
    """
    random_generator = resolve_rng(rng, seed)

    wins = {"A": 0, "B": 0}
    series = []

    while max(wins.values()) < 2:
        md5_result = simulate_md5(
            control_a,
            control_b,
            rng=random_generator,
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