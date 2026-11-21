import uuid
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from api.domain.models import User
from api.errors import NotFoundError
from api.repositories.base import LoginRepository

class LoginService:
    def __init__(self, login: LoginRepository):
        self._login = login
        self._hasher = PasswordHasher()

    def exists(self, email: str) -> bool:
        return self._login.get(email) is not None

    def find_by_email(self, email: str) -> User:
        user = self._login.get(email)
        if not user:
            raise NotFoundError("EMAIL_NOT_FOUND", f"Email '{email}' does not exist.")
        return user

    def reg_user(self, email: str, password: str, session_id: str):
        password_hash = self._hasher.hash(password)
        return self._login.reg_user(
            email=email,
            password=password_hash,
            session_id=session_id,
        )

    def auth(self, email: str, password: str) -> User:
        user = self.find_by_email(email)
        try:
            self._hasher.verify(user.password, password)
        except VerifyMismatchError as exc:
            raise ValueError("INVALID_CREDENTIALS") from exc
        return user
