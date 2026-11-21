import uuid
from datetime import UTC, datetime

from api.domain.models import Session
from api.errors import NotFoundError
from api.repositories.base import SessionRepository


class SessionService:
    def __init__(self, sessions: SessionRepository):
        self._sessions = sessions

    def create(self) -> Session:
        session = Session(id=str(uuid.uuid4()), created_at=datetime.now(UTC))
        self._sessions.add(session)
        return session

    def get(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError("SESSION_NOT_FOUND", f"Session '{session_id}' does not exist.")
        return session

    def save(self, session: Session) -> None:
        self._sessions.save(session)
