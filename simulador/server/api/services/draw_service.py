import random
from dataclasses import dataclass

from copa_engine.rules import GROUP_ROUNDS, KNOCKOUT_BRACKET, derive_seed, draw_groups

from api.domain.models import (
    FAST_TEAM_COUNT,
    GROUP_ROUNDS as GROUP_ROUND_COUNT,
    QUARTER_FINAL_ROUND,
    Draw,
    Match,
    Mode,
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

    A fast cup skips the groups: the user and 7 rivals drawn with the session seed go
    straight into quarter-finals where each of the 4 strongest (same strength measure)
    meets one of the 4 weakest. From there on it is the same knockout.
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
        first_stage = Stage.QUARTER_FINAL if session.mode is Mode.FAST else Stage.GROUP
        return Draw(
            mode=session.mode,
            user_squad=session.squad_id,
            groups=tournament.groups,
            squads={
                squad_id: self._squads.get_players(player_ids)
                for squad_id, player_ids in tournament.squads.items()
            },
            matches=[m for m in self._tournaments.list_matches(session_id) if m.stage is first_stage],
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
        if session.mode is Mode.FAST:  # no groups: everyone in the cup is in the bracket
            qualified = [squad for match in quarter_finals for squad in (match.home, match.away)]
        else:
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
        if session.mode is Mode.FAST:
            return self._create_fast_tournament(session)
        participants = [squad.id for squad in self._squads.list_squads()]  # the 16 (the seed checks)
        squads = self._bring_squads(session, participants)
        drawn = draw_groups(self._entrants(squads), session.seed)
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

    def _create_fast_tournament(self, session: Session) -> Tournament:
        """8 squads, no groups, the quarter-finals drawn at once."""
        # Sorted so the field depends only on the seed, not on the catalogue's order.
        rivals = sorted(squad.id for squad in self._squads.list_squads() if squad.id != session.squad_id)
        field_rng = random.Random(derive_seed(session.seed, "fast-field"))
        participants = [session.squad_id, *field_rng.sample(rivals, FAST_TEAM_COUNT - 1)]
        squads = self._bring_squads(session, participants)

        # Strongest first (ties by name, like the engine's pots); each of the top half
        # meets one of the bottom half, paired at random.
        ranked = sorted(self._entrants(squads), key=lambda entrant: (-entrant.strength, entrant.name))
        half = FAST_TEAM_COUNT // 2
        seeded = [entrant.name for entrant in ranked[:half]]
        unseeded = [entrant.name for entrant in ranked[half:]]
        bracket_rng = random.Random(derive_seed(session.seed, "fast-bracket"))
        bracket_rng.shuffle(seeded)
        bracket_rng.shuffle(unseeded)
        quarter_finals = [
            Match(
                id=f"QF{n}",
                session_id=session.id,
                stage=Stage.QUARTER_FINAL,
                round=QUARTER_FINAL_ROUND,
                home=home,
                away=away,
            )
            for n, (home, away) in enumerate(zip(seeded, unseeded), 1)
        ]

        tournament = Tournament(session.id, groups={}, squads=squads)
        self._tournaments.save(tournament)
        self._tournaments.save_matches(quarter_finals)
        # The group rounds do not exist, so they count as completed: round numbers stay
        # those of a full cup (the quarter-finals are round 4).
        session.round = GROUP_ROUND_COUNT
        session.phase = Phase.QUARTER_FINALS
        self._sessions.save(session)
        return tournament

    def _bring_squads(self, session: Session, participants: list[str]) -> dict[str, list[int]]:
        """The user's call-up, and for each rival one of its presets.

        Which preset, and the shuffle of `random`, come from one generator per squad,
        derived from the session seed.
        """
        return {
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

    def _entrants(self, squads: dict[str, list[int]]) -> list[_Entrant]:
        return [
            _Entrant(squad_id, team_strength(squad_id, self._squads.get_players(player_ids)))
            for squad_id, player_ids in squads.items()
        ]
