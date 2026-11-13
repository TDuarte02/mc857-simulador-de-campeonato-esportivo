"""MongoDB repositories, run against mongomock instead of a real server."""

import random
from datetime import UTC, datetime

import mongomock
import pytest

import api.container
from api.config import Settings
from api.container import build_container
from api.domain.models import (
    Card,
    CardType,
    Goal,
    Injury,
    Match,
    MatchResult,
    Phase,
    PlayerStatus,
    Position,
    Session,
    Stage,
    Tournament,
    UnavailableReason,
)
from api.repositories.mongo import create_mongo_repositories, seed_catalogue
from conftest import Cup, make_client, mock_mongo_db


@pytest.fixture
def db():
    return mock_mongo_db()


@pytest.fixture
def repos(db):
    return create_mongo_repositories(db)


def a_session(session_id: str = "s1") -> Session:
    return Session(
        id=session_id,
        created_at=datetime(2026, 11, 9, 12, 30, tzinfo=UTC),
        phase=Phase.SEMI_FINALS,
        squad_id="brazil",
        call_up=[303, 301, 302],
        player_status={
            301: PlayerStatus(yellow_cards=1),
            302: PlayerStatus(suspended_matches=1, suspension_reason=UnavailableReason.SUSPENDED_RED),
            303: PlayerStatus(injured_matches=2),
        },
        round=4,
        user_eliminated=False,
    )


def a_match(match_id: str, round_no: int = 1, session_id: str = "s1", result=None) -> Match:
    return Match(match_id, session_id, Stage.GROUP, round_no, "brazil", "peru", "A", result, played=result is not None)


# --- Catalogue ------------------------------------------------------------------


def test_seed_loads_the_catalogue_once(db):
    seed_catalogue(db)
    seed_catalogue(db)

    assert db.squads.count_documents({}) == 16
    assert db.players.count_documents({}) == 16 * 40


def test_seed_never_overwrites_existing_data(db):
    db.squads.insert_one({"_id": "brazil", "name": "Seleção", "flag": "x", "federation": "CONMEBOL"})

    seed_catalogue(db)

    assert db.squads.count_documents({}) == 1
    assert db.squads.find_one({"_id": "brazil"})["name"] == "Seleção"
    assert db.players.count_documents({}) > 0  # players were still empty, so they are seeded


def test_create_mongo_repositories_adds_the_query_indexes(db):
    create_mongo_repositories(db, seed=False)

    assert db.squads.find_one() is None
    player_indexes = [index["key"] for index in db.players.index_information().values()]
    match_indexes = [index["key"] for index in db.matches.index_information().values()]
    assert [("squad_id", 1), ("position", 1)] in player_indexes
    assert [("session_id", 1), ("round", 1)] in match_indexes


def test_squads_are_listed_and_fetched(repos):
    squads = repos.squads.list_all()

    assert len(squads) == 16
    assert [squad.id for squad in squads] == sorted(squad.id for squad in squads)
    assert repos.squads.get("brazil").name == "Brasil"
    assert repos.squads.get("atlantis") is None


def test_players_are_filtered_by_squad_and_position(repos):
    everyone = repos.players.list_by_squad("brazil")
    keepers = repos.players.list_by_squad("brazil", Position.GK)

    assert len(everyone) == 40
    assert all(player.squad_id == "brazil" for player in everyone)
    assert [player.id for player in everyone] == sorted(player.id for player in everyone)
    assert keepers and all(player.position is Position.GK for player in keepers)
    assert repos.players.list_by_squad("atlantis") == []


def test_get_many_keeps_the_requested_order_and_skips_unknown_ids(repos):
    first, second = repos.players.list_by_squad("peru")[:2]

    found = repos.players.get_many([second.id, 999_999, first.id])

    assert found == [second, first]


# --- Sessions ---------------------------------------------------------------------


def test_session_round_trips_with_player_status(repos):
    session = a_session()

    repos.sessions.add(session)

    assert repos.sessions.get("s1") == session
    assert repos.sessions.get("missing") is None


def test_session_is_stored_as_plain_bson(repos, db):
    repos.sessions.add(a_session())

    doc = db.sessions.find_one({"_id": "s1"})
    assert type(doc["phase"]) is str
    assert doc["player_status"][1] == {
        "player_id": 302,
        "yellow_cards": 0,
        "suspended_matches": 1,
        "suspension_reason": "SUSPENDED_RED",
        "injured_matches": 0,
    }


def test_changes_only_count_once_saved(repos):
    repos.sessions.add(a_session())

    loaded = repos.sessions.get("s1")
    loaded.round = 5
    assert repos.sessions.get("s1").round == 4

    repos.sessions.save(loaded)
    assert repos.sessions.get("s1").round == 5


def test_naive_dates_from_the_driver_are_read_as_utc():
    repos = create_mongo_repositories(mongomock.MongoClient()["copa"], seed=False)  # not tz-aware
    repos.sessions.add(a_session())

    assert repos.sessions.get("s1").created_at == a_session().created_at


# --- Tournaments and matches ----------------------------------------------------


def test_tournament_round_trips(repos):
    tournament = Tournament("s1", {"A": ["brazil", "peru"]}, {"brazil": [1, 2], "costa_rica": [3]})

    repos.tournaments.save(tournament)

    assert repos.tournaments.get("s1") == tournament
    assert repos.tournaments.get("s2") is None


def test_match_result_round_trips_with_every_event(repos):
    result = MatchResult(
        home_goals=1,
        away_goals=1,
        goals=[Goal(12, 301, "brazil"), Goal(80, 901, "peru")],
        cards=[Card(30, 302, "brazil", CardType.YELLOW), Card(70, 902, "peru", CardType.RED)],
        injuries=[Injury(55, 303, "brazil", 3)],
        home_penalties=4,
        away_penalties=2,
    )
    match = Match("QF1", "s1", Stage.QUARTER_FINAL, 4, "brazil", "peru", None, result, played=True)

    repos.tournaments.save_matches([match])

    assert repos.tournaments.list_matches("s1") == [match]
    assert repos.tournaments.list_matches("s1")[0].winner == "brazil"


def test_matches_are_filtered_by_session_and_round_and_ordered_by_id(repos):
    repos.tournaments.save_matches([a_match("G-B-R1-1"), a_match("G-A-R2-1", 2), a_match("G-A-R1-1")])
    repos.tournaments.save_matches([a_match("G-A-R1-1", session_id="other")])

    assert [m.id for m in repos.tournaments.list_matches("s1")] == ["G-A-R1-1", "G-A-R2-1", "G-B-R1-1"]
    assert [m.id for m in repos.tournaments.list_matches("s1", round_no=1)] == ["G-A-R1-1", "G-B-R1-1"]
    assert len(repos.tournaments.list_matches("other")) == 1


def test_saving_a_match_again_updates_it(repos, db):
    repos.tournaments.save_matches([a_match("G-A-R1-1")])

    repos.tournaments.save_matches([a_match("G-A-R1-1", result=MatchResult(2, 0))])

    assert db.matches.count_documents({"session_id": "s1"}) == 1
    stored = repos.tournaments.list_matches("s1")[0]
    assert stored.played and stored.result.home_goals == 2


# --- Wiring and persistence ---------------------------------------------------------


def test_settings_read_the_mongo_connection_from_the_environment(monkeypatch):
    monkeypatch.setenv("REPOSITORY", "mongo")
    monkeypatch.setenv("MONGO_URI", "mongodb://db.example:27017")
    monkeypatch.setenv("MONGO_DB", "copa_test")

    settings = Settings.from_env()

    assert (settings.repository, settings.mongo_uri, settings.mongo_db) == (
        "mongo",
        "mongodb://db.example:27017",
        "copa_test",
    )


def test_container_connects_with_the_configured_uri_and_database(monkeypatch):
    clients = []

    def fake_client(uri, **options):
        clients.append((uri, options))
        return mongomock.MongoClient(tz_aware=True)

    monkeypatch.setattr(api.container, "MongoClient", fake_client)
    container = build_container(Settings(repository="mongo", mongo_uri="mongodb://mongo:27017", mongo_db="copa_x"))

    assert clients[0][0] == "mongodb://mongo:27017"
    assert clients[0][1]["tz_aware"] is True
    assert len(container.squads.list_squads()) == 16


def test_a_session_survives_an_app_restart(db):
    def boot():
        container = build_container(repositories=create_mongo_repositories(db), rng=random.Random(3))
        return make_client(container)

    cup = Cup(boot())
    cup.start()
    cup.play()
    before = cup.get("history").get_json()

    cup.client = boot()  # a new app process on the same database

    assert cup.get("history").get_json() == before
    assert cup.play()["match"]["round"] == 2
    assert cup.get("round-results").get_json()["round"] == 2
