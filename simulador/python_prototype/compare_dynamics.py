"""
Comparação estatística da Issue #15: resultados com e sem cada mecânica.

Todos os cenários usam as mesmas seeds (0..n-1), então as diferenças vêm
das mecânicas e não de ruído de amostragem.

Rode com: python -m python_prototype.compare_dynamics --n 10000 --md relatorio.md
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, replace, fields
from pathlib import Path
from statistics import fmean, pvariance

from python_prototype.dynamics import (
    DynamicsConfig,
    FoulConfig,
    InjuryConfig,
    MoraleConfig,
    Player
)
from python_prototype.match import MatchEventType, create_match, play_match


POSITIONS_433 = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "RW", "ST", "LW"]
FORMATION_433 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]

def make_squad(prefix: str, rating: int) -> list[Player]:
    attrs = [f.name for f in fields(Player) if f.name not in ("name", "pos")]
    return [
        Player(name=f"{prefix}{i}", pos=pos, **{a: rating for a in attrs})
        for i, pos in enumerate(POSITIONS_433)
    ]


@dataclass(frozen=True)
class DynamicsStats:
    n: int
    mean_goals_a: float
    mean_goals_b: float
    mean_goals_total: float
    var_goals_a: float
    var_goals_b: float
    var_goal_diff: float
    var_goals_total: float
    favorite_win_rate: float | None   # None se os times forem iguais
    mean_attempts_per_sequence: float
    fouls_per_match: float
    injuries_per_match: float
    score_dist: dict[tuple[int, int], int]


def run(config: DynamicsConfig, *, rating_a: int, rating_b: int, n: int) -> DynamicsStats:
    goals_a: list[int] = []
    goals_b: list[int] = []
    dist: Counter[tuple[int, int]] = Counter()
    attempts = sequences = fouls = injuries = 0
    favorite_wins = 0

    for seed in range(n):
        state = create_match(
            make_squad("A", rating_a), FORMATION_433,
            make_squad("B", rating_b), FORMATION_433,
        )
        results = play_match(state, seed=seed, dynamics=config)

        a, b = state.score["A"], state.score["B"]
        goals_a.append(a)
        goals_b.append(b)
        dist[(a, b)] += 1
        if rating_a > rating_b:
            favorite_wins += a > b
        elif rating_b > rating_a:
            favorite_wins += b > a

        for r in results:
            for p in r.possessions:
                sequences += 1
                attempts += p.attack.attempts
        fouls += sum(e.type is MatchEventType.FALTA for e in state.events)
        injuries += sum(e.type is MatchEventType.LESAO for e in state.events)

    diff = [a - b for a, b in zip(goals_a, goals_b)]
    total = [a + b for a, b in zip(goals_a, goals_b)]
    return DynamicsStats(
        n=n,
        mean_goals_a=fmean(goals_a),
        mean_goals_b=fmean(goals_b),
        mean_goals_total=fmean(total),
        var_goals_a=pvariance(goals_a),
        var_goals_b=pvariance(goals_b),
        var_goal_diff=pvariance(diff),
        var_goals_total=pvariance(total),
        favorite_win_rate=None if rating_a == rating_b else favorite_wins / n,
        mean_attempts_per_sequence=attempts / sequences,
        fouls_per_match=fouls / n,
        injuries_per_match=injuries / n,
        score_dist=dict(dist),
    )


def scenarios() -> dict[str, DynamicsConfig]:
    off = DynamicsConfig.disabled()
    return {
        "base (tudo desligado)": off,
        "só moral": replace(off, morale=MoraleConfig()),
        "só faltas": replace(off, fouls=FoulConfig()),
        "faltas + lesões": replace(off, fouls=FoulConfig(), injuries=InjuryConfig()),
        "tudo ligado": DynamicsConfig(),
    }


def format_report(results: dict[str, DynamicsStats], rating_a: int, rating_b: int) -> str:
    n = next(iter(results.values())).n
    cfg = DynamicsConfig()
    lines = [
        "# Comparação estatística (Issue #15)",
        "",
        f"- Times: {rating_a} x {rating_b} | partidas por cenário: {n} | seeds 0..{n - 1}",
        f"- Moral: M={cfg.morale.limit:g}, beta={cfg.morale.beta:g}",
        f"- Faltas: p={cfg.fouls.probability:g} por confronto | "
        f"Lesões: p={cfg.injuries.probability:g} por falta (só evento)",
        "",
        "## Resumo",
        "",
        "| Cenário | Gols A | Gols B | Gols/partida | Var A | Var B | Var saldo "
        "| Var total | Favorito vence | Tent./seq. | Faltas/jogo | Lesões/jogo |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, s in results.items():
        fav = "-" if s.favorite_win_rate is None else f"{s.favorite_win_rate:.1%}"
        lines.append(
            f"| {name} | {s.mean_goals_a:.3f} | {s.mean_goals_b:.3f} | {s.mean_goals_total:.3f} "
            f"| {s.var_goals_a:.3f} | {s.var_goals_b:.3f} | {s.var_goal_diff:.3f} "
            f"| {s.var_goals_total:.3f} | {fav} | {s.mean_attempts_per_sequence:.3f} "
            f"| {s.fouls_per_match:.2f} | {s.injuries_per_match:.2f} |"
        )

    base = results["base (tudo desligado)"]
    morale = results["só moral"]
    lines += [
        "",
        "## Hipótese: a variância do placar aumenta com a moral ativa",
        "",
        f"- Var do saldo: {base.var_goal_diff:.3f} -> {morale.var_goal_diff:.3f}",
        f"- Var dos gols totais: {base.var_goals_total:.3f} -> {morale.var_goals_total:.3f}",
        f"- Var gols A: {base.var_goals_a:.3f} -> {morale.var_goals_a:.3f} | "
        f"Var gols B: {base.var_goals_b:.3f} -> {morale.var_goals_b:.3f}",
    ]

    for name, s in results.items():
        lines += ["", f"## Distribuição de placares: {name}", "", "| Placar A x B | % das partidas |", "|---|---|"]
        top = sorted(s.score_dist.items(), key=lambda kv: -kv[1])[:10]
        lines += [f"| {a} x {b} | {c / s.n:.1%} |" for (a, b), c in top]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Comparação estatística da Issue #15")
    parser.add_argument("--n", type=int, default=10_000)
    parser.add_argument("--rating-a", type=int, default=75)
    parser.add_argument("--rating-b", type=int, default=65)
    parser.add_argument("--md", type=str, default=None, help="Salva o relatório em .md")
    args = parser.parse_args()

    results = {}
    for name, config in scenarios().items():
        print(f"Simulando: {name} ...")
        results[name] = run(config, rating_a=args.rating_a, rating_b=args.rating_b, n=args.n)

    report = format_report(results, args.rating_a, args.rating_b)
    print("\n" + report)
    if args.md:
        Path(args.md).write_text(report, encoding="utf-8")
        print(f"Relatório salvo em {args.md}")


if __name__ == "__main__":
    main()
