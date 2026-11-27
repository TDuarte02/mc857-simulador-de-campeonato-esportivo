import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from api.domain.models import Mode, Session
from api.errors import ConflictError, NotFoundError
from api.repositories.base import CatalogRepository, SessionRepository


class SessionService:
    def __init__(self, sessions: SessionRepository, catalog: CatalogRepository, new_seed: Callable[[], int]):
        self._sessions = sessions
        self._catalog = catalog
        self._new_seed = new_seed

    def create(self, mode: Mode = Mode.FULL) -> Session:
        session = Session(
            id=str(uuid.uuid4()),
            created_at=datetime.now(UTC),
            mode=mode,
            catalog_version=self._catalog.version(),
            seed=self._new_seed(),
        )
        self._sessions.add(session)
        return session

    def get(self, session_id: str) -> Session:
        """The session, as long as it was created on the catalogue in use (its players' ids mean nothing on another)."""
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError("SESSION_NOT_FOUND", f"Session '{session_id}' does not exist.")
        if session.catalog_version != self._catalog.version():
            raise ConflictError(
                "CATALOG_CHANGED",
                "The catalogue was re-seeded after this session was created; start a new session.",
            )
        return session

    def save(self, session: Session) -> None:
        self._sessions.save(session)
