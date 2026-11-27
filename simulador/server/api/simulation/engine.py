"""The match engine (copa_engine) as the server's simulator, and the lineups it plays.

Domain <-> engine:
- an engine Player is named `str(player_id)` (real names repeat inside a squad; ids
  round-trip), with the 18 attributes of `Player.attributes`;
- each XI goes in slot order, with the formation's slot codes;
- every draw derives from the session seed and the match id, exactly as the engine's
  own tournament does: the match itself (no label), "dynamics", "penalties", "cards",
  "scorers", and "injury" + player id for how long an injury lasts.

The engine only logs possessions; the result the API shows is derived afterwards
(copa_engine.derive): one scorer per goal, a display minute inside the 15-minute
cycle, cards from the fouls, and each injury's length.
"""

import random
from collections.abc import Sequence

from copa_engine.collective_attributes import Player as EnginePlayer
from copa_engine.collective_attributes import calculate_team_attributes
from copa_engine.config import DEFAULT_ENGINE_CONFIG, EngineConfig
from copa_engine.derive import MatchLineups, derive_goals, derive_match_cards, foul_minute, injury_matches
from copa_engine.lineup import DEFAULT_FORMATION, FORMATIONS, SquadMember, assign_slots, default_lineup
from copa_engine.match import MatchEventType, create_match, play_match
from copa_engine.penalties import simulate_penalty_shootout
from copa_engine.rules import derive_seed

from api.domain.engine_data import ENGINE_ATTRIBUTES
from api.domain.models import Card, CardType, Goal, Injury, MatchResult, Player, Position
from api.simulation.base import MatchContext, MatchSimulator, TeamSheet

# D9: what the user plays when they send no formation (the app's default). Machine
# teams always play the engine's 4-3-3.
DEFAULT_USER_FORMATION = "4-4-2"
MACHINE_FORMATION = "4-3-3"
assert FORMATIONS[MACHINE_FORMATION] == DEFAULT_FORMATION

# A position code for players stored without any (e.g. an old mock catalogue).
_SECTOR_CODE = {Position.GK: "GK", Position.DEF: "CB", Position.MID: "CM", Position.FW: "ST"}


# --- Domain -> engine -------------------------------------------------------------------


def _positions(player: Player) -> tuple[str, ...]:
    return tuple(player.positions) or (_SECTOR_CODE[player.position],)


def engine_player(player: Player, pos: str | None = None) -> EnginePlayer:
    attributes = player.attributes or {field: player.overall for field in ENGINE_ATTRIBUTES}
    return EnginePlayer(
        name=str(player.id),
        pos=pos or _positions(player)[0],
        **{field: attributes[field] for field in ENGINE_ATTRIBUTES},
    )


def squad_member(player: Player) -> SquadMember:
    return SquadMember(engine_player(player), _positions(player))


def _sheet(squad_id: str, players: Sequence[Player], lineup: Sequence[EnginePlayer], formation: str) -> TeamSheet:
    by_id = {player.id: player for player in players}
    return TeamSheet(squad_id, [by_id[int(p.name)] for p in lineup], formation, list(FORMATIONS[formation]))


# --- Lineups -------------------------------------------------------------------------------


def default_sheet(squad_id: str, squad: Sequence[Player]) -> TeamSheet:
    """A squad the user does not control: the engine's default XI in its 4-3-3."""
    lineup = default_lineup(squad_id, [squad_member(p) for p in squad], DEFAULT_FORMATION)
    return _sheet(squad_id, squad, lineup, MACHINE_FORMATION)


def team_strength(squad_id: str, squad: Sequence[Player]) -> float:
    """What the draw seeds pots by: mean attack, defence and control of the default XI."""
    lineup = default_lineup(squad_id, [squad_member(p) for p in squad], DEFAULT_FORMATION)
    attributes = calculate_team_attributes(lineup, DEFAULT_FORMATION)
    return (attributes.attack + attributes.defense + attributes.control) / 3


def user_sheet(squad_id: str, xi: Sequence[Player], formation: str) -> TeamSheet:
    """The user's XI in `formation` (copa_engine.lineup.assign_slots).

    The XI goes in id order, so the stand-in goalkeeper's tie-break is the lowest id.
    KeyError for an unknown formation, LineupDoesNotFit when the XI does not fit it.
    """
    ordered = sorted(xi, key=lambda player: player.id)
    lineup = assign_slots([squad_member(p) for p in ordered], FORMATIONS[formation])
    return _sheet(squad_id, ordered, lineup, formation)


# --- The simulator ---------------------------------------------------------------------------


class EngineMatchSimulator(MatchSimulator):
    """The real model. The user's matches and everyone else's run on the same engine."""

    def __init__(self, config: EngineConfig = DEFAULT_ENGINE_CONFIG):
        self._config = config

    def simulate_match(self, context: MatchContext) -> MatchResult:
        return self._play(context)

    def simulate_quick(self, context: MatchContext) -> MatchResult:
        return self._play(context)

    def _play(self, context: MatchContext) -> MatchResult:
        config, seed, match_id = self._config, context.seed, context.match_id
        sheets = {"A": context.home, "B": context.away}
        lineups = {}
        for side, sheet in sheets.items():
            if sheet.slots is None:
                raise ValueError(f"The engine needs {sheet.squad_id}'s XI with its slots.")
            lineups[side] = [engine_player(p, slot) for p, slot in zip(sheet.players, sheet.slots)]

        state = create_match(lineups["A"], sheets["A"].slots, lineups["B"], sheets["B"].slots)
        play_match(
            state,
            seed=derive_seed(seed, match_id),
            attack_params=config.attack_params,
            recovery_control_bonus=config.recovery_control_bonus,
            possessions_per_cycle=config.possessions_per_cycle,
            dynamics=config.dynamics,
            dynamics_seed=derive_seed(seed, match_id, "dynamics"),
        )
        events = tuple(state.events)
        squad = {side: sheet.squad_id for side, sheet in sheets.items()}
        result = MatchResult(home_goals=state.score["A"], away_goals=state.score["B"])

        if context.needs_winner and result.home_goals == result.away_goals:
            shootout = simulate_penalty_shootout(
                state.teams["A"].players,  # the XIs at full time
                state.teams["B"].players,
                config.penalties,
                rng=random.Random(derive_seed(seed, match_id, "penalties")),
            )
            result.home_penalties, result.away_penalties = shootout.goals_a, shootout.goals_b

        constant = MatchLineups.constant(lineups["A"], lineups["B"])  # no changes at half time
        result.goals = [
            Goal(goal.minute, int(goal.player.name), squad[goal.team])
            for goal in derive_goals(events, constant, seed=seed, match_id=match_id)
        ]
        cards = [
            Card(
                foul_minute(events, card.data["foul_event"]),
                int(card.data["player"]),
                squad[card.team],
                CardType.RED if card.type is MatchEventType.CARTAO_VERMELHO else CardType.YELLOW,
                second_yellow=bool(card.data.get("second_yellow")),
            )
            for card in derive_match_cards(events, constant, config.cards, seed=seed, match_id=match_id)
        ]
        result.cards = sorted(cards, key=lambda card: card.minute)
        injured: dict[int, Injury] = {}
        for event in events:
            if event.type is MatchEventType.LESAO:
                player_id = int(event.data["player"])
                injured.setdefault(
                    player_id,
                    Injury(
                        foul_minute(events, event.data["foul_event"]),
                        player_id,
                        squad[event.team],
                        injury_matches(seed, match_id, player_id),
                    ),
                )
        result.injuries = list(injured.values())
        return result
