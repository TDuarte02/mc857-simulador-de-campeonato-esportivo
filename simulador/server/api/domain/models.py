from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

# Tournament shape: 16 teams, 4 groups of 4, top 2 advance to an 8-team bracket.
GROUP_NAMES = ("A", "B", "C", "D")
GROUP_SIZE = 4
TEAM_COUNT = len(GROUP_NAMES) * GROUP_SIZE
QUALIFIED_PER_GROUP = 2

# Rounds are numbered across the whole cup: 1-3 are the group stage. A fast cup has
# no groups and starts at the quarter-finals, still round 4.
FAST_TEAM_COUNT = 8
GROUP_ROUNDS = GROUP_SIZE - 1
QUARTER_FINAL_ROUND = 4
SEMI_FINAL_ROUND = 5
FINALS_ROUND = 6  # final and third-place match are played together
LAST_ROUND = FINALS_ROUND

# Winners of each pair of quarter-finals meet in a semi-final.
SEMI_FINAL_PATHS = (("QF1", "QF2"), ("QF3", "QF4"))


class Mode(StrEnum):
    """How long the cup is."""

    FULL = "FULL"  # 16 squads: group stage, then the 8-team knockout
    FAST = "FAST"  # 8 squads straight into the quarter-finals (third-place match included)


def first_round(mode: "Mode") -> int:
    """The first round a session in this mode actually plays."""
    return QUARTER_FINAL_ROUND if mode is Mode.FAST else 1


class Position(StrEnum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FW = "FW"


class Federation(StrEnum):
    CONMEBOL = "CONMEBOL"
    CONCACAF = "CONCACAF"


class Stage(StrEnum):
    GROUP = "GROUP"
    QUARTER_FINAL = "QUARTER_FINAL"
    SEMI_FINAL = "SEMI_FINAL"
    THIRD_PLACE = "THIRD_PLACE"
    FINAL = "FINAL"


class Phase(StrEnum):
    """Where a session is in its lifecycle."""

    CREATED = "CREATED"
    CALLED_UP = "CALLED_UP"
    GROUP_STAGE = "GROUP_STAGE"
    PLAYOFFS_PENDING = "PLAYOFFS_PENDING"
    QUARTER_FINALS = "QUARTER_FINALS"
    SEMI_FINALS = "SEMI_FINALS"
    FINALS = "FINALS"
    FINISHED = "FINISHED"


class CardType(StrEnum):
    YELLOW = "YELLOW"
    RED = "RED"


class UnavailableReason(StrEnum):
    SUSPENDED_RED = "SUSPENDED_RED"
    SUSPENDED_YELLOWS = "SUSPENDED_YELLOWS"
    INJURED = "INJURED"


class NextStep(StrEnum):
    """What the client should do after a simulated match."""

    NEXT_ROUND = "NEXT_ROUND"
    AWAITING_PLAYOFFS_DRAW = "AWAITING_PLAYOFFS_DRAW"
    THIRD_PLACE_MATCH = "THIRD_PLACE_MATCH"
    ELIMINATED = "ELIMINATED"
    FINISHED = "FINISHED"


class Placement(StrEnum):
    CHAMPION = "CHAMPION"
    RUNNER_UP = "RUNNER_UP"
    THIRD_PLACE = "THIRD_PLACE"
    FOURTH_PLACE = "FOURTH_PLACE"
    QUARTER_FINALS = "QUARTER_FINALS"
    GROUP_STAGE = "GROUP_STAGE"


def round_stage(round_no: int) -> Stage:
    if round_no <= GROUP_ROUNDS:
        return Stage.GROUP
    return {
        QUARTER_FINAL_ROUND: Stage.QUARTER_FINAL,
        SEMI_FINAL_ROUND: Stage.SEMI_FINAL,
        FINALS_ROUND: Stage.FINAL,
    }[round_no]


@dataclass(frozen=True)
class Squad:
    id: str
    name: str
    flag: str
    federation: Federation


# Version of the generated mock catalogue; a seeded catalogue's comes from its file.
MOCK_CATALOG_VERSION = "mock"


@dataclass(frozen=True)
class Player:
    id: int
    squad_id: str
    name: str
    age: int
    position: Position  # sector of the primary position
    overall: int
    is_current: bool = False  # called up in 2024
    is_legend: bool = False
    positions: tuple[str, ...] = ()  # dataset codes, primary first (e.g. "CAM", "ST")
    # The match engine's 18 numeric fields (engine_data.ENGINE_ATTRIBUTES).
    attributes: dict[str, float] = field(default_factory=dict, hash=False)
    # Shared by the 2024 and legend versions of a person; defaults to the player's id.
    person_key: str | None = None

    @property
    def person(self) -> str:
        return self.person_key or str(self.id)


@dataclass
class Goal:
    minute: int
    player_id: int
    squad_id: str


@dataclass
class Card:
    minute: int
    player_id: int
    squad_id: str
    type: CardType
    # A red for a second yellow in the same match; the report keeps both cards.
    second_yellow: bool = False


@dataclass
class Injury:
    minute: int
    player_id: int
    squad_id: str
    matches_out: int


@dataclass
class MatchResult:
    home_goals: int
    away_goals: int
    goals: list[Goal] = field(default_factory=list)
    cards: list[Card] = field(default_factory=list)
    injuries: list[Injury] = field(default_factory=list)
    home_penalties: int | None = None
    away_penalties: int | None = None


@dataclass
class LineupSlot:
    """Who played where in the user's XI: the formation's slot (e.g. "FB", "ST") and the player."""

    slot: str
    player_id: int


@dataclass
class Match:
    id: str
    session_id: str
    stage: Stage
    round: int
    home: str
    away: str
    group: str | None = None
    result: MatchResult | None = None
    # False while a pre-simulated result is still hidden from the user.
    played: bool = False
    # The user's XI, slot by slot; only on the user's matches.
    lineup: list[LineupSlot] | None = None

    def involves(self, squad_id: str | None) -> bool:
        return squad_id in (self.home, self.away)

    def opponent_of(self, squad_id: str) -> str:
        return self.away if squad_id == self.home else self.home

    @property
    def winner(self) -> str | None:
        result = self.result
        if result is None:
            return None
        if result.home_goals != result.away_goals:
            return self.home if result.home_goals > result.away_goals else self.away
        if result.home_penalties is not None and result.away_penalties is not None:
            return self.home if result.home_penalties > result.away_penalties else self.away
        return None

    @property
    def loser(self) -> str | None:
        winner = self.winner
        return None if winner is None else self.opponent_of(winner)


@dataclass
class PlayerStatus:
    """Discipline and fitness of one called-up player."""

    yellow_cards: int = 0  # accumulated towards the next suspension
    suspended_matches: int = 0
    suspension_reason: UnavailableReason | None = None
    injured_matches: int = 0

    @property
    def available(self) -> bool:
        return self.suspended_matches == 0 and self.injured_matches == 0

    @property
    def reason(self) -> UnavailableReason | None:
        return UnavailableReason.INJURED if self.injured_matches else self.suspension_reason

    @property
    def matches_remaining(self) -> int:
        return max(self.suspended_matches, self.injured_matches)


@dataclass
class Session:
    id: str
    created_at: datetime
    mode: Mode = Mode.FULL
    phase: Phase = Phase.CREATED
    squad_id: str | None = None
    call_up: list[int] = field(default_factory=list)
    player_status: dict[int, PlayerStatus] = field(default_factory=dict)
    round: int = 0  # rounds completed so far (a fast cup starts at GROUP_ROUNDS)
    user_eliminated: bool = False
    # The catalogue the session was created on; it cannot continue on another one.
    catalog_version: str = MOCK_CATALOG_VERSION
    # Every random choice of the session derives from it (63 bits, fits a BSON int64).
    # Never sent to the client.
    seed: int = 0


@dataclass
class Tournament:
    session_id: str
    groups: dict[str, list[str]]  # empty in a fast cup
    # The 26 players each participating squad brought to the cup.
    squads: dict[str, list[int]]


@dataclass
class Standing:
    squad_id: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    yellow_cards: int = 0
    red_cards: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


@dataclass
class Podium:
    champion: str
    runner_up: str
    third: str
    fourth: str


# --- What the services hand back to the controllers ---------------------------


@dataclass
class Preset:
    id: str
    name: str
    description: str
    players: list[Player]


@dataclass
class CallUp:
    session_id: str
    squad_id: str
    players: list[Player]


@dataclass
class Draw:
    mode: Mode
    user_squad: str
    groups: dict[str, list[str]]
    squads: dict[str, list[Player]]
    matches: list[Match]  # the group fixtures, or a fast cup's quarter-finals


@dataclass
class UnavailablePlayer:
    player: Player
    reason: UnavailableReason | None
    matches_remaining: int


@dataclass
class Availability:
    available: list[Player]
    unavailable: list[UnavailablePlayer]
    yellow_cards: dict[int, int]


@dataclass
class NextInfo:
    step: NextStep
    match: Match | None = None


@dataclass
class SimulationOutcome:
    match: Match
    next: NextInfo
    user_squad: str


@dataclass
class RoundResults:
    round: int
    stage: Stage
    matches: list[Match]
    groups: dict[str, list[Standing]] | None = None
    qualified: list[str] | None = None
    advanced: list[str] | None = None
    podium: Podium | None = None


@dataclass
class PlayoffsDraw:
    qualified: list[str]
    quarter_finals: list[Match]


@dataclass
class History:
    session_id: str
    phase: Phase
    user_squad: str | None
    placement: Placement | None
    podium: Podium | None
    groups: dict[str, list[Standing]]
    matches: list[Match]
