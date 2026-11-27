from api.domain.models import Match, Stage, Tournament
from api.repositories.base import PlayerRepository
from api.simulation.base import MatchContext, MatchSimulator, TeamSheet
from api.simulation.engine import default_sheet


class MatchRunner:
    """Turns a stored match into a request for the model and keeps the result on it."""

    def __init__(self, players: PlayerRepository, simulator: MatchSimulator):
        self._players = players
        self._simulator = simulator

    def run_quick(self, tournament: Tournament, match: Match, seed: int) -> None:
        """A match the user is not in: both sides field their default XI."""
        match.result = self._simulator.simulate_quick(self._context(tournament, match, seed, None))

    def run_full(self, tournament: Tournament, match: Match, seed: int, user: TeamSheet) -> None:
        """The user's match: their XI against the opponent's default XI, from its stored squad."""
        match.result = self._simulator.simulate_match(self._context(tournament, match, seed, user))

    def default_sheet(self, tournament: Tournament, squad_id: str) -> TeamSheet:
        return default_sheet(squad_id, self._players.get_many(tournament.squads[squad_id]))

    def _context(self, tournament: Tournament, match: Match, seed: int, user: TeamSheet | None) -> MatchContext:
        def sheet(squad_id: str) -> TeamSheet:
            if user is not None and squad_id == user.squad_id:
                return user
            return self.default_sheet(tournament, squad_id)

        return MatchContext(
            home=sheet(match.home),
            away=sheet(match.away),
            stage=match.stage,
            needs_winner=match.stage is not Stage.GROUP,
            seed=seed,
            match_id=match.id,
        )
