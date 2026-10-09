"""Wires repositories, the simulator and the services together.

This is the only place that knows which implementations are in use. To go from
the mocks to the real thing, add the new class to REPOSITORIES or SIMULATORS and
select it with the REPOSITORY / SIMULATOR environment variables.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass

from api.config import Settings
from api.repositories.base import (
    PlayerRepository,
    SessionRepository,
    SquadRepository,
    TournamentRepository,
)
from api.repositories.memory import (
    InMemoryPlayerRepository,
    InMemorySessionRepository,
    InMemorySquadRepository,
    InMemoryTournamentRepository,
)
from api.repositories.mock_data import build_players, build_squads
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
class Repositories:
    squads: SquadRepository
    players: PlayerRepository
    sessions: SessionRepository
    tournaments: TournamentRepository


@dataclass(frozen=True)
class Container:
    settings: Settings
    sessions: SessionService
    squads: SquadService
    call_ups: CallUpService
    draws: DrawService
    matches: MatchService
    results: ResultsService


def _memory_repositories() -> Repositories:
    return Repositories(
        squads=InMemorySquadRepository(build_squads()),
        players=InMemoryPlayerRepository(build_players()),
        sessions=InMemorySessionRepository(),
        tournaments=InMemoryTournamentRepository(),
    )


REPOSITORIES: dict[str, Callable[[], Repositories]] = {
    "memory": _memory_repositories,
}

SIMULATORS: dict[str, Callable[[random.Random], MatchSimulator]] = {
    "mock": RandomMatchSimulator,
}


def build_container(
    settings: Settings | None = None,
    *,
    simulator: MatchSimulator | None = None,
    rng: random.Random | None = None,
) -> Container:
    """Builds the service graph. `simulator` and `rng` can be injected, e.g. by tests."""
    settings = settings or Settings()
    rng = rng or random.Random()
    repositories = _pick(REPOSITORIES, settings.repository, "REPOSITORY")()
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
