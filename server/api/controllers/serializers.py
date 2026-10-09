"""Turns what the services return into the JSON the client receives (camelCase)."""

from api.domain.models import (
    Availability,
    CallUp,
    Draw,
    History,
    Match,
    Player,
    PlayoffsDraw,
    Podium,
    Preset,
    RoundResults,
    SimulationOutcome,
    Squad,
    Stage,
    Standing,
)
from api.services.squad_service import SquadService


class Serializer:
    def __init__(self, squads: SquadService):
        self._squads = squads  # resolves the squad and player ids stored on matches

    def squad(self, squad: Squad) -> dict:
        return {
            "id": squad.id,
            "name": squad.name,
            "flag": squad.flag,
            "federation": squad.federation,
        }

    def player(self, player: Player) -> dict:
        return {
            "id": player.id,
            "name": player.name,
            "age": player.age,
            "position": player.position,
            "overall": player.overall,
        }

    def preset(self, preset: Preset) -> dict:
        return {
            "id": preset.id,
            "name": preset.name,
            "description": preset.description,
            "players": [self.player(player) for player in preset.players],
        }

    def call_up(self, call_up: CallUp) -> dict:
        return {
            "sessionId": call_up.session_id,
            "squad": self._squad_by_id(call_up.squad_id),
            "players": [self.player(player) for player in call_up.players],
        }

    def draw(self, draw: Draw) -> dict:
        return {
            "userSquad": self._squad_by_id(draw.user_squad),
            "groups": [
                {
                    "name": name,
                    "squads": [
                        {
                            **self._squad_by_id(squad_id),
                            "players": [self.player(player) for player in draw.squads[squad_id]],
                        }
                        for squad_id in squad_ids
                    ],
                }
                for name, squad_ids in draw.groups.items()
            ],
            "matches": [self.match(match) for match in draw.matches],
        }

    def availability(self, availability: Availability) -> dict:
        return {
            "available": [
                {**self.player(player), "yellowCards": availability.yellow_cards[player.id]}
                for player in availability.available
            ],
            "unavailable": [
                {
                    **self.player(entry.player),
                    "reason": entry.reason,
                    "matchesRemaining": entry.matches_remaining,
                }
                for entry in availability.unavailable
            ],
        }

    def match(self, match: Match) -> dict:
        return {
            "id": match.id,
            "stage": match.stage,
            "round": match.round,
            "group": match.group,
            "home": self._squad_by_id(match.home),
            "away": self._squad_by_id(match.away),
            "played": match.played,
            # Pre-simulated results stay hidden until their round is played.
            "result": self._result(match) if match.played else None,
        }

    def outcome(self, outcome: SimulationOutcome) -> dict:
        upcoming = outcome.next.match
        return {
            "match": self.match(outcome.match),
            "next": {
                "step": outcome.next.step,
                "stage": upcoming.stage if upcoming else None,
                "round": upcoming.round if upcoming else None,
                "opponent": self._squad_by_id(upcoming.opponent_of(outcome.user_squad)) if upcoming else None,
            },
        }

    def round_results(self, results: RoundResults) -> dict:
        return {
            "round": results.round,
            "stage": results.stage,
            "matches": [self.match(match) for match in results.matches],
            "groups": self._groups(results.groups) if results.groups is not None else None,
            "qualified": self._squad_list(results.qualified),
            "advanced": self._squad_list(results.advanced),
            "podium": self._podium(results.podium),
        }

    def playoffs_draw(self, draw: PlayoffsDraw) -> dict:
        return {
            "qualified": self._squad_list(draw.qualified),
            "quarterFinals": [self.match(match) for match in draw.quarter_finals],
        }

    def history(self, history: History) -> dict:
        def stage(wanted: Stage) -> list[dict]:
            return [self.match(match) for match in history.matches if match.stage is wanted]

        def single(wanted: Stage) -> dict | None:
            return next(iter(stage(wanted)), None)

        user = history.user_squad
        played = [match for match in history.matches if match.played]
        return {
            "sessionId": history.session_id,
            "phase": history.phase,
            "userSquad": self._squad_by_id(user) if user else None,
            "placement": history.placement,
            "podium": self._podium(history.podium),
            "groups": self._groups(history.groups),
            "bracket": {
                "quarterFinals": stage(Stage.QUARTER_FINAL),
                "semiFinals": stage(Stage.SEMI_FINAL),
                "thirdPlace": single(Stage.THIRD_PLACE),
                "final": single(Stage.FINAL),
            },
            "userPath": [self.match(match) for match in played if match.involves(user)],
            "matches": [self.match(match) for match in played],
        }

    def _squad_by_id(self, squad_id: str) -> dict:
        return self.squad(self._squads.get_squad(squad_id))

    def _squad_list(self, squad_ids: list[str] | None) -> list[dict] | None:
        return None if squad_ids is None else [self._squad_by_id(squad_id) for squad_id in squad_ids]

    def _groups(self, groups: dict[str, list[Standing]]) -> list[dict]:
        return [
            {"name": name, "standings": [self._standing(row) for row in table]}
            for name, table in groups.items()
        ]

    def _standing(self, row: Standing) -> dict:
        return {
            "squad": self._squad_by_id(row.squad_id),
            "played": row.played,
            "won": row.won,
            "drawn": row.drawn,
            "lost": row.lost,
            "goalsFor": row.goals_for,
            "goalsAgainst": row.goals_against,
            "goalDifference": row.goal_difference,
            "points": row.points,
            "yellowCards": row.yellow_cards,
            "redCards": row.red_cards,
        }

    def _podium(self, podium: Podium | None) -> dict | None:
        if podium is None:
            return None
        return {
            "champion": self._squad_by_id(podium.champion),
            "runnerUp": self._squad_by_id(podium.runner_up),
            "third": self._squad_by_id(podium.third),
            "fourth": self._squad_by_id(podium.fourth),
        }

    def _result(self, match: Match) -> dict:
        result = match.result
        events = (*result.goals, *result.cards, *result.injuries)
        names = {p.id: p.name for p in self._squads.get_players({e.player_id for e in events})}

        def event(item, **extra) -> dict:
            return {
                "minute": item.minute,
                "squad": item.squad_id,
                "player": {"id": item.player_id, "name": names.get(item.player_id)},
                **extra,
            }

        penalties = None
        if result.home_penalties is not None:
            penalties = {"home": result.home_penalties, "away": result.away_penalties}
        return {
            "homeGoals": result.home_goals,
            "awayGoals": result.away_goals,
            "penalties": penalties,
            "winner": match.winner,
            "goals": [event(goal) for goal in result.goals],
            "cards": [event(card, type=card.type) for card in result.cards],
            "injuries": [event(injury, matchesOut=injury.matches_out) for injury in result.injuries],
        }
