"""In-memory repositories: everything lives in dicts and is lost on restart.

Sessions, tournaments and matches are copied on the way in and out, so these
behave like a real database: a change that is never saved is lost.
"""

import uuid
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from collections.abc import Iterable
from copy import deepcopy

from api.domain.models import MOCK_CATALOG_VERSION, Match, Player, Position, Session, Squad, Tournament, User
from api.repositories.base import (
    CatalogRepository,
    PlayerRepository,
    Repositories,
    SessionRepository,
    LoginRepository,
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


class InMemoryCatalogRepository(CatalogRepository):
    def version(self) -> str:
        return MOCK_CATALOG_VERSION


class InMemorySessionRepository(SessionRepository):
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def add(self, session: Session) -> None:
        self._sessions[session.id] = deepcopy(session)

    def get(self, session_id: str) -> Session | None:
        return deepcopy(self._sessions.get(session_id))

    def save(self, session: Session) -> None:
        self._sessions[session.id] = deepcopy(session)

class InMemoryLoginRepository(LoginRepository):
    def __init__(self, users: Iterable[User] = ()):
        self._users_by_email: dict[str, User] = {}
        self._hasher = PasswordHasher()
        for user in users:
            self._users_by_email[user.email.strip().lower()] = deepcopy(user)

    def get(self, email: str) -> User | None:
        user = self._users_by_email.get(email.strip().lower())
        return deepcopy(user) if user is not None else None
    
    def exists(self, email: str) -> bool:
        return email.strip().lower() in self._users_by_email

    def find_by_email(self, email: str) -> User | None:
        user = self._users_by_email.get(email.strip().lower())
        return deepcopy(user) if user is not None else None

    def reg_user(self, email: str, password: str, session_id: str) -> User:
        normalized_email = email.strip().lower()
        user = User(
            id=str(uuid.uuid4()),
            sessionId=session_id,
            email=normalized_email,
            password=password,
        )
        self._users_by_email[normalized_email] = deepcopy(user)
        return deepcopy(user)

    def auth(self, email: str, password: str) -> User | None:
        user = self._users_by_email.get(email.strip().lower())
        if user is None:
            return None
        try:
            self._hasher.verify(user.password, password)
        except VerifyMismatchError:
            return None
        return deepcopy(user)

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
        login=InMemoryLoginRepository(),
        tournaments=InMemoryTournamentRepository(),
        catalog=InMemoryCatalogRepository(),
    )
