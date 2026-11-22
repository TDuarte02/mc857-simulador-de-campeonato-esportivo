"""
Experimentos de calibração (Issue #14) com múltiplas posses por ciclo (Issue #29).

Rode com: python -m python_prototype.experiments
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, fields

from python_prototype.attack import AttackParameters, DEFAULT_ATTACK_PARAMETERS
from python_prototype.collective_attributes import Player
from python_prototype.match import (
    CYCLES_PER_MATCH,
    MatchEventType,
    create_match,
    play_match,
)

POSITIONS_433 = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "RW", "ST", "LW"]
FORMATION_433 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]


def make_squad(prefix: str, rating: int) -> list[Player]:
    attrs = [f.name for f in fields(Player) if f.name not in ("name", "pos")]
    return [
        Player(name=f"{prefix}{i}", pos=pos, **{a: rating for a in attrs})
        for i, pos in enumerate(POSITIONS_433)
    ]


@dataclass(frozen=True)
class ExperimentResult:
    k: int
    n_matches: int
    goals_per_match: float
    sequences_per_match: float
    goals_per_cycle: float
    attempts_per_sequence: float
    cycle_goal_dist: dict[int, int]    # gols no ciclo -> nº de ciclos
    match_goal_dist: dict[int, int]    # gols na partida -> nº de partidas
    max_goals_in_cycle: int
    max_goals_in_match: int
    a_wins: float
    draws: float
    b_wins: float


def run_experiment(
    rating_a: int = 70,
    rating_b: int = 70,
    *,
    k: int = 1,
    n: int = 4000,
    params: AttackParameters = DEFAULT_ATTACK_PARAMETERS,
    recovery_control_bonus: float = 5.0,
) -> ExperimentResult:
    """Simula `n` partidas (seeds 0..n-1) e agrega as estatísticas."""
    cycle_dist: Counter[int] = Counter()
    match_dist: Counter[int] = Counter()
    total_goals = total_seq = total_attempts = 0
    a_wins = draws = b_wins = 0

    for seed in range(n):
        state = create_match(
            make_squad("A", rating_a), FORMATION_433,
            make_squad("B", rating_b), FORMATION_433,
        )
        results = play_match(
            state,
            seed=seed,
            attack_params=params,
            recovery_control_bonus=recovery_control_bonus,
            possessions_per_cycle=k,
        )

        match_goals = sum(r.goals for r in results)
        goal_events = sum(e.type is MatchEventType.GOAL for e in state.events)
        # Consistência interna: cada gol contado uma única vez.
        assert sum(state.score.values()) == match_goals == goal_events

        for r in results:
            cycle_dist[r.goals] += 1
            total_seq += len(r.possessions)
            total_attempts += sum(p.attack.attempts for p in r.possessions)

        match_dist[match_goals] += 1
        total_goals += match_goals
        sa, sb = state.score["A"], state.score["B"]
        a_wins += sa > sb
        draws += sa == sb
        b_wins += sa < sb

    n_cycles = n * CYCLES_PER_MATCH
    return ExperimentResult(
        k=k,
        n_matches=n,
        goals_per_match=total_goals / n,
        sequences_per_match=total_seq / n,
        goals_per_cycle=total_goals / n_cycles,
        attempts_per_sequence=total_attempts / total_seq,
        cycle_goal_dist=dict(sorted(cycle_dist.items())),
        match_goal_dist=dict(sorted(match_dist.items())),
        max_goals_in_cycle=max(cycle_dist),
        max_goals_in_match=max(match_dist),
        a_wins=a_wins / n,
        draws=draws / n,
        b_wins=b_wins / n,
    )


def expected_goal_probability_per_sequence(
    q: float = 0.5, params: AttackParameters = DEFAULT_ATTACK_PARAMETERS
) -> float:
    """
    P(gol) de uma sequencia ofensiva, em forma fechada (soma da serie):
    sum_n  g_max*q * prod_{k<n} P_C(k).
    Com times iguais q = 0.5 para qualquer atacante, entao vale para o ciclo todo.
    """
    p_goal = params.g_max * q
    survive = 1.0
    total = 0.0
    for k in range(1, 500):
        total += survive * p_goal
        survive *= params.c_max * params.r ** (k - 1) * q
        if survive < 1e-15:
            break
    return total


def print_report(r: ExperimentResult, expected_mean: float | None = None) -> None:
    print(f"\n=== K = {r.k} ({r.n_matches} partidas) ===")
    line = f"Gols por partida:        {r.goals_per_match:.3f}"
    if expected_mean is not None:
        line += f"  (analítico: {expected_mean:.3f})"
    print(line)
    print(f"Sequencias por partida:  {r.sequences_per_match:.2f}")
    print(f"Gols por ciclo:          {r.goals_per_cycle:.3f}")
    print(f"Tentativas por sequência:{r.attempts_per_sequence:.3f}")
    print(f"Max. gols em um ciclo:   {r.max_goals_in_cycle}")
    print(f"Max. gols em uma partida:{r.max_goals_in_match}")
    print(f"A/empate/B:              {r.a_wins:.1%} / {r.draws:.1%} / {r.b_wins:.1%}")
    print("Distribuicao de gols por ciclo:")
    total = sum(r.cycle_goal_dist.values())
    for goals, c in r.cycle_goal_dist.items():
        print(f"  {goals} gol(s): {c / total:6.1%}")


def verify(results: dict[int, ExperimentResult], params: AttackParameters) -> bool:
    """Confirma o comportamento esperado da Issue #29 (times iguais)."""
    p = expected_goal_probability_per_sequence(0.5, params)
    ok = True

    def check(label: str, cond: bool) -> None:
        nonlocal ok
        ok &= cond
        print(f"[{'OK' if cond else 'FALHA'}] {label}")

    print("\n=== Verificaçoes ===")
    for k, r in sorted(results.items()):
        expected = CYCLES_PER_MATCH * k * p
        check(
            f"K={k}: sequencias por partida == {CYCLES_PER_MATCH * k}",
            r.sequences_per_match == CYCLES_PER_MATCH * k,
        )
        check(
            f"K={k}: gols por partida ({r.goals_per_match:.3f}) ~ analitico ({expected:.3f})",
            abs(r.goals_per_match - expected) < 0.08,
        )
        check(
            f"K={k}: nenhum ciclo com mais de {k} gols",
            r.max_goals_in_cycle <= k,
        )
    if 1 in results:
        check("K=1: no maximo 1 gol por ciclo e 6 por partida",
              results[1].max_goals_in_cycle <= 1 and results[1].max_goals_in_match <= 6)
    multi = [r for k, r in results.items() if k > 1]
    check("K>1: existem ciclos com mais de 1 gol",
          all(r.max_goals_in_cycle > 1 for r in multi))
    check("K>1: existem partidas com mais de 6 gols",
          any(r.max_goals_in_match > 6 for r in multi))
    ks = sorted(results)
    check("gols por partida crescem com K",
          all(results[a].goals_per_match < results[b].goals_per_match
              for a, b in zip(ks, ks[1:])))
    return ok

def to_markdown(
    results: dict[int, ExperimentResult],
    params: AttackParameters,
    rating_a: int,
    rating_b: int,
) -> str:
    p = expected_goal_probability_per_sequence(0.5, params)
    lines = [
        "# Experimentos: posses por ciclo (Issue #29)",
        "",
        f"- Times: {rating_a} x {rating_b}",
        f"- Parametros: g_max={params.g_max}, c_max={params.c_max}, r={params.r}",
        f"- P(gol por sequência, times iguais): {p:.4f}",
        "",
        "## Resumo por K",
        "",
        "| K | Gols/partida | Analitico | Sequencias/partida | Gols/ciclo "
        "| Tentativas/seq. | Max. gols/ciclo | Max. gols/partida | A | Empate | B |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for k, r in sorted(results.items()):
        analytic = f"{CYCLES_PER_MATCH * k * p:.3f}" if rating_a == rating_b else "-"
        lines.append(
            f"| {k} | {r.goals_per_match:.3f} | {analytic} | "
            f"{r.sequences_per_match:.2f} | {r.goals_per_cycle:.3f} | "
            f"{r.attempts_per_sequence:.3f} | {r.max_goals_in_cycle} | "
            f"{r.max_goals_in_match} | {r.a_wins:.1%} | {r.draws:.1%} | {r.b_wins:.1%} |"
        )

    for k, r in sorted(results.items()):
        total_c = sum(r.cycle_goal_dist.values())
        total_m = sum(r.match_goal_dist.values())
        lines += [
            "",
            f"## K = {k} ({r.n_matches} partidas)",
            "",
            "**Gols por ciclo**",
            "",
            "| Gols | % dos ciclos |",
            "|---|---|",
        ]
        lines += [f"| {g} | {c / total_c:.1%} |" for g, c in r.cycle_goal_dist.items()]
        lines += [
            "",
            "**Gols por partida**",
            "",
            "| Gols | % das partidas |",
            "|---|---|",
        ]
        lines += [f"| {g} | {c / total_m:.1%} |" for g, c in r.match_goal_dist.items()]

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibração de posses por ciclo")
    parser.add_argument("--n", type=int, default=4000)
    parser.add_argument("--ks", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--rating-a", type=int, default=70)
    parser.add_argument("--rating-b", type=int, default=70)
    parser.add_argument("--g-max", type=float, default=DEFAULT_ATTACK_PARAMETERS.g_max)
    parser.add_argument("--c-max", type=float, default=DEFAULT_ATTACK_PARAMETERS.c_max)
    parser.add_argument("--r", type=float, default=DEFAULT_ATTACK_PARAMETERS.r)
    parser.add_argument("--md", type=str, default=None,
                    help="Caminho do arquivo .md para salvar o relatório")
    args = parser.parse_args()

    params = AttackParameters(g_max=args.g_max, c_max=args.c_max, r=args.r)
    p = expected_goal_probability_per_sequence(0.5, params)
    print(f"P(gol por sequência, times iguais) = {p:.4f}")

    results = {}
    for k in args.ks:
        r = run_experiment(args.rating_a, args.rating_b, k=k, n=args.n, params=params)
        results[k] = r
        print_report(r, CYCLES_PER_MATCH * k * p)

    if args.rating_a == args.rating_b:
        verify(results, params)
    if args.md:
        from pathlib import Path
        Path(args.md).write_text(
            to_markdown(results, params, args.rating_a, args.rating_b),
            encoding="utf-8",
        )
        print(f"\nRelatório salvo em {args.md}")


if __name__ == "__main__":
    main()