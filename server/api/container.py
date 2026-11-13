"""Wires repositories, the simulator and the services together.

This is the only place that knows which implementations are in use. Storage is
picked with the REPOSITORY environment variable (`memory` or `mongo`) and the
model with SIMULATOR (`mock`); a new implementation is one more registry entry.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass

from pymongo import MongoClient

from api.config import Settings
from api.repositories.base import Repositories
from api.repositories.memory import create_memory_repositories
from api.repositories.mongo import create_mongo_repositories
from api.services.call_up_service import CallUpService
from api.services.draw_service import DrawService
from api.services.match_runner import MatchRunner
from api.services.match_service import MatchService
from api.services.results_service import ResultsService
from api.services.session_service import SessionService
from api.services.squad_service import SquadService
from api.simulation.base import MatchSimulator
from api.simulation.mock import RandomMatchSimulator


@dataclass(frozen=True)
class Container:
    settings: Settings
    sessions: SessionService
    squads: SquadService
    call_ups: CallUpService
    draws: DrawService
    matches: MatchService
    results: ResultsService


def _mongo_repositories(settings: Settings) -> Repositories:
    client = MongoClient(settings.mongo_uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    return create_mongo_repositories(client[settings.mongo_db])


REPOSITORIES: dict[str, Callable[[Settings], Repositories]] = {
    "memory": lambda settings: create_memory_repositories(),
    "mongo": _mongo_repositories,
}

SIMULATORS: dict[str, Callable[[random.Random], MatchSimulator]] = {
    "mock": RandomMatchSimulator,
}


def build_container(
    settings: Settings | None = None,
    *,
    repositories: Repositories | None = None,
    simulator: MatchSimulator | None = None,
    rng: random.Random | None = None,
) -> Container:
    """Builds the service graph. `repositories`, `simulator` and `rng` can be injected, e.g. by tests."""
    settings = settings or Settings()
    rng = rng or random.Random()
    repositories = repositories or _pick(REPOSITORIES, settings.repository, "REPOSITORY")(settings)
    simulator = simulator or _pick(SIMULATORS, settings.simulator, "SIMULATOR")(rng)

    sessions = SessionService(repositories.sessions)
    squads = SquadService(repositories.squads, repositories.players, settings, rng)
    runner = MatchRunner(repositories.players, simulator)
    draws = DrawService(sessions, squads, repositories.tournaments, runner, rng)
    return Container(
        settings=settings,
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
