from api.domain.models import Match, Player, Stage, Tournament
from api.domain.rules import best_lineup
from api.repositories.base import PlayerRepository
from api.simulation.base import MatchContext, MatchSimulator, TeamSheet


class MatchRunner:
    """Turns a stored match into a request for the model and keeps the result on it."""

    def __init__(self, players: PlayerRepository, simulator: MatchSimulator):
        self._players = players
        self._simulator = simulator

    def run_quick(self, tournament: Tournament, match: Match) -> None:
        """A match the user is not in: both sides field their best XI."""
        match.result = self._simulator.simulate_quick(self._context(tournament, match, {}))

    def run_full(
        self,
        tournament: Tournament,
        match: Match,
        squad_id: str,
        lineup: list[Player],
        formation: str | None,
    ) -> None:
        """The user's match: their chosen XI against the opponent's stored squad."""
        sheet = TeamSheet(squad_id, lineup, formation)
        match.result = self._simulator.simulate_match(self._context(tournament, match, {squad_id: sheet}))

    def _context(self, tournament: Tournament, match: Match, sheets: dict[str, TeamSheet]) -> MatchContext:
        def sheet(squad_id: str) -> TeamSheet:
            if squad_id in sheets:
                return sheets[squad_id]
            squad = self._players.get_many(tournament.squads[squad_id])
            return TeamSheet(squad_id, best_lineup(squad))

        return MatchContext(
            home=sheet(match.home),
            away=sheet(match.away),
            stage=match.stage,
            needs_winner=match.stage is not Stage.GROUP,
        )
