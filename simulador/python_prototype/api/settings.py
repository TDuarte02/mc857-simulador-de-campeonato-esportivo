import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    dataset_path: str = "players_data.csv"
    game_ttl_seconds: float = 3600.0
    max_games: int = 1000
    cors_origins: tuple[str, ...] = ("*",)

    @classmethod
    def from_env(cls) -> "Settings":
        d = cls()
        origins = os.environ.get("COPA_CORS_ORIGINS")
        return cls(
            dataset_path=os.environ.get("COPA_DATASET_PATH", d.dataset_path),
            game_ttl_seconds=float(os.environ.get("COPA_GAME_TTL_SECONDS", d.game_ttl_seconds)),
            max_games=int(os.environ.get("COPA_MAX_GAMES", d.max_games)),
            cors_origins=tuple(o.strip() for o in origins.split(",")) if origins else d.cors_origins,
        )
