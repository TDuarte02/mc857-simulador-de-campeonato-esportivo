"""
Experimentos em lote para verificar o comportamento estatístico do simulador.

O módulo apenas OBSERVA o motor: cada partida é jogada por `play_match` e as
métricas são extraídas dos `CycleResult` e do placar devolvidos. Nada aqui
altera `match.py`, `attack.py` ou `dispute.py`.

Reprodutibilidade: a partida de índice i usa a semente `base_seed + i`.
Configurações diferentes comparadas com a mesma `base_seed` usam, portanto,
as mesmas sementes (números aleatórios comuns), o que reduz o ruído das
comparações.

Rode com:  python -m python_prototype.experiments [arquivo_de_saida.md]
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

from python_prototype.attack import (
    AttackOutcome,
    AttackParameters,
    DEFAULT_ATTACK_PARAMETERS,
)
from python_prototype.collective_attributes import Player
from python_prototype.common import TeamId, ensure_finite_non_negative
from python_prototype.match import (
    DEFAULT_RECOVERY_CONTROL_BONUS,
    MatchState,
    create_match,
    play_match,
)

# ============================================================
# Configuração
# ============================================================

DEFAULT_N_MATCHES = 4000


@dataclass(frozen=True)
class ExperimentConfig:
    """
    Parâmetros de um experimento.

    - n_matches: quantidade de partidas simuladas.
    - base_seed: a partida i usa a semente `base_seed + i`.
    - attack_params: parâmetros da sequência ofensiva.
    - recovery_control_bonus: bônus de Controle após perda de posse.
    """

    n_matches: int = DEFAULT_N_MATCHES
    base_seed: int = 0
    attack_params: AttackParameters = DEFAULT_ATTACK_PARAMETERS
    recovery_control_bonus: float = DEFAULT_RECOVERY_CONTROL_BONUS

    def __post_init__(self) -> None:
        if isinstance(self.n_matches, bool) or not isinstance(self.n_matches, int):
            raise ValueError(f"n_matches deve ser inteiro; recebido: {self.n_matches!r}")
        if self.n_matches < 1:
            raise ValueError("n_matches deve ser pelo menos 1.")
        if isinstance(self.base_seed, bool) or not isinstance(self.base_seed, int):
            raise ValueError(f"base_seed deve ser inteiro; recebido: {self.base_seed!r}")
        ensure_finite_non_negative(
            self.recovery_control_bonus, "Bônus de recuperação de posse"
        )


@dataclass(frozen=True)
class MatchSetup:
    """
    Descreve os dois times de um experimento.

    O estado da partida é mutável, então cada partida é criada do zero por
    `build()`. `modifiers_a/b` são ajustes aditivos (chaves "attack",
    "defense", "control") aplicados antes da partida, úteis para isolar o
    efeito de um único atributo.
    """

    players_a: tuple[Player, ...]
    formation_a: tuple[str, ...]
    players_b: tuple[Player, ...]
    formation_b: tuple[str, ...]
    modifiers_a: Mapping[str, float] = field(default_factory=dict)
    modifiers_b: Mapping[str, float] = field(default_factory=dict)

    def build(self) -> MatchState:
        state = create_match(
            self.players_a, self.formation_a, self.players_b, self.formation_b
        )
        state.teams["A"].modifiers.update(self.modifiers_a)
        state.teams["B"].modifiers.update(self.modifiers_b)
        return state


def with_modifiers(
    setup: MatchSetup,
    *,
    a: Mapping[str, float] | None = None,
    b: Mapping[str, float] | None = None,
) -> MatchSetup:
    """Cópia de `setup` com modificadores adicionais (substituem chaves iguais)."""
    return replace(
        setup,
        modifiers_a={**setup.modifiers_a, **(a or {})},
        modifiers_b={**setup.modifiers_b, **(b or {})},
    )


# ============================================================
# Resultado
# ============================================================


def standard_error(proportion: float, n: int) -> float:
    """Erro-padrão (aproximação normal) de uma proporção observada em n casos."""
    if n <= 0:
        return math.nan
    return math.sqrt(max(0.0, proportion * (1.0 - proportion)) / n)


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else math.nan


@dataclass(frozen=True)
class ExperimentResult:
    """Contagens brutas de um experimento; as taxas são propriedades derivadas."""

    config: ExperimentConfig
    matches: int
    goals_a: int
    goals_b: int
    a_wins: int
    draws: int
    b_wins: int
    # tentativas por sequência -> quantidade de sequências
    attempts_histogram: Mapping[int, int]
    # desfecho de cada TENTATIVA (CONTINUE, GOAL, POSSESSION_LOST)
    attempt_outcomes: Mapping[AttackOutcome, int]
    # por time atacante
    sequences_by_team: Mapping[TeamId, int]
    attempts_by_team: Mapping[TeamId, int]
    goals_by_team: Mapping[TeamId, int]
    # disputas de Controle
    duels_won_a: int
    duels_total: int
    md3_won_a: int
    md3_total: int

    # --- partidas ---
    @property
    def mean_goals_per_match(self) -> float:
        return (self.goals_a + self.goals_b) / self.matches

    @property
    def mean_goals_a(self) -> float:
        return self.goals_a / self.matches

    @property
    def mean_goals_b(self) -> float:
        return self.goals_b / self.matches

    @property
    def mean_goal_difference(self) -> float:
        return (self.goals_a - self.goals_b) / self.matches

    @property
    def a_win_rate(self) -> float:
        return self.a_wins / self.matches

    @property
    def draw_rate(self) -> float:
        return self.draws / self.matches

    @property
    def b_win_rate(self) -> float:
        return self.b_wins / self.matches

    # --- sequências ofensivas ---
    @property
    def sequences(self) -> int:
        return sum(self.attempts_histogram.values())

    @property
    def total_attempts(self) -> int:
        return sum(k * v for k, v in self.attempts_histogram.items())

    @property
    def mean_attempts_per_sequence(self) -> float:
        return _ratio(self.total_attempts, self.sequences)

    @property
    def continuation_rate(self) -> float:
        """Fração das tentativas que terminaram em continuação."""
        return _ratio(self.attempt_outcomes.get(AttackOutcome.CONTINUE, 0), self.total_attempts)

    @property
    def goal_rate_per_attempt(self) -> float:
        return _ratio(self.attempt_outcomes.get(AttackOutcome.GOAL, 0), self.total_attempts)

    @property
    def loss_rate_per_attempt(self) -> float:
        return _ratio(
            self.attempt_outcomes.get(AttackOutcome.POSSESSION_LOST, 0), self.total_attempts
        )

    @property
    def goal_rate_per_sequence(self) -> float:
        return _ratio(sum(self.goals_by_team.values()), self.sequences)

    def goal_rate_per_attempt_of(self, team: TeamId) -> float:
        """Gols por tentativa considerando só os ataques de `team`."""
        return _ratio(self.goals_by_team.get(team, 0), self.attempts_by_team.get(team, 0))

    # --- Controle ---
    @property
    def duel_win_rate_a(self) -> float:
        return _ratio(self.duels_won_a, self.duels_total)

    @property
    def md3_win_rate_a(self) -> float:
        return _ratio(self.md3_won_a, self.md3_total)

    def summary(self) -> dict[str, float]:
        """Métricas principais, em formato simples para tabelas."""
        return {
            "partidas": self.matches,
            "gols_por_partida": self.mean_goals_per_match,
            "vitorias_a": self.a_win_rate,
            "empates": self.draw_rate,
            "vitorias_b": self.b_win_rate,
            "tentativas_por_sequencia": self.mean_attempts_per_sequence,
            "continuacao_por_tentativa": self.continuation_rate,
            "gol_por_tentativa": self.goal_rate_per_attempt,
            "perda_por_tentativa": self.loss_rate_per_attempt,
            "duelos_ganhos_a": self.duel_win_rate_a,
            "md3_ganhas_a": self.md3_win_rate_a,
        }


# ============================================================
# Execução
# ============================================================


def run_experiment(
    setup: MatchSetup, config: ExperimentConfig = ExperimentConfig()
) -> ExperimentResult:
    """Joga `config.n_matches` partidas e agrega as métricas."""
    goals = {"A": 0, "B": 0}
    wins = {"A": 0, "draw": 0, "B": 0}
    histogram: Counter[int] = Counter()
    attempt_outcomes: Counter[AttackOutcome] = Counter()
    sequences_by_team: Counter[str] = Counter()
    attempts_by_team: Counter[str] = Counter()
    goals_by_team: Counter[str] = Counter()
    duels_won_a = duels_total = md3_won_a = md3_total = 0

    for i in range(config.n_matches):
        state = setup.build()
        results = play_match(
            state,
            seed=config.base_seed + i,
            attack_params=config.attack_params,
            recovery_control_bonus=config.recovery_control_bonus,
        )

        goals["A"] += state.score["A"]
        goals["B"] += state.score["B"]
        if state.score["A"] > state.score["B"]:
            wins["A"] += 1
        elif state.score["A"] < state.score["B"]:
            wins["B"] += 1
        else:
            wins["draw"] += 1

        for result in results:
            team = result.attacking_team
            histogram[result.attack.attempts] += 1
            attempt_outcomes.update(result.attack.history)
            sequences_by_team[team] += 1
            attempts_by_team[team] += result.attack.attempts
            if result.is_goal:
                goals_by_team[team] += 1

            md3_total += 1
            md3_won_a += result.md3.winner == "A"
            for md5 in result.md3.series:
                duels_total += len(md5.duels)
                duels_won_a += md5.wins_a

    return ExperimentResult(
        config=config,
        matches=config.n_matches,
        goals_a=goals["A"],
        goals_b=goals["B"],
        a_wins=wins["A"],
        draws=wins["draw"],
        b_wins=wins["B"],
        attempts_histogram=dict(sorted(histogram.items())),
        attempt_outcomes=dict(attempt_outcomes),
        sequences_by_team=dict(sequences_by_team),
        attempts_by_team=dict(attempts_by_team),
        goals_by_team=dict(goals_by_team),
        duels_won_a=duels_won_a,
        duels_total=duels_total,
        md3_won_a=md3_won_a,
        md3_total=md3_total,
    )


def compare_configs(
    setup: MatchSetup, configs: Mapping[str, ExperimentConfig]
) -> dict[str, ExperimentResult]:
    """Roda o mesmo confronto sob várias configurações de parâmetros."""
    return {label: run_experiment(setup, config) for label, config in configs.items()}


def compare_setups(
    setups: Mapping[str, MatchSetup], config: ExperimentConfig = ExperimentConfig()
) -> dict[str, ExperimentResult]:
    """Roda a mesma configuração sobre vários confrontos (p. ex. diferenças de nível)."""
    return {label: run_experiment(setup, config) for label, setup in setups.items()}


# ============================================================
# Montagem de times uniformes (para experimentos controlados)
# ============================================================

_POSITIONS_433 = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "RW", "ST", "LW"]
_FORMATION_433 = ("GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W")


def _uniform_player(name: str, pos: str, rating: int) -> Player:
    return Player(name, pos, *([rating] * 18))


def uniform_setup(
    rating_a: int,
    rating_b: int,
    *,
    modifiers_a: Mapping[str, float] | None = None,
    modifiers_b: Mapping[str, float] | None = None,
) -> MatchSetup:
    """Dois times 4-3-3 com todos os atributos iguais ao rating de cada lado."""
    squad_a = tuple(_uniform_player(f"A{i}", p, rating_a) for i, p in enumerate(_POSITIONS_433))
    squad_b = tuple(_uniform_player(f"B{i}", p, rating_b) for i, p in enumerate(_POSITIONS_433))
    return MatchSetup(
        squad_a, _FORMATION_433, squad_b, _FORMATION_433,
        modifiers_a=dict(modifiers_a or {}), modifiers_b=dict(modifiers_b or {}),
    )


# ============================================================
# Relatório
# ============================================================


def describe_config(config: ExperimentConfig) -> str:
    p = config.attack_params
    return (
        f"n={config.n_matches}, seed_base={config.base_seed}, "
        f"g_max={p.g_max}, c_max={p.c_max}, r={p.r}, "
        f"bônus_recuperação={config.recovery_control_bonus:g}"
    )


def format_report(results: Mapping[str, ExperimentResult], title: str = "Experimentos") -> str:
    """Tabela em Markdown com as métricas principais e os parâmetros usados."""
    header = (
        "| Cenário | Gols/jogo | Vit. A | Empate | Vit. B | Tent./seq. "
        "| Continuação | Gol/tent. | Perda | Duelos A | MD3 A |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for label, r in results.items():
        rows.append(
            f"| {label} | {r.mean_goals_per_match:.2f} | {r.a_win_rate:.1%} | "
            f"{r.draw_rate:.1%} | {r.b_win_rate:.1%} | {r.mean_attempts_per_sequence:.2f} | "
            f"{r.continuation_rate:.1%} | {r.goal_rate_per_attempt:.1%} | "
            f"{r.loss_rate_per_attempt:.1%} | {r.duel_win_rate_a:.1%} | {r.md3_win_rate_a:.1%} |"
        )
    params = "\n".join(f"- **{label}**: {describe_config(r.config)}" for label, r in results.items())
    return f"# {title}\n\n{header}" + "\n".join(rows) + f"\n\n## Parâmetros\n\n{params}\n"


# ============================================================
# Execução direta
# ============================================================

if __name__ == "__main__":
    base = ExperimentConfig()

    matchups = compare_setups(
        {
            "70 x 70": uniform_setup(70, 70),
            "72 x 68": uniform_setup(72, 68),
            "80 x 60": uniform_setup(80, 60),
            "90 x 40": uniform_setup(90, 40),
            "100 x 20": uniform_setup(100, 20),
        },
        base,
    )
    
    parameter_sweep = compare_configs(
        uniform_setup(70, 70),
        {
            "padrão": base,
            "g_max=0.20": replace(base, attack_params=AttackParameters(g_max=0.20)),
            "c_max=0.30": replace(base, attack_params=AttackParameters(c_max=0.30)),
            "r=0.50": replace(base, attack_params=AttackParameters(r=0.50)),
            "sem bônus": replace(base, recovery_control_bonus=0.0),
            "bônus=10": replace(base, recovery_control_bonus=10.0),
        },
    )

    report = (
        format_report(matchups, "Diferença de nível entre os times")
        + "\n"
        + format_report(parameter_sweep, "Variação de parâmetros (70 x 70)")
    )
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(report)
    print(report)
