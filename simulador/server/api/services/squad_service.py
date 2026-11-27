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

    def presets(self, squad_id: str, rng: random.Random | None = None) -> list[Preset]:
        """Ready-made call-ups, mirroring the app's presets (SquadLogic.kt).

        `random` shuffles with `rng`: the session's own generator when an opponent's
        squad is built, the shared one otherwise.
        """
        rng = rng or self._rng
        pool = self.list_players(squad_id)
        size = self._settings.squad_size
        quotas = ", ".join(f"{quota} {position}" for position, quota in self._settings.squad_quotas.items())
        current_first = sorted(pool, key=lambda p: (not p.is_current, -p.overall, p.id))
        legends_first = sorted(pool, key=lambda p: (not p.is_legend, -p.overall, p.id))
        shuffled = rng.sample(pool, len(pool))
        return [
            Preset(
                "current",
                "Elenco atual",
                f"Os convocados de 2024, completados pelo overall até {quotas}; "
                "convocados além da cota de uma posição ficam de fora",
                self._fill_quotas(current_first),
            ),
            Preset(
                "legends",
                "Seleção das lendas",
                f"Os {size} maiores da história: lendas primeiro, completadas pelo overall",
                self._fill_quotas(legends_first),
            ),
            Preset("random", "Aleatório", f"{size} jogadores sorteados", self._fill_quotas(shuffled)),
        ]

    def random_preset(self, squad_id: str, rng: random.Random | None = None) -> Preset:
        """One of the presets, picked (and, if `random`, shuffled) with `rng`."""
        rng = rng or self._rng
        return rng.choice(self.presets(squad_id, rng))

    def _fill_quotas(self, ranked: list[Player]) -> list[Player]:
        """Takes players in the given order until every position's quota is full.

        A second version of a person (their 2024 self and their legend) is skipped.
        """
        squad: list[Player] = []
        people: set[str] = set()
        for position, quota in self._settings.squad_quotas.items():
            taken = 0
            for player in ranked:
                if taken == quota:
                    break
                if player.position is position and player.person not in people:
                    squad.append(player)
                    people.add(player.person)
                    taken += 1
        return squad
