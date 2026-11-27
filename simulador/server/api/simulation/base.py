"""Contract between the backend and the simulation model.

A model only has to implement MatchSimulator and be registered in api/container.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from api.domain.models import MatchResult, Player, Stage


@dataclass(frozen=True)
class TeamSheet:
    squad_id: str
    players: list[Player]  # the XI on the pitch, in slot order
    formation: str | None = None  # e.g. "4-4-2"
    # The formation's slot each player fills (e.g. "GK", "FB", "ST"), aligned with `players`.
    slots: list[str] | None = None


@dataclass(frozen=True)
class MatchContext:
    home: TeamSheet
    away: TeamSheet
    stage: Stage
    # Knockout matches cannot end level: on a draw the result must carry penalties.
    needs_winner: bool
    # The session's seed and the match id: a deterministic model derives its draws from both.
    seed: int = 0
    match_id: str = ""


class MatchSimulator(ABC):
    @abstractmethod
    def simulate_match(self, context: MatchContext) -> MatchResult:
        """Full simulation, used for the matches the user plays."""

    @abstractmethod
    def simulate_quick(self, context: MatchContext) -> MatchResult:
        """Used for every match the user is not in (may be weaker and cheaper)."""
