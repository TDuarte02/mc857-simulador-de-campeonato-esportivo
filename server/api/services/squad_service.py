import random
from collections.abc import Iterable

from api.config import Settings
from api.domain.models import Player, Position, Preset, Squad
from api.errors import NotFoundError
from api.repositories.base import PlayerRepository, SquadRepository


class SquadService:
    def __init__(
        self,
        squads: SquadRepository,
        players: PlayerRepository,
        settings: Settings,
        rng: random.Random,
    ):
        self._squads = squads
        self._players = players
        self._settings = settings
        self._rng = rng

    def list_squads(self) -> list[Squad]:
        return self._squads.list_all()

    def get_squad(self, squad_id: str) -> Squad:
        squad = self._squads.get(squad_id)
        if squad is None:
            raise NotFoundError("SQUAD_NOT_FOUND", f"Squad '{squad_id}' does not exist.")
        return squad

    def list_players(self, squad_id: str, position: Position | None = None) -> list[Player]:
        self.get_squad(squad_id)
        return self._players.list_by_squad(squad_id, position)

    def get_players(self, player_ids: Iterable[int]) -> list[Player]:
        return self._players.get_many(player_ids)

    def presets(self, squad_id: str) -> list[Preset]:
        """Ready-made call-ups, mirroring the app's presets (SquadLogic.kt)."""
        pool = self.list_players(squad_id)
        size = self._settings.squad_size
        by_overall = sorted(pool, key=lambda p: -p.overall)
        current_first = sorted(pool, key=lambda p: (not p.is_current, -p.overall))
        shuffled = self._rng.sample(pool, len(pool))
        return [
            Preset(
                "current",
                "Elenco atual",
                f"Os {size} convocados mais recentes",
                self._fill_quotas(current_first),
            ),
            Preset(
                "legends",
                "Seleção das lendas",
                f"Os {size} maiores da história",
                self._fill_quotas(by_overall),
            ),
            Preset("random", "Aleatório", f"{size} jogadores sorteados", self._fill_quotas(shuffled)),
        ]

    def random_preset(self, squad_id: str) -> Preset:
        return self._rng.choice(self.presets(squad_id))

    def _fill_quotas(self, ranked: list[Player]) -> list[Player]:
        """Takes players in the given order until every position's quota is full."""
        squad: list[Player] = []
        for position, quota in self._settings.squad_quotas.items():
            squad += [player for player in ranked if player.position is position][:quota]
        return squad
