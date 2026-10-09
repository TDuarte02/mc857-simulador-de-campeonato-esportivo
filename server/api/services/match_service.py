from api.config import Settings
from api.domain.models import (
    FINALS_ROUND,
    GROUP_ROUNDS,
    LAST_ROUND,
    QUARTER_FINAL_ROUND,
    SEMI_FINAL_PATHS,
    SEMI_FINAL_ROUND,
    Availability,
    Match,
    NextInfo,
    NextStep,
    Phase,
    Player,
    Position,
    Session,
    SimulationOutcome,
    Stage,
    Tournament,
    UnavailablePlayer,
)
from api.domain.rules import apply_match_events, qualified_squads
from api.errors import ConflictError, ValidationError
from api.repositories.base import TournamentRepository
from api.services.draw_service import DrawService
from api.services.match_runner import MatchRunner
from api.services.session_service import SessionService
from api.services.squad_service import SquadService


class MatchService:
    def __init__(
        self,
        sessions: SessionService,
        squads: SquadService,
        draws: DrawService,
        tournaments: TournamentRepository,
        runner: MatchRunner,
        settings: Settings,
    ):
        self._sessions = sessions
        self._squads = squads
        self._draws = draws
        self._tournaments = tournaments
        self._runner = runner
        self._settings = settings

    def available_players(self, session_id: str) -> Availability:
        session = self._sessions.get(session_id)
        if session.phase is Phase.CREATED:
            raise ConflictError("CALL_UP_REQUIRED", "This session has no call-up yet.")
        available, unavailable = [], []
        for player in self._squads.get_players(session.call_up):
            status = session.player_status[player.id]
            if status.available:
                available.append(player)
            else:
                unavailable.append(UnavailablePlayer(player, status.reason, status.matches_remaining))
        yellow_cards = {player_id: status.yellow_cards for player_id, status in session.player_status.items()}
        return Availability(available, unavailable, yellow_cards)

    def simulate(self, session_id: str, player_ids: list[int], formation: str | None = None) -> SimulationOutcome:
        """Plays the user's match of the current round and closes the round."""
        session = self._sessions.get(session_id)
        tournament = self._require_tournament(session)
        if session.phase is Phase.FINISHED:
            raise ConflictError("TOURNAMENT_FINISHED", "The cup is over.")
        if session.user_eliminated:
            raise ConflictError(
                "USER_ELIMINATED", "Your squad is out; use simulate-all to finish the cup."
            )
        if session.phase is Phase.PLAYOFFS_PENDING:
            raise ConflictError("PLAYOFFS_DRAW_REQUIRED", "Draw the playoffs before the next match.")

        lineup = self._validate_lineup(session, player_ids)
        round_no = session.round + 1
        match = self._user_match(session, round_no)
        self._runner.run_full(tournament, match, session.squad_id, lineup, formation)
        apply_match_events(session.player_status, match.result, session.squad_id, self._settings)
        self._complete_round(session, tournament, round_no)
        self._sessions.save(session)
        return SimulationOutcome(match, self._next(session), session.squad_id)

    def simulate_all(self, session_id: str) -> None:
        """Finishes the cup once the user is out. Calling it on a finished cup is a no-op."""
        session = self._sessions.get(session_id)
        tournament = self._require_tournament(session)
        if session.phase is Phase.FINISHED:
            return
        if not session.user_eliminated:
            raise ConflictError(
                "USER_STILL_PLAYING", "simulate-all is only available after your squad is eliminated."
            )
        if session.phase is Phase.PLAYOFFS_PENDING:
            self._draws.ensure_playoffs(session, tournament)
        while session.round < LAST_ROUND:
            self._complete_round(session, tournament, session.round + 1)
        self._sessions.save(session)

    def _require_tournament(self, session: Session) -> Tournament:
        tournament = self._tournaments.get(session.id)
        if tournament is None:
            raise ConflictError("DRAW_REQUIRED", "Draw the groups before simulating.")
        return tournament

    def _user_match(self, session: Session, round_no: int) -> Match:
        matches = self._tournaments.list_matches(session.id, round_no)
        return next(match for match in matches if match.involves(session.squad_id))

    def _validate_lineup(self, session: Session, player_ids: list[int]) -> list[Player]:
        size = self._settings.lineup_size
        if len(player_ids) != size or len(set(player_ids)) != size:
            raise ValidationError("INVALID_LINEUP", f"A lineup needs exactly {size} different players.")
        statuses = session.player_status
        not_called_up = [player_id for player_id in player_ids if player_id not in statuses]
        if not_called_up:
            raise ValidationError("INVALID_LINEUP", f"Players {not_called_up} are not in the call-up.")
        unavailable = [player_id for player_id in player_ids if not statuses[player_id].available]
        if unavailable:
            raise ValidationError(
                "PLAYER_UNAVAILABLE", f"Players {unavailable} are suspended or injured."
            )

        squad = {player.id: player for player in self._squads.get_players(session.call_up)}
        lineup = [squad[player_id] for player_id in player_ids]
        goalkeepers = sum(player.position is Position.GK for player in lineup)
        # A squad with every goalkeeper sidelined may still play, with an outfield XI.
        has_fit_goalkeeper = any(
            player.position is Position.GK and statuses[player.id].available for player in squad.values()
        )
        if goalkeepers != (1 if has_fit_goalkeeper else 0):
            raise ValidationError("INVALID_LINEUP", "A lineup needs exactly one goalkeeper.")
        return lineup

    def _complete_round(self, session: Session, tournament: Tournament, round_no: int) -> None:
        """Resolves what is left of a round, reveals it and sets up the next one."""
        matches = self._tournaments.list_matches(session.id, round_no)
        for match in matches:
            if match.result is None:
                self._runner.run_quick(tournament, match)
            match.played = True
        self._tournaments.save_matches(matches)
        session.round = round_no
        user = session.squad_id

        if round_no < GROUP_ROUNDS:
            return
        if round_no == GROUP_ROUNDS:
            qualified = qualified_squads(tournament.groups, self._tournaments.list_matches(session.id))
            session.user_eliminated = user not in qualified
            session.phase = Phase.PLAYOFFS_PENDING
        elif round_no == QUARTER_FINAL_ROUND:
            semi_finals = self._open_semi_finals(session, matches)
            session.user_eliminated = not any(match.involves(user) for match in semi_finals)
            session.phase = Phase.SEMI_FINALS
        elif round_no == SEMI_FINAL_ROUND:
            self._open_finals(session, matches)
            session.phase = Phase.FINALS
        else:
            session.phase = Phase.FINISHED

    def _open_semi_finals(self, session: Session, quarter_finals: list[Match]) -> list[Match]:
        by_id = {match.id: match for match in quarter_finals}
        semi_finals = [
            Match(
                id=f"SF{n}",
                session_id=session.id,
                stage=Stage.SEMI_FINAL,
                round=SEMI_FINAL_ROUND,
                home=by_id[first].winner,
                away=by_id[second].winner,
            )
            for n, (first, second) in enumerate(SEMI_FINAL_PATHS, 1)
        ]
        self._tournaments.save_matches(semi_finals)
        return semi_finals

    def _open_finals(self, session: Session, semi_finals: list[Match]) -> None:
        first, second = sorted(semi_finals, key=lambda match: match.id)
        self._tournaments.save_matches(
            [
                Match("THIRD", session.id, Stage.THIRD_PLACE, FINALS_ROUND, first.loser, second.loser),
                Match("FINAL", session.id, Stage.FINAL, FINALS_ROUND, first.winner, second.winner),
            ]
        )

    def _next(self, session: Session) -> NextInfo:
        if session.phase is Phase.FINISHED:
            return NextInfo(NextStep.FINISHED)
        if session.user_eliminated:
            return NextInfo(NextStep.ELIMINATED)
        if session.phase is Phase.PLAYOFFS_PENDING:
            return NextInfo(NextStep.AWAITING_PLAYOFFS_DRAW)
        upcoming = self._user_match(session, session.round + 1)
        if upcoming.stage is Stage.THIRD_PLACE:
            return NextInfo(NextStep.THIRD_PLACE_MATCH, upcoming)
        return NextInfo(NextStep.NEXT_ROUND, upcoming)
