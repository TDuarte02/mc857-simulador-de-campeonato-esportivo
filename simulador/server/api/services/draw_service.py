import random
from dataclasses import dataclass

from copa_engine.rules import GROUP_ROUNDS, KNOCKOUT_BRACKET, derive_seed, draw_groups

from api.domain.models import (
    GROUP_ROUNDS as GROUP_ROUND_COUNT,
    QUARTER_FINAL_ROUND,
    Draw,
    Match,
    Phase,
    PlayoffsDraw,
    Session,
    Stage,
    Tournament,
)
from api.domain.rules import group_standings, qualified_squads
from api.errors import ConflictError
from api.repositories.base import TournamentRepository
from api.services.match_runner import MatchRunner
from api.services.session_service import SessionService
from api.services.squad_service import SquadService
from api.simulation.engine import team_strength


@dataclass(frozen=True)
class _Entrant:
    """What copa_engine.rules.draw_groups needs of a squad."""

    name: str
    strength: float


class DrawService:
    """The group draw and the bracket, both the engine's (decision D2).

    Pots are seeded by the strength of each squad's default XI; the groups are drawn
    with the session seed; the quarter-finals follow group positions (QF1 = 1A x 2B,
    QF2 = 1B x 2A, QF3 = 1D x 2C, QF4 = 1C x 2D).
    """

    def __init__(
        self,
        sessions: SessionService,
        squads: SquadService,
        tournaments: TournamentRepository,
        runner: MatchRunner,
    ):
        self._sessions = sessions
        self._squads = squads
        self._tournaments = tournaments
        self._runner = runner

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
        """Reveals the quarter-finals on the first call; later calls return the same bracket."""
        session = self._sessions.get(session_id)
        tournament = self._tournaments.get(session_id)
        if tournament is None or session.round < GROUP_ROUND_COUNT:
            raise ConflictError(
                "GROUP_STAGE_NOT_FINISHED", "The playoffs are drawn once the group stage is over."
            )
        quarter_finals = self.ensure_playoffs(session, tournament)
        qualified = qualified_squads(tournament.groups, self._played_group_matches(session.id), session.seed)
        return PlayoffsDraw(qualified=qualified, quarter_finals=quarter_finals)

    def ensure_playoffs(self, session: Session, tournament: Tournament) -> list[Match]:
        existing = self._tournaments.list_matches(session.id, QUARTER_FINAL_ROUND)
        if existing:
            return existing

        tables = group_standings(tournament.groups, self._played_group_matches(session.id), session.seed)

        def team(source) -> str:
            return tables[source.ref][source.position - 1].squad_id

        quarter_finals = [
            Match(
                id=match_id,
                session_id=session.id,
                stage=Stage.QUARTER_FINAL,
                round=QUARTER_FINAL_ROUND,
                home=team(home),
                away=team(away),
            )
            for match_id, (home, away) in KNOCKOUT_BRACKET.items()
            if home.kind == "group"
        ]
        self._tournaments.save_matches(quarter_finals)
        session.phase = Phase.QUARTER_FINALS
        self._sessions.save(session)
        return quarter_finals

    def _played_group_matches(self, session_id: str) -> list[Match]:
        return [m for m in self._tournaments.list_matches(session_id) if m.stage is Stage.GROUP and m.played]

    def _create_tournament(self, session: Session) -> Tournament:
        participants = [squad.id for squad in self._squads.list_squads()]  # the 16 (the seed checks)
        # Each rival brings one of its presets; which one, and the shuffle of `random`,
        # come from one generator per squad, derived from the session seed.
        squads = {
            squad_id: list(session.call_up)
            if squad_id == session.squad_id
            else [
                player.id
                for player in self._squads.random_preset(
                    squad_id, random.Random(derive_seed(session.seed, "preset", squad_id))
                ).players
            ]
            for squad_id in participants
        }
        entrants = [
            _Entrant(squad_id, team_strength(squad_id, self._squads.get_players(squads[squad_id])))
            for squad_id in participants
        ]
        drawn = draw_groups(entrants, session.seed)
        groups = {group.name: [team.name for team in group.teams] for group in drawn.groups}
        tournament = Tournament(session.id, groups, squads)

        matches = [
            Match(
                id=f"G-{group}-R{round_no}-{n}",
                session_id=session.id,
                stage=Stage.GROUP,
                round=round_no,
                home=teams[a - 1],
                away=teams[b - 1],
                group=group,
            )
            for group, teams in groups.items()
            for round_no, pairs in enumerate(GROUP_ROUNDS, 1)
            for n, (a, b) in enumerate(pairs, 1)
        ]
        # Group matches without the user are simulated up front and revealed round by round.
        for match in matches:
            if not match.involves(session.squad_id):
                self._runner.run_quick(tournament, match, session.seed)

        self._tournaments.save(tournament)
        self._tournaments.save_matches(matches)
        session.phase = Phase.GROUP_STAGE
        self._sessions.save(session)
        return tournament
