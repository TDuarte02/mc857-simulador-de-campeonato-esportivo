"""
Preparação do torneio (Issue #33): sementes derivadas, configuração única,
leitura do dataset, elenco de 23, escalação padrão automática, seleções
sintéticas, força e sorteio dos grupos por potes.

As próximas issues acrescentam os seus parâmetros a `TournamentConfig`.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, replace
from pathlib import Path

from python_prototype.attack import DEFAULT_ATTACK_PARAMETERS, AttackParameters
from python_prototype.collective_attributes import (
    POSITION_SECTORS,
    Player,
    TeamAttributes,
    calculate_team_attributes,
    canonical_position,
    formation_distribution,
)
from python_prototype.common import ensure_finite_non_negative
from python_prototype.dynamics import DynamicsConfig
from python_prototype.match import (
    DEFAULT_POSSESSIONS_PER_CYCLE,
    DEFAULT_RECOVERY_CONTROL_BONUS,
    PossessionsSpec,
    _validate_possessions,
)

from python_prototype.penalties import DEFAULT_PENALTY_CONFIG, PenaltyConfig

# ============================================================
# Constantes
# ============================================================

DEFAULT_NATIONS: tuple[str, ...] = (
    "Argentina", "Canada", "Peru", "Chile",
    "Mexico", "Ecuador", "Venezuela", "Jamaica",
    "United States", "Uruguay", "Panama", "Bolivia",
    "Brazil", "Colombia", "Paraguay", "Costa Rica",
)
DEFAULT_FORMATION: tuple[str, ...] = (
    "GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W",
)

GROUP_NAMES: tuple[str, ...] = ("A", "B", "C", "D")
TEAMS_PER_GROUP = 4
N_TEAMS = len(GROUP_NAMES) * TEAMS_PER_GROUP  # 16
N_POTS = TEAMS_PER_GROUP

# Ordem de preenchimento dos slots da escalação.
SECTOR_ORDER = {"GK": 0, "DEF": 1, "MID": 2, "FW": 3}

# Atributos de linha que podem vir vazios em goleiros (viram 0).
LINE_ATTRIBUTES = ("pace", "shooting", "passing", "dribbling", "defending", "physic")

_NUMERIC_FIELDS = tuple(f for f in fields(Player) if f.name not in ("name", "pos"))
_REQUIRED_COLUMNS = ("nationality_name", "player_positions", *(f.name for f in _NUMERIC_FIELDS))


class SetupError(ValueError):
    """Erro explícito de preparação do torneio (dataset, elenco ou escalação)."""


# ============================================================
# Sementes
# ============================================================

def derive_seed(tournament_seed: int, *labels: object) -> int:
    """
    Semente derivada e estável: SHA-256 de (semente, rótulos), 64 bits.

    Idêntica entre execuções e processos (não usa `hash()` nem contadores).
    """
    if isinstance(tournament_seed, bool) or not isinstance(tournament_seed, int):
        raise ValueError(f"A semente do torneio deve ser um inteiro; recebido: {tournament_seed!r}")
    payload = json.dumps(
        [tournament_seed, *(str(label) for label in labels)],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


# ============================================================
# Configuração
# ============================================================

@dataclass(frozen=True)
class TournamentConfig:
    seed: int = 2026
    nations: tuple[str, ...] = DEFAULT_NATIONS
    formation: tuple[str, ...] = DEFAULT_FORMATION
    squad_size: int = 23
    squad_goalkeepers: int = 3
    dataset_path: Path | str = "players_data.csv"
    # Simulação das partidas (Issues #11, #13, #15). Configuração única:
    # `possessions_per_cycle` é sempre passado explicitamente a `play_match`.
    attack_params: AttackParameters = DEFAULT_ATTACK_PARAMETERS
    recovery_control_bonus: float = DEFAULT_RECOVERY_CONTROL_BONUS
    possessions_per_cycle: PossessionsSpec = DEFAULT_POSSESSIONS_PER_CYCLE
    dynamics: DynamicsConfig = DynamicsConfig()
    penalties: PenaltyConfig = DEFAULT_PENALTY_CONFIG

    def __post_init__(self) -> None:
        object.__setattr__(self, "nations", tuple(self.nations))
        object.__setattr__(self, "formation", tuple(self.formation))
        object.__setattr__(self, "dataset_path", Path(self.dataset_path))

        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError(f"seed deve ser inteiro; recebido: {self.seed!r}")
        if len(self.nations) != N_TEAMS or len(set(self.nations)) != N_TEAMS:
            raise ValueError(f"O torneio exige {N_TEAMS} nações distintas.")
        if len(self.formation) != 11:
            raise ValueError("A formação padrão deve ter exatamente 11 slots.")
        counts = formation_distribution(self.formation)  # valida os nomes dos slots
        if counts["GK"] != 1:
            raise ValueError("A formação padrão deve ter exatamente um goleiro.")
        for label, value in (("squad_size", self.squad_size), ("squad_goalkeepers", self.squad_goalkeepers)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{label} deve ser inteiro; recebido: {value!r}")
        if self.squad_goalkeepers < 1:
            raise ValueError("O elenco precisa de pelo menos 1 goleiro.")
        if self.squad_size - self.squad_goalkeepers < 10:
            raise ValueError("O elenco precisa de pelo menos 10 jogadores de linha.")
        if not isinstance(self.penalties, PenaltyConfig):
            raise ValueError(f"penalties deve ser um PenaltyConfig; recebido: {self.penalties!r}")

        ensure_finite_non_negative(self.recovery_control_bonus, "Bônus de recuperação de posse")
        _validate_possessions(self.possessions_per_cycle)
        self.dynamics.validate(self.attack_params)


# ============================================================
# Estruturas
# ============================================================

@dataclass(frozen=True)
class SquadMember:
    """Jogador do elenco com todas as suas posições reconhecidas."""

    player: Player
    positions: tuple[str, ...]  # texto original das posições reconhecidas

    @property
    def canonical_positions(self) -> frozenset[str]:
        return frozenset(canonical_position(p) for p in self.positions)

    @property
    def sectors(self) -> frozenset[str]:
        return frozenset(POSITION_SECTORS[c] for c in self.canonical_positions)

    @property
    def is_goalkeeper(self) -> bool:
        return "GK" in self.canonical_positions


@dataclass(frozen=True)
class NationalTeam:
    name: str
    squad: tuple[SquadMember, ...]
    formation: tuple[str, ...]
    lineup: tuple[Player, ...]      # na ordem dos slots da formação
    attributes: TeamAttributes      # com modificadores de formação

    @property
    def strength(self) -> float:
        """Média de Ataque, Defesa e Controle da escalação padrão."""
        a = self.attributes
        return (a.attack + a.defense + a.control) / 3


@dataclass(frozen=True)
class Group:
    name: str
    teams: tuple[NationalTeam, ...]  # índice + 1 = posição no grupo = nº do pote

    def position_of(self, team_name: str) -> int:
        for index, team in enumerate(self.teams, start=1):
            if team.name == team_name:
                return index
        raise ValueError(f"{team_name!r} não está no grupo {self.name}.")


@dataclass(frozen=True)
class DrawResult:
    pots: tuple[tuple[NationalTeam, ...], ...]
    groups: tuple[Group, ...]


@dataclass(frozen=True)
class DiscardedRow:
    line: int
    name: str
    nation: str
    reason: str


@dataclass(frozen=True)
class DatasetReport:
    """Linhas lidas (das nações pedidas) e as descartadas, com o motivo."""

    rows_read: int
    discarded: tuple[DiscardedRow, ...]

    @property
    def reasons(self) -> Counter[str]:
        return Counter(row.reason for row in self.discarded)


@dataclass(frozen=True)
class TournamentSetup:
    config: TournamentConfig
    teams: tuple[NationalTeam, ...]  # na ordem de `config.nations`
    draw: DrawResult
    report: DatasetReport | None     # None com seleções sintéticas


# ============================================================
# Leitura do dataset
# ============================================================

class _RowError(Exception):
    pass


def _row_name(row: Mapping[str, str | None]) -> str:
    return (row.get("short_name") or row.get("long_name") or "").strip()


def _parse_row(row: Mapping[str, str | None]) -> SquadMember:
    name = _row_name(row)
    if not name:
        raise _RowError("nome vazio")

    recognized: list[tuple[str, str]] = []
    for raw in (row.get("player_positions") or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            recognized.append((raw, canonical_position(raw)))
        except ValueError:
            continue  # posição não reconhecida: ignorada
    if not recognized:
        raise _RowError("nenhuma posição reconhecida")

    # Goleiro é só goleiro; jogador de linha nunca é goleiro.
    gk = [raw for raw, canon in recognized if canon == "GK"]
    if gk:
        positions: tuple[str, ...] = (gk[0],)
    else:
        positions = tuple(raw for raw, _ in recognized)

    values = {f.name: (row.get(f.name) or "").strip() for f in _NUMERIC_FIELDS}
    for attr in LINE_ATTRIBUTES:
        if values[attr] == "":
            if not gk:
                raise _RowError(f"atributo de linha vazio em jogador de linha: {attr}")
            values[attr] = "0"

    try:
        player = Player.from_csv_row(name, positions[0], values)
    except ValueError as exc:
        raise _RowError(str(exc)) from None
    return SquadMember(player, positions)


def read_players_csv(
    path: Path | str, nations: Sequence[str]
) -> tuple[dict[str, list[SquadMember]], DatasetReport]:
    """
    Lê o CSV e devolve os jogadores válidos por nação e o relatório de descartes.

    Só as linhas das `nations` são consideradas; as demais são filtradas
    (não contam como descartadas).
    """
    wanted = set(nations)
    members: dict[str, list[SquadMember]] = {n: [] for n in nations}
    discarded: list[DiscardedRow] = []
    rows_read = 0

    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = set(reader.fieldnames or [])
        missing = [c for c in _REQUIRED_COLUMNS if c not in header]
        if not ({"short_name", "long_name"} & header):
            missing.append("short_name/long_name")
        if missing:
            raise SetupError(f"Dataset {str(path)!r} sem as colunas: {missing}")

        for row in reader:
            nation = (row.get("nationality_name") or "").strip()
            if nation not in wanted:
                continue
            rows_read += 1
            try:
                members[nation].append(_parse_row(row))
            except _RowError as exc:
                discarded.append(DiscardedRow(reader.line_num, _row_name(row), nation, str(exc)))

    return members, DatasetReport(rows_read, tuple(discarded))


# ============================================================
# Elenco
# ============================================================

def _rank(member: SquadMember) -> tuple[int, str]:
    return (-member.player.overall, member.player.name)


def _unique_names(members: Sequence[SquadMember]) -> list[SquadMember]:
    """Garante nomes únicos (sufixo numérico em duplicatas)."""
    seen: set[str] = set()
    result: list[SquadMember] = []
    for member in members:
        name = member.player.name
        if name in seen:
            n = 2
            while f"{name} ({n})" in seen:
                n += 1
            name = f"{name} ({n})"
            member = replace(member, player=replace(member.player, name=name))
        seen.add(name)
        result.append(member)
    return result


def build_squad(members: Sequence[SquadMember], config: TournamentConfig) -> tuple[SquadMember, ...]:
    """Os melhores goleiros e jogadores de linha por overall (desempate por nome)."""
    goalkeepers = sorted((m for m in members if m.is_goalkeeper), key=_rank)
    outfield = sorted((m for m in members if not m.is_goalkeeper), key=_rank)
    chosen = (
        goalkeepers[: config.squad_goalkeepers]
        + outfield[: config.squad_size - config.squad_goalkeepers]
    )
    return tuple(_unique_names(chosen))


# ============================================================
# Escalação padrão
# ============================================================

def build_default_lineup(
    nation: str, squad: Sequence[SquadMember], formation: Sequence[str]
) -> tuple[Player, ...]:
    """
    Escalação determinística: slots preenchidos por setor (GK, DEF, MID, FW);
    em cada slot, o melhor não utilizado com a mesma posição canônica; na
    falta, o melhor do mesmo setor, recriado com a posição do slot. O goleiro
    nunca é improvisado. Devolve os jogadores na ordem dos slots.
    """
    slots = list(formation)
    canon = [canonical_position(s) for s in slots]
    order = sorted(range(len(slots)), key=lambda i: SECTOR_ORDER[POSITION_SECTORS[canon[i]]])
    ranked = sorted(squad, key=_rank)

    used: set[int] = set()
    chosen: dict[int, Player] = {}

    for i in order:
        slot, slot_canon = slots[i], canon[i]
        sector = POSITION_SECTORS[slot_canon]

        if slot_canon == "GK":
            pick = next(
                (k for k, m in enumerate(ranked) if k not in used and m.is_goalkeeper), None
            )
            if pick is None:
                raise SetupError(f"{nation}: não há goleiro disponível para a escalação.")
            used.add(pick)
            chosen[i] = ranked[pick].player
            continue

        candidates = [(k, m) for k, m in enumerate(ranked) if k not in used and not m.is_goalkeeper]
        exact = next(((k, m) for k, m in candidates if slot_canon in m.canonical_positions), None)
        if exact is not None:
            k, member = exact
            pos = next(p for p in member.positions if canonical_position(p) == slot_canon)
        else:
            same_sector = next(((k, m) for k, m in candidates if sector in m.sectors), None)
            if same_sector is None:
                raise SetupError(
                    f"{nation}: não há jogador disponível do setor {sector} "
                    f"para o slot {slot}."
                )
            k, member = same_sector
            pos = slot
        used.add(k)
        chosen[i] = member.player if member.player.pos == pos else replace(member.player, pos=pos)

    return tuple(chosen[i] for i in range(len(slots)))


def build_national_team(
    name: str, members: Sequence[SquadMember], config: TournamentConfig
) -> NationalTeam:
    """Monta elenco, escalação padrão e atributos de uma seleção."""
    if not members:
        raise SetupError(f"{name}: nenhum jogador válido para montar o elenco.")
    squad = build_squad(members, config)
    lineup = build_default_lineup(name, squad, config.formation)
    try:
        attributes = calculate_team_attributes(lineup, config.formation)
    except ValueError as exc:
        raise SetupError(f"{name}: escalação inválida: {exc}") from exc
    return NationalTeam(name, squad, config.formation, lineup, attributes)


def load_national_teams(
    config: TournamentConfig,
) -> tuple[dict[str, NationalTeam], DatasetReport]:
    """Lê o dataset e monta as 16 seleções (na ordem de `config.nations`)."""
    members, report = read_players_csv(config.dataset_path, config.nations)
    teams = {nation: build_national_team(nation, members[nation], config) for nation in config.nations}
    return teams, report


# ============================================================
# Seleções sintéticas
# ============================================================

def uniform_player(name: str, pos: str, rating: float) -> Player:
    """Player com todos os atributos iguais a `rating`."""
    return Player(name=name, pos=pos, **{f.name: rating for f in _NUMERIC_FIELDS})


def synthetic_team(name: str, rating: float, config: TournamentConfig | None = None) -> NationalTeam:
    """Seleção sem dataset: elenco completo com todos os atributos iguais a `rating`."""
    config = config or TournamentConfig()
    outfield_slots = [s for s in config.formation if canonical_position(s) != "GK"]
    n_outfield = config.squad_size - config.squad_goalkeepers
    positions = ["GK"] * config.squad_goalkeepers + [
        outfield_slots[i % len(outfield_slots)] for i in range(n_outfield)
    ]
    members = [
        SquadMember(uniform_player(f"{name} {i:02d}", pos, rating), (pos,))
        for i, pos in enumerate(positions)
    ]
    return build_national_team(name, members, config)


def synthetic_teams(
    config: TournamentConfig | None = None, ratings: Sequence[float] | None = None
) -> tuple[NationalTeam, ...]:
    """16 seleções sintéticas (padrão: ratings 60, 62, ..., 90)."""
    config = config or TournamentConfig()
    if ratings is None:
        ratings = [60 + 2 * i for i in range(N_TEAMS)]
    if len(ratings) != len(config.nations):
        raise ValueError(f"São necessários {len(config.nations)} ratings; recebido: {len(ratings)}")
    return tuple(synthetic_team(n, r, config) for n, r in zip(config.nations, ratings))


# ============================================================
# Potes e sorteio
# ============================================================

def draw_groups(teams: Sequence[NationalTeam], seed: int) -> DrawResult:
    """
    Ordena por força (desempate por nome), divide em 4 potes de 4 e sorteia
    os grupos A-D: cada grupo recebe um time de cada pote. A posição no
    grupo é o número do pote. O pote p usa Random(derive_seed(seed, "draw", p)).
    """
    if len(teams) != N_TEAMS:
        raise ValueError(f"O sorteio exige {N_TEAMS} seleções; recebido: {len(teams)}")
    if len({t.name for t in teams}) != N_TEAMS:
        raise ValueError("Os nomes das seleções devem ser únicos.")

    ranked = sorted(teams, key=lambda t: (-t.strength, t.name))
    pots = tuple(
        tuple(ranked[p * TEAMS_PER_GROUP:(p + 1) * TEAMS_PER_GROUP]) for p in range(N_POTS)
    )

    members: list[list[NationalTeam]] = [[] for _ in GROUP_NAMES]
    for pot_number, pot in enumerate(pots, start=1):
        order = list(pot)
        random.Random(derive_seed(seed, "draw", pot_number)).shuffle(order)
        for group_index, team in enumerate(order):
            members[group_index].append(team)

    groups = tuple(Group(name, tuple(ts)) for name, ts in zip(GROUP_NAMES, members))
    return DrawResult(pots, groups)


def setup_tournament(
    config: TournamentConfig, teams: Sequence[NationalTeam] | None = None
) -> TournamentSetup:
    """
    Prepara o torneio: carrega as seleções do dataset (ou usa `teams`, p. ex.
    sintéticas) e sorteia os grupos com `config.seed`.
    """
    report: DatasetReport | None = None
    if teams is None:
        loaded, report = load_national_teams(config)
        ordered = tuple(loaded[n] for n in config.nations)
    else:
        ordered = tuple(teams)
    return TournamentSetup(config, ordered, draw_groups(ordered, config.seed), report)
