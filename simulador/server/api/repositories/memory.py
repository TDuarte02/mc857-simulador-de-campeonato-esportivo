"""In-memory repositories: everything lives in dicts and is lost on restart.

Sessions, tournaments and matches are copied on the way in and out, so these
behave like a real database: a change that is never saved is lost.
"""

from collections.abc import Iterable
from copy import deepcopy

from api.domain.models import Match, Player, Position, Session, Squad, Tournament
from api.repositories.base import (
    PlayerRepository,
    Repositories,
    SessionRepository,
    SquadRepository,
    TournamentRepository,
)
from api.repositories.mock_data import build_players, build_squads


class InMemorySquadRepository(SquadRepository):
    def __init__(self, squads: Iterable[Squad]):
        self._squads = {squad.id: squad for squad in squads}

    def list_all(self) -> list[Squad]:
        return list(self._squads.values())

    def get(self, squad_id: str) -> Squad | None:
        return self._squads.get(squad_id)


class InMemoryPlayerRepository(PlayerRepository):
    def __init__(self, players: Iterable[Player]):
        self._players = {player.id: player for player in players}

    def list_by_squad(self, squad_id: str, position: Position | None = None) -> list[Player]:
        return [
            player
            for player in self._players.values()
            if player.squad_id == squad_id and (position is None or player.position is position)
        ]

    def get_many(self, player_ids: Iterable[int]) -> list[Player]:
        return [self._players[i] for i in player_ids if i in self._players]


class InMemorySessionRepository(SessionRepository):
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def add(self, session: Session) -> None:
        self._sessions[session.id] = deepcopy(session)

    def get(self, session_id: str) -> Session | None:
        return deepcopy(self._sessions.get(session_id))

    def save(self, session: Session) -> None:
        self._sessions[session.id] = deepcopy(session)


class InMemoryTournamentRepository(TournamentRepository):
    def __init__(self):
        self._tournaments: dict[str, Tournament] = {}
        self._matches: dict[str, dict[str, Match]] = {}

    def get(self, session_id: str) -> Tournament | None:
        return deepcopy(self._tournaments.get(session_id))

    def save(self, tournament: Tournament) -> None:
        self._tournaments[tournament.session_id] = deepcopy(tournament)

    def list_matches(self, session_id: str, round_no: int | None = None) -> list[Match]:
        matches = self._matches.get(session_id, {}).values()
        return [deepcopy(match) for match in matches if round_no is None or match.round == round_no]

    def save_matches(self, matches: Iterable[Match]) -> None:
        for match in matches:
            self._matches.setdefault(match.session_id, {})[match.id] = deepcopy(match)


def create_memory_repositories() -> Repositories:
    return Repositories(
        squads=InMemorySquadRepository(build_squads()),
        players=InMemoryPlayerRepository(build_players()),
        sessions=InMemorySessionRepository(),
        tournaments=InMemoryTournamentRepository(),
    )
