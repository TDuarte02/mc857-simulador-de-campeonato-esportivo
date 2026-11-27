"""Tournament rules on the domain models: no storage, no HTTP.

The order of a group table is the engine's (copa_engine.rules.compute_standings:
points, goal difference, goals scored, head-to-head, then a draw seeded by the
session). Only matches already played count.
"""

from collections.abc import Iterable

from copa_engine.rules import GroupGame
from copa_engine.rules import compute_standings as engine_standings

from api.config import Settings
from api.domain.models import (
    QUALIFIED_PER_GROUP,
    CardType,
    Match,
    MatchResult,
    PlayerStatus,
    Podium,
    Stage,
    Standing,
    UnavailableReason,
)


def compute_standings(group: str, squad_ids: list[str], matches: Iterable[Match], seed: int) -> list[Standing]:
    """Table for one group. The engine decides the order; cards are counted here (the API shows them)."""
    played = [m for m in matches if m.played and m.result is not None]
    games = [GroupGame(m.home, m.away, m.result.home_goals, m.result.away_goals) for m in played]
    order = engine_standings(group, squad_ids, games, seed)

    table = {squad_id: Standing(squad_id) for squad_id in squad_ids}
    for row in order:
        standing = table[row.team]
        standing.played, standing.won, standing.drawn, standing.lost = row.played, row.wins, row.draws, row.losses
        standing.goals_for, standing.goals_against, standing.points = row.goals_for, row.goals_against, row.points
    for match in played:
        for card in match.result.cards:
            if card.squad_id in table:
                if card.type is CardType.RED:
                    table[card.squad_id].red_cards += 1
                else:
                    table[card.squad_id].yellow_cards += 1
    return [table[row.team] for row in order]


def group_standings(groups: dict[str, list[str]], matches: Iterable[Match], seed: int) -> dict[str, list[Standing]]:
    matches = list(matches)
    return {
        name: compute_standings(name, teams, [m for m in matches if m.group == name], seed)
        for name, teams in groups.items()
    }


def qualified_squads(groups: dict[str, list[str]], matches: Iterable[Match], seed: int) -> list[str]:
    """The top two of each group, group by group: A1, A2, B1, B2, ..."""
    tables = group_standings(groups, matches, seed)
    return [row.squad_id for table in tables.values() for row in table[:QUALIFIED_PER_GROUP]]


def podium(matches: Iterable[Match]) -> Podium | None:
    deciders = {m.stage: m for m in matches if m.played}
    final, third = deciders.get(Stage.FINAL), deciders.get(Stage.THIRD_PLACE)
    if final is None or third is None:
        return None
    return Podium(final.winner, final.loser, third.winner, third.loser)


def apply_match_events(
    statuses: dict[int, PlayerStatus],
    result: MatchResult,
    squad_id: str,
    settings: Settings,
) -> None:
    """Updates a squad's availability after it played a match.

    Players who sat this match out have served one game of their ban or recovery;
    then the new cards and injuries are applied. A player sent off for a second
    yellow has both cards in the report, but that yellow does not count towards
    accumulation: the red already suspends them.
    """
    for status in statuses.values():
        if status.suspended_matches:
            status.suspended_matches -= 1
            if status.suspended_matches == 0:
                status.suspension_reason = None
        if status.injured_matches:
            status.injured_matches -= 1

    sent_off_for_yellows = {
        card.player_id for card in result.cards if card.type is CardType.RED and card.second_yellow
    }
    for card in result.cards:
        status = statuses.get(card.player_id)
        if card.squad_id != squad_id or status is None:
            continue
        if card.type is CardType.RED:
            status.suspended_matches = settings.red_card_ban
            status.suspension_reason = UnavailableReason.SUSPENDED_RED
            continue
        if card.player_id in sent_off_for_yellows:
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
