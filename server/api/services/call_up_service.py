from collections import Counter

from api.config import Settings
from api.domain.models import CallUp, Phase, Player, PlayerStatus
from api.errors import ConflictError, ValidationError
from api.services.session_service import SessionService
from api.services.squad_service import SquadService


class CallUpService:
    def __init__(self, sessions: SessionService, squads: SquadService, settings: Settings):
        self._sessions = sessions
        self._squads = squads
        self._settings = settings

    def call_up(self, session_id: str, squad_id: str, player_ids: list[int]) -> CallUp:
        session = self._sessions.get(session_id)
        if session.phase not in (Phase.CREATED, Phase.CALLED_UP):
            raise ConflictError("DRAW_ALREADY_DONE", "The call-up cannot change after the draw.")
        squad = self._squads.get_squad(squad_id)
        players = self._validate(squad.id, player_ids)

        session.squad_id = squad.id
        session.call_up = [player.id for player in players]
        session.player_status = {player.id: PlayerStatus() for player in players}
        session.phase = Phase.CALLED_UP
        self._sessions.save(session)
        return CallUp(session.id, squad.id, players)

    def _validate(self, squad_id: str, player_ids: list[int]) -> list[Player]:
        size = self._settings.squad_size
        if len(player_ids) != size:
            raise ValidationError(
                "INVALID_CALL_UP", f"A call-up needs exactly {size} players, got {len(player_ids)}."
            )
        if len(set(player_ids)) != size:
            raise ValidationError("INVALID_CALL_UP", "A player cannot be called up twice.")

        pool = {player.id: player for player in self._squads.list_players(squad_id)}
        unknown = [player_id for player_id in player_ids if player_id not in pool]
        if unknown:
            raise ValidationError(
                "INVALID_CALL_UP", f"Players {unknown} do not belong to squad '{squad_id}'."
            )

        players = [pool[player_id] for player_id in player_ids]
        counts = Counter(player.position for player in players)
        for position, quota in self._settings.squad_quotas.items():
            if counts[position] != quota:
                raise ValidationError(
                    "INVALID_CALL_UP",
                    f"A call-up needs exactly {quota} {position} players, got {counts[position]}.",
                )
        return players
