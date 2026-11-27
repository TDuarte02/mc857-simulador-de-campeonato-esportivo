"""What the match engine needs from a player: position codes, their sectors and 18 attributes.

All of it comes from the engine (copa_engine.collective_attributes), so the catalogue
and the simulator can never disagree on what a position code means.
"""

from dataclasses import fields

from copa_engine.collective_attributes import POSITION_ALIASES, POSITION_SECTORS, Player as EnginePlayer
from copa_engine.collective_attributes import canonical_position as _engine_canonical
from copa_engine.common import ATTRIBUTE_MAX

from api.domain.models import Position

__all__ = [
    "ATTRIBUTE_MAX",
    "ENGINE_ATTRIBUTES",
    "LINE_ATTRIBUTES",
    "POSITION_ALIASES",
    "POSITION_SECTORS",
    "canonical_position",
    "sector_of",
]

# The six outfield attributes, which goalkeepers may lack (the engine reads them as 0).
LINE_ATTRIBUTES = ("pace", "shooting", "passing", "dribbling", "defending", "physic")

# The engine Player's numeric fields, in its order. Integers except the six above.
ENGINE_ATTRIBUTES = tuple(f.name for f in fields(EnginePlayer) if f.name not in ("name", "pos"))


def canonical_position(code: str) -> str:
    """The engine's canonical position for a dataset code; KeyError if unknown."""
    try:
        return _engine_canonical(code)
    except ValueError:
        raise KeyError(code) from None


def sector_of(code: str) -> Position:
    return Position(POSITION_SECTORS[canonical_position(code)])
