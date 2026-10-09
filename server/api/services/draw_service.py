import random

from api.domain.models import (
    GROUP_NAMES,
    GROUP_ROUNDS,
    GROUP_SIZE,
    QUARTER_FINAL_ROUND,
    TEAM_COUNT,
    Draw,
    Match,
    Phase,
    PlayoffsDraw,
    Session,
    Stage,
    Tournament,
)
from api.domain.rules import qualified_squads, round_robin
from api.errors import ConflictError
from api.repositories.base import TournamentRepository
from api.services.match_runner import MatchRunner
from api.services.session_service import SessionService
from api.services.squad_service import SquadService


class DrawService:
    def __init__(
        self,
        sessions: SessionService,
        squads: SquadService,
        tournaments: TournamentRepository,
        runner: MatchRunner,
        rng: random.Random,
    ):
        self._sessions = sessions
        self._squads = squads
        self._tournaments = tournaments
        self._runner = runner
        self._rng = rng

    def draw(self, session_id: str) -> Draw:
        """Draws the groups on the first call; later calls return the same draw."""
        session = self._sessions.get(session_id)
        if session.phase is Phase.CREATED:
            raise ConflictError("CALL_UP_REQUIRED", "Send the call-up before drawing the groups.")
        tournament = self._tournaments.get(session_id) or self._create_tournament(session)
        return Draw(
            user_squad=session.squad_id,
            groups=tournament.groups,
            squads={
                squad_id: self._squads.get_players(player_ids)
                for squad_id, player_ids in tournament.squads.items()
            },
            matches=[m for m in self._tournaments.list_matches(session_id) if m.stage is Stage.GROUP],
        )

    def playoffs_draw(self, session_id: str) -> PlayoffsDraw:
        """Draws the quarter-finals on the first call; later calls return the same bracket."""
        session = self._sessions.get(session_id)
        tournament = self._tournaments.get(session_id)
        if tournament is None or session.round < GROUP_ROUNDS:
            raise ConflictError(
                "GROUP_STAGE_NOT_FINISHED", "The playoffs are drawn once the group stage is over."
            )
        quarter_finals = self.ensure_playoffs(session, tournament)
        qualified = qualified_squads(tournament.groups, self._tournaments.list_matches(session_id))
        return PlayoffsDraw(qualified=qualified, quarter_finals=quarter_finals)

    def ensure_playoffs(self, session: Session, tournament: Tournament) -> list[Match]:
        existing = self._tournaments.list_matches(session.id, QUARTER_FINAL_ROUND)
        if existing:
            return existing

        qualified = qualified_squads(tournament.groups, self._tournaments.list_matches(session.id))
        self._rng.shuffle(qualified)
        quarter_finals = [
            Match(
                id=f"QF{n + 1}",
                session_id=session.id,
                stage=Stage.QUARTER_FINAL,
                round=QUARTER_FINAL_ROUND,
                home=qualified[2 * n],
                away=qualified[2 * n + 1],
            )
            for n in range(len(qualified) // 2)
        ]
        self._tournaments.save_matches(quarter_finals)
        session.phase = Phase.QUARTER_FINALS
        self._sessions.save(session)
        return quarter_finals

    def _create_tournament(self, session: Session) -> Tournament:
        rivals = [squad.id for squad in self._squads.list_squads() if squad.id != session.squad_id]
        participants = [session.squad_id, *self._rng.sample(rivals, TEAM_COUNT - 1)]
        self._rng.shuffle(participants)
        groups = {
            name: participants[i * GROUP_SIZE : (i + 1) * GROUP_SIZE]
            for i, name in enumerate(GROUP_NAMES)
        }
        # Rivals bring one of their preset squads; it is stored so later matches reuse it.
        squads = {
            squad_id: list(session.call_up)
            if squad_id == session.squad_id
            else [player.id for player in self._squads.random_preset(squad_id).players]
            for squad_id in participants
        }
        tournament = Tournament(session.id, groups, squads)

        matches = [
            Match(
                id=f"G-{group}-R{round_no}-{n}",
                session_id=session.id,
                stage=Stage.GROUP,
                round=round_no,
                home=home,
                away=away,
                group=group,
            )
            for group, teams in groups.items()
            for round_no, fixtures in enumerate(round_robin(teams), 1)
            for n, (home, away) in enumerate(fixtures, 1)
        ]
        # Group matches without the user are simulated up front and revealed round by round.
        for match in matches:
            if not match.involves(session.squad_id):
                self._runner.run_quick(tournament, match)

        self._tournaments.save(tournament)
        self._tournaments.save_matches(matches)
        session.phase = Phase.GROUP_STAGE
        self._sessions.save(session)
        return tournament
