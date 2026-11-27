from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from api.domain.models import User
from api.errors import ConflictError, UnauthorizedError
from api.repositories.base import DuplicateEmailError, LoginRepository


class LoginService:
    """Accounts: registration and password checks. Only argon2 hashes are stored."""

    def __init__(self, login: LoginRepository):
        self._login = login
        self._hasher = PasswordHasher()

    def exists(self, email: str) -> bool:
        return self._login.exists(email)

    def reg_user(self, email: str, password: str, session_id: str) -> User:
        try:
            return self._login.reg_user(
                email=email,
                password=self._hasher.hash(password),
                session_id=session_id,
            )
        except DuplicateEmailError:
            raise ConflictError("USER_ALREADY_EXISTS", "An account with this email already exists.") from None

    def auth(self, email: str, password: str) -> User:
        """The account, if the password matches.

        An unknown email and a wrong password get the same answer, so the API does not
        reveal which emails have accounts.
        """
        user = self._login.find_by_email(email)
        try:
            if user is None:
                raise VerifyMismatchError
            self._hasher.verify(user.password, password)
        except (VerifyMismatchError, InvalidHashError):
            raise UnauthorizedError("INVALID_CREDENTIALS", "Wrong email or password.") from None
        return user
