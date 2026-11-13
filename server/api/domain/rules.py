"""Pure tournament rules: no storage, no HTTP, no randomness."""

from collections.abc import Iterable, Sequence

from api.config import Settings
from api.domain.models import (
    QUALIFIED_PER_GROUP,
    CardType,
    Match,
    MatchResult,
    Player,
    PlayerStatus,
    Podium,
    Position,
    Stage,
    Standing,
    UnavailableReason,
)

# Shape of the XI the backend picks for squads the user does not control.
OPPONENT_LINEUP = {Position.GK: 1, Position.DEF: 4, Position.MID: 4, Position.FW: 2}


def round_robin(teams: Sequence[str]) -> list[list[tuple[str, str]]]:
    """Every team meets every other once (circle method); needs an even number of teams."""
    rotation = list(teams)
    rounds = []
    for _ in range(len(rotation) - 1):
        half = len(rotation) // 2
        rounds.append([(rotation[i], rotation[-1 - i]) for i in range(half)])
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return rounds


def compute_standings(squad_ids: Iterable[str], matches: Iterable[Match]) -> list[Standing]:
    """Table for one group, counting only matches already played.

    Tie-breakers follow the app's standingComparator (GroupLogic.kt): points, goal
    difference, goals scored, fewer reds, fewer yellows.
    """
    table = {squad_id: Standing(squad_id) for squad_id in squad_ids}
    for match in matches:
        result = match.result
        if not match.played or result is None:
            continue
        sides = (
            (match.home, result.home_goals, result.away_goals),
            (match.away, result.away_goals, result.home_goals),
        )
        for squad_id, scored, conceded in sides:
            row = table[squad_id]
            row.played += 1
            row.goals_for += scored
            row.goals_against += conceded
            if scored > conceded:
                row.won += 1
                row.points += 3
            elif scored == conceded:
                row.drawn += 1
                row.points += 1
            else:
                row.lost += 1
        for card in result.cards:
            row = table[card.squad_id]
            if card.type is CardType.RED:
                row.red_cards += 1
            else:
                row.yellow_cards += 1
    return sorted(
        table.values(),
        key=lambda row: (
            -row.points,
            -row.goal_difference,
            -row.goals_for,
            row.red_cards,
            row.yellow_cards,
            row.squad_id,
        ),
    )


def group_standings(groups: dict[str, list[str]], matches: Iterable[Match]) -> dict[str, list[Standing]]:
    matches = list(matches)
    return {
        name: compute_standings(teams, [m for m in matches if m.group == name])
        for name, teams in groups.items()
    }


def qualified_squads(groups: dict[str, list[str]], matches: Iterable[Match]) -> list[str]:
    tables = group_standings(groups, matches)
    return [row.squad_id for table in tables.values() for row in table[:QUALIFIED_PER_GROUP]]


def podium(matches: Iterable[Match]) -> Podium | None:
    deciders = {m.stage: m for m in matches if m.played}
    final, third = deciders.get(Stage.FINAL), deciders.get(Stage.THIRD_PLACE)
    if final is None or third is None:
        return None
    return Podium(final.winner, final.loser, third.winner, third.loser)


def best_lineup(players: Iterable[Player]) -> list[Player]:
    """Strongest XI of a squad by overall, in OPPONENT_LINEUP's shape."""
    ranked = sorted(players, key=lambda p: -p.overall)
    lineup = []
    for position, count in OPPONENT_LINEUP.items():
        lineup += [p for p in ranked if p.position is position][:count]
    return lineup


def apply_match_events(
    statuses: dict[int, PlayerStatus],
    result: MatchResult,
    squad_id: str,
    settings: Settings,
) -> None:
    """Updates a squad's availability after it played a match.

    Players who sat this match out have served one game of their ban or recovery;
    then the new cards and injuries are applied.
    """
    for status in statuses.values():
        if status.suspended_matches:
            status.suspended_matches -= 1
            if status.suspended_matches == 0:
                status.suspension_reason = None
        if status.injured_matches:
            status.injured_matches -= 1

    for card in result.cards:
        status = statuses.get(card.player_id)
        if card.squad_id != squad_id or status is None:
            continue
        if card.type is CardType.RED:
            status.suspended_matches = settings.red_card_ban
            status.suspension_reason = UnavailableReason.SUSPENDED_RED
            continue
        status.yellow_cards += 1
        if status.yellow_cards >= settings.yellow_limit:
            status.yellow_cards = 0
            if status.suspended_matches == 0:  # a red in the same match already bans them
                status.suspended_matches = settings.yellow_ban
                status.suspension_reason = UnavailableReason.SUSPENDED_YELLOWS

    for injury in result.injuries:
        status = statuses.get(injury.player_id)
        if injury.squad_id == squad_id and status is not None:
            status.injured_matches = injury.matches_out
