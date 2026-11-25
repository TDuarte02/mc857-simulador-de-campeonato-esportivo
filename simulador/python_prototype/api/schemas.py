from typing import Any, Literal

from pydantic import BaseModel


class NationOut(BaseModel):
    id: str
    name: str
    display_name: str
    flag: str
    confederation: str


class PlayerOut(BaseModel):
    name: str
    positions: list[str]
    sectors: list[str]
    overall: int
    is_goalkeeper: bool
    attributes: dict[str, float]


class SquadRules(BaseModel):
    size: int
    goalkeepers: int
    outfield: int
    min_defenders: int
    min_midfielders: int
    min_forwards: int


class PoolOut(BaseModel):
    nation: str
    rules: SquadRules
    players: list[PlayerOut]


class CreateGameIn(BaseModel):
    user_team: str
    squad: list[str]
    seed: int | None = None


class PickIn(BaseModel):
    player: str
    slot: str


class StartMatchIn(BaseModel):
    picks: list[PickIn] | None = None


class LineupIn(BaseModel):
    picks: list[PickIn]
    formation: list[str] | None = None


class PlayIn(BaseModel):
    until: Literal["halftime", "end"]


class PenaltiesSummary(BaseModel):
    first_team: str | None
    goals_a: int
    goals_b: int
    winner: str | None
    sudden_death: bool


class MatchSummary(BaseModel):
    id: str
    phase: str
    group: str | None
    round: int | None
    slot_a: str | None
    slot_b: str | None
    team_a: str | None
    team_b: str | None
    status: str
    goals_a: int | None
    goals_b: int | None
    penalties: PenaltiesSummary | None
    winner: str | None


class StandingRow(BaseModel):
    team: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int


class GroupOut(BaseModel):
    name: str
    teams: list[str]
    standings: list[StandingRow]
    is_final: bool
    matches: list[MatchSummary]


class LineupSlot(BaseModel):
    player: str
    slot: str


class ActiveMatch(BaseModel):
    match_id: str
    team_a: str
    team_b: str
    user_side: str
    phase: str
    minute: int
    score: dict[str, int]
    can_change_lineup: bool
    cycles_played: int
    lineup: list[LineupSlot]
    formation: list[str]


class GameState(BaseModel):
    game_id: str
    seed: int
    user_team: str | None
    phase: str
    is_finished: bool
    user_eliminated: bool
    groups: list[GroupOut]
    knockout: list[MatchSummary]
    next_match: MatchSummary | None
    pending_user_match: MatchSummary | None
    active_match: ActiveMatch | None
    suspended: list[str]


class CreateGameOut(BaseModel):
    game_id: str
    seed: int
    state: GameState


class AdvanceOut(BaseModel):
    pending_match: MatchSummary | None
    phase: str
    user_eliminated: bool
    is_finished: bool
    suspended: list[str]


class PossessionOut(BaseModel):
    index: int
    attacking_team: str
    attempts: int
    scorer: str | None


class CycleOut(BaseModel):
    cycle: int
    start_minute: int
    end_minute: int
    goals: int
    scorers: list[str]
    possessions: list[PossessionOut]


class TimelineEntry(BaseModel):
    minute: int
    type: str
    team: str | None = None
    player: str | None = None
    score: dict[str, int] | None = None
    data: dict[str, Any] = {}


class TeamStats(BaseModel):
    goals: int
    possession: float
    attacks: int
    attempts: int
    possession_lost: int
    fouls: int
    yellow_cards: int
    red_cards: int


class Kick(BaseModel):
    team: str
    player: str
    scored: bool


class PenaltiesView(BaseModel):
    first_team: str
    goals_a: int
    goals_b: int
    winner: str
    sudden_death: bool
    kicks: list[Kick]


class MatchView(BaseModel):
    match_id: str
    team_a: str
    team_b: str
    score: dict[str, int]
    penalties: PenaltiesView | None
    stats: dict[str, TeamStats]
    timeline: list[TimelineEntry]


class PlayOut(BaseModel):
    match_id: str
    phase: str
    minute: int
    score: dict[str, int]
    finished: bool
    cycles: list[CycleOut]
    view: MatchView | None
    suspended: list[str]
