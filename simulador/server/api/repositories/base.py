"""Storage contracts the services depend on.

A storage backend implements these four classes and is registered in
api/container.py; nothing above this layer changes.

Implementations must behave like a database: what `get`/`list_*` return is a
copy, so a change only exists once it is passed to `save`/`save_matches`.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

from api.domain.models import Match, Player, Position, Session, Squad, Tournament


class SquadRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Squad]: ...

    @abstractmethod
    def get(self, squad_id: str) -> Squad | None: ...


class PlayerRepository(ABC):
    @abstractmethod
    def list_by_squad(self, squad_id: str, position: Position | None = None) -> list[Player]: ...

    @abstractmethod
    def get_many(self, player_ids: Iterable[int]) -> list[Player]:
        """Players in the order their ids were given; unknown ids are skipped."""


class SessionRepository(ABC):
    @abstractmethod
    def add(self, session: Session) -> None: ...

    @abstractmethod
    def get(self, session_id: str) -> Session | None: ...

    @abstractmethod
    def save(self, session: Session) -> None: ...


class TournamentRepository(ABC):
    """A session's draw (groups and every squad's players) and all of its matches."""

    @abstractmethod
    def get(self, session_id: str) -> Tournament | None: ...

    @abstractmethod
    def save(self, tournament: Tournament) -> None: ...

    @abstractmethod
    def list_matches(self, session_id: str, round_no: int | None = None) -> list[Match]: ...

    @abstractmethod
    def save_matches(self, matches: Iterable[Match]) -> None:
        """Inserts new matches and updates the ones already stored."""


@dataclass(frozen=True)
class Repositories:
    """One complete storage backend."""

    squads: SquadRepository
    players: PlayerRepository
    sessions: SessionRepository
    tournaments: TournamentRepository
