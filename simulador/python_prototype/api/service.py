"""Orquestra TournamentGame / UserMatchSession: suspensões, cartões e views."""
from __future__ import annotations

import secrets
from typing import Any

from simulador.python_prototype.cards import derive_cards, red_card_players
from python_prototype.common import TEAM_IDS
from python_prototype.game import TournamentGame
from python_prototype.group_stage import MatchRecord, MatchStatus, group_standings
from python_prototype.match import CycleResult
from simulador.python_prototype.match_view import MatchLineups, build_match_view
from python_prototype.session import UserMatchSession, lineup_from_picks
from python_prototype.tournament import TournamentConfig, derive_seed

from .catalog import Catalog
from .errors import ApiError
from .store import GameSession, GameStore


def _side_name(record: MatchRecord, side: str) -> str | None:
    return record.team_a if side == "A" else record.team_b


def match_summary(record: MatchRecord) -> dict[str, Any]:
    result, winner, pen, ga, gb = record.result, None, None, None, None
    if result is not None:
        ga, gb = result.goals_a, result.goals_b
        if ga != gb:
            winner = record.team_a if ga > gb else record.team_b
        if result.penalties is not None:
            p = result.penalties
            pen = {"first_team": _side_name(record, p.first_team), "goals_a": p.goals_a,
                   "goals_b": p.goals_b, "winner": _side_name(record, p.winner),
                   "sudden_death": p.sudden_death}
            if ga == gb:
                winner = pen["winner"]
    return {
        "id": record.match_id, "phase": record.phase.value, "group": record.group,
        "round": record.round_number, "slot_a": record.slot_a, "slot_b": record.slot_b,
        "team_a": record.team_a, "team_b": record.team_b, "status": record.status.value,
        "goals_a": ga, "goals_b": gb, "penalties": pen, "winner": winner,
    }


def _cycle_out(c: CycleResult) -> dict[str, Any]:
    return {
        "cycle": c.cycle, "start_minute": c.start_minute, "end_minute": c.end_minute,
        "goals": c.goals, "scorers": list(c.scorers),
        "possessions": [
            {"index": p.index, "attacking_team": p.attacking_team,
             "attempts": p.attack.attempts, "scorer": p.scorer}
            for p in c.possessions
        ],
    }


class GameService:
    def __init__(self, catalog: Catalog, store: GameStore,
                 config_overrides: dict[str, Any] | None = None) -> None:
        self.catalog, self.store = catalog, store
        self.config_overrides = config_overrides or {}

    # --- criação / consulta -----------------------------------------------

    def create_game(self, user_team: str, squad: list[str], seed: int | None) -> GameSession:
        nation = self.catalog.resolve_nation(user_team)
        seed = secrets.randbelow(2**31) if seed is None else seed
        config = TournamentConfig(seed=seed, **self.config_overrides)
        user = self.catalog.build_user_team(nation, squad, config)
        teams = tuple(user if n == nation else self.catalog.base_teams[n] for n in config.nations)
        game = TournamentGame.create(config, teams, nation)
        return self.store.add(game, seed)

    def active_match(self, gs: GameSession) -> dict[str, Any] | None:
        s = gs.game.session
        if s is None:
            return None
        return {
            "match_id": s.match_id, "team_a": s.record.team_a, "team_b": s.record.team_b,
            "user_side": s.user_side, "phase": s.phase.value, "minute": s.match.clock,
            "score": s.score, "can_change_lineup": s.can_change_lineup,
            "cycles_played": len(s.cycles),
            "lineup": [{"player": p.name, "slot": slot}
                       for p, slot in zip(s.user_lineup, s.user_formation)],
            "formation": list(s.user_formation),
        }

    def _eliminated(self, gs: GameSession) -> bool:
        g = gs.game
        if not g.user_eliminated:
            return False
        return not (g.is_finished and g.final_ranking().champion == g.user_team)

    def state(self, gs: GameSession) -> dict[str, Any]:
        game = gs.game
        st = game.state
        try:
            nxt = game.next_match()
        except ValueError:
            nxt = None
        groups = []
        for group in st.groups:
            standings = group_standings(st, group.name)
            groups.append({
                "name": group.name,
                "teams": [t.name for t in group.teams],
                "standings": [
                    {"team": r.team, "played": r.played, "wins": r.wins, "draws": r.draws,
                     "losses": r.losses, "goals_for": r.goals_for,
                     "goals_against": r.goals_against, "goal_diff": r.goal_diff,
                     "points": r.points}
                    for r in standings.rows
                ],
                "is_final": standings.is_final,
                "matches": [match_summary(m) for m in st.group_matches(group.name)],
            })
        pending = game.pending_user_match
        return {
            "game_id": gs.game_id, "seed": gs.seed, "user_team": game.user_team,
            "phase": game.phase.value, "is_finished": game.is_finished,
            "user_eliminated": self._eliminated(gs),
            "groups": groups,
            "knockout": [match_summary(m) for m in st.matches.values()
                         if m.phase.value == "MATA_MATA"],
            "next_match": match_summary(nxt) if nxt else None,
            "pending_user_match": match_summary(pending) if pending else None,
            "active_match": self.active_match(gs),
            "suspended": sorted(gs.suspended),
        }

    # --- fluxo do usuário ---------------------------------------------------

    def advance(self, gs: GameSession) -> dict[str, Any]:
        record = gs.game.advance_to_user_match()
        return {
            "pending_match": match_summary(record) if record else None,
            "phase": gs.game.phase.value, "user_eliminated": self._eliminated(gs),
            "is_finished": gs.game.is_finished, "suspended": sorted(gs.suspended),
        }

    @staticmethod
    def _reject_suspended(gs: GameSession, players) -> None:
        bad = sorted(p.name for p in players if p.name in gs.suspended)
        if bad:
            raise ApiError(422, "suspended_player",
                           f"Jogador(es) suspenso(s) não podem ser escalados: {', '.join(bad)}.")

    def _picks(self, gs: GameSession, picks, formation):
        team = gs.game.state.teams[gs.game.user_team]
        players, slots = lineup_from_picks(team, [(p.player, p.slot) for p in picks])
        if formation is not None and tuple(formation) != slots:
            raise ApiError(422, "invalid_lineup", "A formação não corresponde aos slots dos picks.")
        self._reject_suspended(gs, players)
        return players, slots

    def start_match(self, gs: GameSession, picks) -> dict[str, Any]:
        game = gs.game
        if picks:
            players, formation = self._picks(gs, picks, None)
        else:
            players, formation = None, None
            self._reject_suspended(gs, game.state.teams[game.user_team].lineup)
        game.start_user_match(players, formation)
        gs.first_half = None
        return self.active_match(gs)

    def _session(self, gs: GameSession) -> UserMatchSession:
        s = gs.game.session
        if s is None:
            raise ApiError(409, "no_active_match", "Não há partida do usuário em andamento.")
        return s

    def change_lineup(self, gs: GameSession, picks, formation) -> dict[str, Any]:
        session = self._session(gs)
        players, slots = self._picks(gs, picks, formation)
        session.change_lineup(players, slots)
        return self.active_match(gs)

    def second_half(self, gs: GameSession) -> dict[str, Any]:
        self._session(gs).start_second_half()
        return self.active_match(gs)

    def cancel(self, gs: GameSession) -> dict[str, Any]:
        gs.game.cancel_user_match()
        gs.first_half = None
        return self.state(gs)

    def play(self, gs: GameSession, until: str) -> dict[str, Any]:
        session = self._session(gs)
        if gs.first_half is None and session.match.cycle_index == 0:
            gs.first_half = {s: session.match.teams[s].players for s in TEAM_IDS}
        before = len(session.cycles)
        if until == "halftime":
            session.play_until_stop()
        else:
            session.play_to_end()
        cycles = session.cycles[before:]
        view = None
        if session.is_finished:
            self._finalize(gs, session)
            view = self.match_view(gs, session.record.match_id)
        return {
            "match_id": session.match_id, "phase": session.phase.value,
            "minute": session.match.clock, "score": session.score,
            "finished": session.is_finished, "cycles": [_cycle_out(c) for c in cycles],
            "view": view, "suspended": sorted(gs.suspended),
        }

    def _finalize(self, gs: GameSession, session: UserMatchSession) -> None:
        record, config = session.record, gs.game.state.config
        second = {s: session.match.teams[s].players for s in TEAM_IDS}
        lineups = MatchLineups(gs.first_half or second, second)
        cards = derive_cards(
            record.result.events, lineups.at, config.cards,
            seed=derive_seed(config.seed, record.match_id, "cards"),
        )
        gs.lineups[record.match_id] = lineups
        gs.cards[record.match_id] = cards
        # Vermelho do usuário suspende na próxima partida DELE; quem cumpriu sai da lista.
        gs.suspended = set(red_card_players(cards, session.user_side))
        gs.first_half = None

    def simulate(self, gs: GameSession) -> dict[str, Any]:
        gs.game.simulate_to_end()
        return self.state(gs)

    # --- partida ------------------------------------------------------------

    def match_view(self, gs: GameSession, match_id: str) -> dict[str, Any]:
        st = gs.game.state
        try:
            record = st.match(match_id)
        except ValueError as exc:
            raise ApiError(404, "match_not_found", str(exc)) from exc
        if record.status is not MatchStatus.ENCERRADA or record.result is None:
            raise ApiError(409, "match_not_played", f"A partida {match_id} ainda não foi jogada.")
        config = st.config
        lineups = gs.lineups.get(match_id) or MatchLineups.constant(
            st.teams[record.team_a].lineup, st.teams[record.team_b].lineup)
        cards = gs.cards.get(match_id)
        if cards is None:
            cards = derive_cards(
                record.result.events, lineups.at, config.cards,
                seed=derive_seed(config.seed, match_id, "cards"))
            gs.cards[match_id] = cards
        return build_match_view(
            match_id=match_id, seed=config.seed,
            team_names={"A": record.team_a, "B": record.team_b},
            events=record.result.events, card_events=cards, lineups=lineups,
            penalties=record.result.penalties,
        )
