import os
from dataclasses import dataclass, field

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

    @property
    def squad_size(self) -> int:
        return sum(self.squad_quotas.values())

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            simulator=os.environ.get("SIMULATOR", "mock"),
            repository=os.environ.get("REPOSITORY", "memory"),
        )
