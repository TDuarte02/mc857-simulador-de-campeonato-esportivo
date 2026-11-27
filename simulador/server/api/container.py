"""Wires repositories, the simulator and the services together.

This is the only place that knows which implementations are in use. Storage is
picked with the REPOSITORY environment variable (`memory` or `mongo`) and the
model with SIMULATOR (`engine` or `mock`); a new implementation is one more
registry entry.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass

from pymongo import MongoClient

from api.config import Settings
from api.repositories.base import CatalogRepository, Repositories
from api.repositories.memory import create_memory_repositories
from api.repositories.mongo import catalog_is_empty, create_mongo_repositories
from api.services.call_up_service import CallUpService
from api.services.draw_service import DrawService
from api.services.match_runner import MatchRunner
from api.services.match_service import MatchService
from api.services.results_service import ResultsService
from api.services.session_service import SessionService
from api.services.squad_service import SquadService
from api.simulation.base import MatchSimulator
from api.simulation.engine import EngineMatchSimulator
from api.simulation.mock import RandomMatchSimulator


# A session seed: 63 bits, so it fits a BSON int64.
SEED_BITS = 63


@dataclass(frozen=True)
class Meta:
    """What runs behind the API: the simulator's name and the catalogue in use."""

    simulator: str
    catalog: CatalogRepository

    @property
    def catalog_version(self) -> str:
        return self.catalog.version()


@dataclass(frozen=True)
class Container:
    settings: Settings
    meta: Meta
    sessions: SessionService
    squads: SquadService
    call_ups: CallUpService
    draws: DrawService
    matches: MatchService
    results: ResultsService


class EmptyCatalogError(RuntimeError):
    """The database has no squads or players, and the mock catalogue was not asked for."""


def open_mongo_client(settings: Settings) -> MongoClient:
    """A client for MongoDB, or for Amazon DocumentDB when its TLS/retry settings are set.

    Reads always go to the primary (pymongo's default): the services read back what
    they just wrote, so a lagging replica would return stale sessions.
    """
    options: dict = {"tz_aware": True, "serverSelectionTimeoutMS": 5000}
    if settings.mongo_tls_ca_file:
        options |= {"tls": True, "tlsCAFile": settings.mongo_tls_ca_file}
    if not settings.mongo_retry_writes:
        options["retryWrites"] = False
    if settings.mongo_replica_set:
        options["replicaSet"] = settings.mongo_replica_set
    return MongoClient(settings.mongo_uri, **options)


def _mongo_repositories(settings: Settings) -> Repositories:
    db = open_mongo_client(settings)[settings.mongo_db]
    repositories = create_mongo_repositories(db, seed_mock=settings.seed_mock_catalog)
    if catalog_is_empty(db):
        raise EmptyCatalogError(
            f"The catalogue in '{settings.mongo_db}' is empty. Load it with "
            "`python -m api.seed --file <players csv>` (docker compose runs the `seed` service "
            "first), or set SEED_MOCK_CATALOG=1 to serve generated mock data."
        )
    return repositories


REPOSITORIES: dict[str, Callable[[Settings], Repositories]] = {
    "memory": lambda settings: create_memory_repositories(),
    "mongo": _mongo_repositories,
}

SIMULATORS: dict[str, Callable[[random.Random], MatchSimulator]] = {
    # The engine draws everything from the session seed; it ignores the shared generator.
    "engine": lambda rng: EngineMatchSimulator(),
    "mock": RandomMatchSimulator,
}


def build_container(
    settings: Settings | None = None,
    *,
    repositories: Repositories | None = None,
    simulator: MatchSimulator | None = None,
    rng: random.Random | None = None,
    session_seed: Callable[[], int] | None = None,
) -> Container:
    """Builds the service graph.

    `repositories`, `simulator`, `rng` and `session_seed` (what seeds a new session)
    can be injected, e.g. by tests. By default a session seed comes from `rng`.
    """
    settings = settings or Settings()
    rng = rng or random.Random()
    repositories = repositories or _pick(REPOSITORIES, settings.repository, "REPOSITORY")(settings)
    simulator_name = settings.simulator if simulator is None else type(simulator).__name__
    simulator = simulator or _pick(SIMULATORS, settings.simulator, "SIMULATOR")(rng)
    session_seed = session_seed or (lambda: rng.getrandbits(SEED_BITS))

    sessions = SessionService(repositories.sessions, repositories.catalog, session_seed)
    squads = SquadService(repositories.squads, repositories.players, settings, rng)
    runner = MatchRunner(repositories.players, simulator)
    draws = DrawService(sessions, squads, repositories.tournaments, runner)
    return Container(
        settings=settings,
        meta=Meta(simulator_name, repositories.catalog),
        sessions=sessions,
        squads=squads,
        call_ups=CallUpService(sessions, squads, settings),
        draws=draws,
        matches=MatchService(sessions, squads, draws, repositories.tournaments, runner, settings),
        results=ResultsService(sessions, repositories.tournaments),
    )


def _pick(registry: dict, name: str, variable: str):
    if name not in registry:
        raise ValueError(f"Unknown {variable} '{name}'. Available: {', '.join(registry)}.")
    return registry[name]
