"""MongoDB repositories.

Collections: squads, players, sessions, tournaments, matches. Documents use
snake_case fields and plain strings for enums; each repository converts between
documents and the domain dataclasses, so no Mongo document leaves this module.

Only single-document operations are used (no bulk_write), which keeps the code
runnable against mongomock in the unit tests.
"""

from collections.abc import Iterable
from datetime import UTC

from pymongo import ASCENDING
from pymongo.database import Database

from api.domain.models import (
    Card,
    CardType,
    Federation,
    Goal,
    Injury,
    Match,
    MatchResult,
    Phase,
    Player,
    PlayerStatus,
    Position,
    Session,
    Squad,
    Stage,
    Tournament,
    UnavailableReason,
)
from api.repositories.base import (
    PlayerRepository,
    Repositories,
    SessionRepository,
    SquadRepository,
    TournamentRepository,
)
from api.repositories.mock_data import build_players, build_squads


def create_mongo_repositories(db: Database, seed: bool = True) -> Repositories:
    """Repositories over `db`, with indexes in place and, if `seed`, the mock catalogue loaded."""
    db.players.create_index([("squad_id", ASCENDING), ("position", ASCENDING)])
    db.matches.create_index([("session_id", ASCENDING), ("round", ASCENDING)])
    if seed:
        seed_catalogue(db)
    return Repositories(
        squads=MongoSquadRepository(db),
        players=MongoPlayerRepository(db),
        sessions=MongoSessionRepository(db),
        tournaments=MongoTournamentRepository(db),
    )


def seed_catalogue(db: Database) -> None:
    """Loads the mock squads and players into empty collections. Existing data is left alone."""
    if db.squads.find_one() is None:
        db.squads.insert_many([_squad_doc(squad) for squad in build_squads()])
    if db.players.find_one() is None:
        db.players.insert_many([_player_doc(player) for player in build_players()])


class MongoSquadRepository(SquadRepository):
    def __init__(self, db: Database):
        self._squads = db.squads

    def list_all(self) -> list[Squad]:
        return [_squad(doc) for doc in self._squads.find().sort("_id", ASCENDING)]

    def get(self, squad_id: str) -> Squad | None:
        doc = self._squads.find_one({"_id": squad_id})
        return _squad(doc) if doc else None


class MongoPlayerRepository(PlayerRepository):
    def __init__(self, db: Database):
        self._players = db.players

    def list_by_squad(self, squad_id: str, position: Position | None = None) -> list[Player]:
        query = {"squad_id": squad_id}
        if position is not None:
            query["position"] = position.value
        return [_player(doc) for doc in self._players.find(query).sort("_id", ASCENDING)]

    def get_many(self, player_ids: Iterable[int]) -> list[Player]:
        ids = list(player_ids)
        found = {doc["_id"]: _player(doc) for doc in self._players.find({"_id": {"$in": ids}})}
        return [found[player_id] for player_id in ids if player_id in found]


class MongoSessionRepository(SessionRepository):
    def __init__(self, db: Database):
        self._sessions = db.sessions

    def add(self, session: Session) -> None:
        self._sessions.insert_one(_session_doc(session))

    def get(self, session_id: str) -> Session | None:
        doc = self._sessions.find_one({"_id": session_id})
        return _session(doc) if doc else None

    def save(self, session: Session) -> None:
        self._sessions.replace_one({"_id": session.id}, _session_doc(session), upsert=True)


class MongoTournamentRepository(TournamentRepository):
    def __init__(self, db: Database):
        self._tournaments = db.tournaments
        self._matches = db.matches

    def get(self, session_id: str) -> Tournament | None:
        doc = self._tournaments.find_one({"_id": session_id})
        return _tournament(doc) if doc else None

    def save(self, tournament: Tournament) -> None:
        doc = _tournament_doc(tournament)
        self._tournaments.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    def list_matches(self, session_id: str, round_no: int | None = None) -> list[Match]:
        query: dict = {"session_id": session_id}
        if round_no is not None:
            query["round"] = round_no
        return [_match(doc) for doc in self._matches.find(query).sort("match_id", ASCENDING)]

    def save_matches(self, matches: Iterable[Match]) -> None:
        for match in matches:
            doc = _match_doc(match)
            self._matches.replace_one({"_id": doc["_id"]}, doc, upsert=True)


# --- Domain <-> document ---------------------------------------------------------


def _squad_doc(squad: Squad) -> dict:
    return {
        "_id": squad.id,
        "name": squad.name,
        "flag": squad.flag,
        "federation": squad.federation.value,
    }


def _squad(doc: dict) -> Squad:
    return Squad(doc["_id"], doc["name"], doc["flag"], Federation(doc["federation"]))


def _player_doc(player: Player) -> dict:
    return {
        "_id": player.id,
        "squad_id": player.squad_id,
        "name": player.name,
        "age": player.age,
        "position": player.position.value,
        "overall": player.overall,
        "is_current": player.is_current,
        "is_legend": player.is_legend,
    }


def _player(doc: dict) -> Player:
    return Player(
        id=doc["_id"],
        squad_id=doc["squad_id"],
        name=doc["name"],
        age=doc["age"],
        position=Position(doc["position"]),
        overall=doc["overall"],
        is_current=doc.get("is_current", False),
        is_legend=doc.get("is_legend", False),
    )


def _session_doc(session: Session) -> dict:
    return {
        "_id": session.id,
        "created_at": session.created_at,
        "phase": session.phase.value,
        "squad_id": session.squad_id,
        "call_up": session.call_up,
        # BSON keys must be strings, so the per-player map is stored as a list.
        "player_status": [
            {
                "player_id": player_id,
                "yellow_cards": status.yellow_cards,
                "suspended_matches": status.suspended_matches,
                "suspension_reason": status.suspension_reason.value if status.suspension_reason else None,
                "injured_matches": status.injured_matches,
            }
            for player_id, status in session.player_status.items()
        ],
        "round": session.round,
        "user_eliminated": session.user_eliminated,
    }


def _session(doc: dict) -> Session:
    created_at = doc["created_at"]
    if created_at.tzinfo is None:  # BSON dates are UTC; clients that are not tz-aware drop the zone
        created_at = created_at.replace(tzinfo=UTC)
    return Session(
        id=doc["_id"],
        created_at=created_at,
        phase=Phase(doc["phase"]),
        squad_id=doc["squad_id"],
        call_up=list(doc["call_up"]),
        player_status={
            entry["player_id"]: PlayerStatus(
                yellow_cards=entry["yellow_cards"],
                suspended_matches=entry["suspended_matches"],
                suspension_reason=UnavailableReason(entry["suspension_reason"])
                if entry["suspension_reason"]
                else None,
                injured_matches=entry["injured_matches"],
            )
            for entry in doc["player_status"]
        },
        round=doc["round"],
        user_eliminated=doc["user_eliminated"],
    )


def _tournament_doc(tournament: Tournament) -> dict:
    return {"_id": tournament.session_id, "groups": tournament.groups, "squads": tournament.squads}


def _tournament(doc: dict) -> Tournament:
    return Tournament(
        session_id=doc["_id"],
        groups={name: list(teams) for name, teams in doc["groups"].items()},
        squads={squad_id: list(players) for squad_id, players in doc["squads"].items()},
    )


def _match_doc(match: Match) -> dict:
    return {
        "_id": f"{match.session_id}/{match.id}",
        "session_id": match.session_id,
        "match_id": match.id,
        "stage": match.stage.value,
        "round": match.round,
        "home": match.home,
        "away": match.away,
        "group": match.group,
        "played": match.played,
        "result": _result_doc(match.result) if match.result else None,
    }


def _match(doc: dict) -> Match:
    return Match(
        id=doc["match_id"],
        session_id=doc["session_id"],
        stage=Stage(doc["stage"]),
        round=doc["round"],
        home=doc["home"],
        away=doc["away"],
        group=doc["group"],
        result=_result(doc["result"]) if doc["result"] else None,
        played=doc["played"],
    )


def _result_doc(result: MatchResult) -> dict:
    return {
        "home_goals": result.home_goals,
        "away_goals": result.away_goals,
        "home_penalties": result.home_penalties,
        "away_penalties": result.away_penalties,
        "goals": [
            {"minute": goal.minute, "player_id": goal.player_id, "squad_id": goal.squad_id}
            for goal in result.goals
        ],
        "cards": [
            {
                "minute": card.minute,
                "player_id": card.player_id,
                "squad_id": card.squad_id,
                "type": card.type.value,
            }
            for card in result.cards
        ],
        "injuries": [
            {
                "minute": injury.minute,
                "player_id": injury.player_id,
                "squad_id": injury.squad_id,
                "matches_out": injury.matches_out,
            }
            for injury in result.injuries
        ],
    }


def _result(doc: dict) -> MatchResult:
    return MatchResult(
        home_goals=doc["home_goals"],
        away_goals=doc["away_goals"],
        goals=[Goal(g["minute"], g["player_id"], g["squad_id"]) for g in doc["goals"]],
        cards=[Card(c["minute"], c["player_id"], c["squad_id"], CardType(c["type"])) for c in doc["cards"]],
        injuries=[
            Injury(i["minute"], i["player_id"], i["squad_id"], i["matches_out"]) for i in doc["injuries"]
        ],
        home_penalties=doc["home_penalties"],
        away_penalties=doc["away_penalties"],
    )
