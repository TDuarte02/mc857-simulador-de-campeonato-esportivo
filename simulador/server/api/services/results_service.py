from api.domain.models import (
    GROUP_ROUNDS,
    LAST_ROUND,
    History,
    Match,
    Placement,
    RoundResults,
    Session,
    Stage,
    round_stage,
)
from api.domain.rules import group_standings, podium, qualified_squads
from api.errors import ConflictError
from api.repositories.base import TournamentRepository
from api.services.session_service import SessionService


class ResultsService:
    def __init__(self, sessions: SessionService, tournaments: TournamentRepository):
        self._sessions = sessions
        self._tournaments = tournaments

    def round_results(self, session_id: str) -> RoundResults:
        """Every result of the round that was just played."""
        session = self._sessions.get(session_id)
        if session.round == 0:
            raise ConflictError("NO_ROUND_PLAYED", "No round has been played yet.")
        tournament = self._tournaments.get(session_id)
        matches = self._matches(session_id)
        results = RoundResults(
            round=session.round,
            stage=round_stage(session.round),
            matches=[match for match in matches if match.round == session.round],
        )
        if session.round <= GROUP_ROUNDS:
            results.groups = group_standings(tournament.groups, matches)
            if session.round == GROUP_ROUNDS:
                results.qualified = qualified_squads(tournament.groups, matches)
        elif session.round < LAST_ROUND:
            results.advanced = [match.winner for match in results.matches]
        else:
            results.podium = podium(matches)
        return results

    def history(self, session_id: str) -> History:
        """Everything that happened in the session so far; complete once the cup is over."""
        session = self._sessions.get(session_id)
        tournament = self._tournaments.get(session_id)
        matches = self._matches(session_id)
        return History(
            session_id=session.id,
            phase=session.phase,
            user_squad=session.squad_id,
            placement=self._placement(session, matches),
            podium=podium(matches),
            groups=group_standings(tournament.groups, matches) if tournament else {},
            matches=matches,
        )

    def _matches(self, session_id: str) -> list[Match]:
        return sorted(self._tournaments.list_matches(session_id), key=lambda m: (m.round, m.id))

    def _placement(self, session: Session, matches: list[Match]) -> Placement | None:
        """Where the user's squad finished, or None while it is still in the cup."""
        user = session.squad_id
        last = next((m for m in reversed(matches) if m.played and m.involves(user)), None)
        if last is None:
            return None
        won = last.winner == user
        if last.stage is Stage.FINAL:
            return Placement.CHAMPION if won else Placement.RUNNER_UP
        if last.stage is Stage.THIRD_PLACE:
            return Placement.THIRD_PLACE if won else Placement.FOURTH_PLACE
        if last.stage is Stage.QUARTER_FINAL and not won:
            return Placement.QUARTER_FINALS
        if last.stage is Stage.GROUP and session.round >= GROUP_ROUNDS and session.user_eliminated:
            return Placement.GROUP_STAGE
        return None
