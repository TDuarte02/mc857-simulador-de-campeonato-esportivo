"""Contract between the backend and the simulation model.

The real model only has to implement MatchSimulator and be registered in
api/container.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from api.domain.models import MatchResult, Player, Stage


@dataclass(frozen=True)
class TeamSheet:
    squad_id: str
    players: list[Player]  # the XI on the pitch
    formation: str | None = None


@dataclass(frozen=True)
class MatchContext:
    home: TeamSheet
    away: TeamSheet
    stage: Stage
    # Knockout matches cannot end level: on a draw the result must carry penalties.
    needs_winner: bool


class MatchSimulator(ABC):
    @abstractmethod
    def simulate_match(self, context: MatchContext) -> MatchResult:
        """Full simulation, used for the matches the user plays."""

    @abstractmethod
    def simulate_quick(self, context: MatchContext) -> MatchResult:
        """Weaker, cheaper simulation, used for every match the user is not in."""
