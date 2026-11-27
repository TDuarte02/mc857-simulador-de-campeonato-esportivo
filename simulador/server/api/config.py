import os
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from api.domain.models import Position


def _default_quotas() -> dict[Position, int]:
    # Same split the mobile app enforces (SquadLogic.kt: SQUAD_TOTALS).
    return {Position.GK: 3, Position.DEF: 8, Position.MID: 8, Position.FW: 7}


@dataclass(frozen=True)
class Settings:
    squad_quotas: dict[Position, int] = field(default_factory=_default_quotas)
    lineup_size: int = 11

    # Matches a player misses after a red card / after reaching the yellow limit.
    red_card_ban: int = 1
    yellow_limit: int = 2
    yellow_ban: int = 1

    # Which implementations container.py wires in.
    simulator: str = "mock"
    repository: str = "memory"

    # Used when repository == "mongo". The URI can carry a password, so it is kept
    # out of repr() (and so out of logs and tracebacks).
    mongo_uri: str = field(default="mongodb://localhost:27017", repr=False)
    mongo_db: str = "copa"
    # Amazon DocumentDB: TLS with Amazon's CA bundle, no retryable writes (not
    # supported), replica set "rs0". Unset for a plain MongoDB.
    mongo_tls_ca_file: str | None = None
    mongo_retry_writes: bool = True
    mongo_replica_set: str | None = None
    # Loads the generated mock catalogue into an empty database (tests, development).
    # Off by default: production serves the catalogue loaded by `python -m api.seed`.
    seed_mock_catalog: bool = False
    # When set, every request must carry it in the X-Origin-Verify header. In AWS,
    # API Gateway adds it after checking the API key, so calling the instance
    # directly (bypassing the key) gets 403. Kept out of repr().
    origin_secret: str | None = field(default=None, repr=False)

    @property
    def squad_size(self) -> int:
        return sum(self.squad_quotas.values())

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            simulator=os.environ.get("SIMULATOR", "mock"),
            repository=os.environ.get("REPOSITORY", "memory"),
            mongo_uri=_mongo_uri_from_env(),
            mongo_db=os.environ.get("MONGO_DB", cls.mongo_db),
            mongo_tls_ca_file=os.environ.get("MONGO_TLS_CA_FILE") or None,
            mongo_retry_writes=not _is_false(os.environ.get("MONGO_RETRY_WRITES", "")),
            mongo_replica_set=os.environ.get("MONGO_REPLICA_SET") or None,
            seed_mock_catalog=os.environ.get("SEED_MOCK_CATALOG", "").lower() in ("1", "true", "yes"),
            origin_secret=os.environ.get("ORIGIN_SECRET") or None,
        )


def _is_false(value: str) -> bool:
    return value.strip().lower() in ("0", "false", "no")


def _mongo_uri_from_env() -> str:
    """MONGO_URI as given, or one built from MONGO_HOST/PORT/USERNAME/PASSWORD.

    In AWS the credentials come from Secrets Manager as separate variables; they
    are URL-escaped here so any character in the generated password is safe.
    """
    host = os.environ.get("MONGO_HOST")
    if not host:
        return os.environ.get("MONGO_URI", Settings.__dataclass_fields__["mongo_uri"].default)
    port = os.environ.get("MONGO_PORT", "27017")
    user, password = os.environ.get("MONGO_USERNAME", ""), os.environ.get("MONGO_PASSWORD", "")
    credentials = f"{quote_plus(user)}:{quote_plus(password)}@" if user else ""
    return f"mongodb://{credentials}{host}:{port}/"
