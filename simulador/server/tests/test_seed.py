"""The offline catalogue loader (api/seed.py), on mongomock, and the API on a seeded catalogue."""

import csv
import random
from datetime import UTC, datetime
from pathlib import Path

import pytest

from api.config import Settings
from api.container import build_container
from api.domain.engine_data import ENGINE_ATTRIBUTES, LINE_ATTRIBUTES
from api.domain.models import Position
from api.repositories.mongo import create_mongo_repositories
from api.repositories.nations import NATIONS
from api.seed import SeedError, main, parse_catalog, seed_catalog
from conftest import Cup, make_client, mock_mongo_db

QUOTAS = Settings().squad_quotas
REAL_FILE = Path(__file__).resolve().parents[3] / "pipeline-dados/artefatos/jogadores_copa_america_2024_filtrado.csv"
COLUMNS = [
    "sofifa_id", "short_name", "long_name", "nationality_name", "player_positions", "age",
    *ENGINE_ATTRIBUTES, "camada", "is_convocado_2024", "person_key",
]


def catalogue_rows() -> list[dict]:
    """A valid catalogue: every nation with exactly one call-up's worth of players."""
    rows = []
    for nation in NATIONS:
        for code, count in (("GK", 3), ("CB", 8), ("CAM, CM", 8), ("ST", 7)):
            for n in range(count):
                player_id = len(rows) + 1
                row = {field: 70 for field in ENGINE_ATTRIBUTES}
                if code == "GK":
                    row.update({field: "" for field in LINE_ATTRIBUTES})
                row.update(
                    sofifa_id=player_id,
                    short_name=f"{nation.name} {code.split(',')[0]} {n}",
                    long_name=f"{nation.name} {code} {n}",
                    nationality_name=nation.dataset_name,
                    player_positions=code,
                    age=25,
                    camada="base_22",
                    is_convocado_2024=True,
                    person_key=player_id,
                )
                rows.append(row)
    return rows


def write_catalogue(path: Path, rows: list[dict]) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def row_of(rows, nation_id: str, code: str = "ST", n: int = 0) -> dict:
    nation = next(x for x in NATIONS if x.id == nation_id)
    return next(r for r in rows if r["short_name"] == f"{nation.name} {code} {n}")


@pytest.fixture
def rows():
    return catalogue_rows()


@pytest.fixture
def csv_file(tmp_path, rows):
    return write_catalogue(tmp_path / "players.csv", rows)


# --- Parsing ------------------------------------------------------------------------------


def test_a_valid_file_becomes_16_squads_of_players(csv_file):
    catalog = parse_catalog(csv_file, QUOTAS)

    assert [squad.id for squad in catalog.squads] == [nation.id for nation in NATIONS]
    assert len(catalog.players) == 16 * 26
    midfielder = next(p for p in catalog.players if p.positions == ("CAM", "CM"))
    assert midfielder.position is Position.MID
    assert midfielder.attributes["movement_agility"] == 70
    assert midfielder.is_current and not midfielder.is_legend


def test_goalkeepers_outfield_attributes_become_zero(csv_file):
    keeper = next(p for p in parse_catalog(csv_file, QUOTAS).players if p.position is Position.GK)

    assert keeper.positions == ("GK",)
    assert all(keeper.attributes[field] == 0 for field in LINE_ATTRIBUTES)
    assert keeper.attributes["goalkeeping_reflexes"] == 70


def test_accents_are_preserved(tmp_path, rows):
    row_of(rows, "argentina")["short_name"] = "Ángel Di María"
    catalog = parse_catalog(write_catalogue(tmp_path / "p.csv", rows), QUOTAS)

    assert "Ángel Di María" in {p.name for p in catalog.players}
    assert {s.name for s in catalog.squads} >= {"Bolívia", "Panamá", "Canadá"}


def test_duplicate_ids_are_rejected_with_their_lines(tmp_path, rows):
    row_of(rows, "peru")["sofifa_id"] = 1

    with pytest.raises(SeedError) as error:
        parse_catalog(write_catalogue(tmp_path / "p.csv", rows), QUOTAS)

    assert any("duplicate id 1 (also on line 2)" in str(p) for p in error.value.problems)


def test_missing_engine_fields_and_unknown_nations_are_rejected(tmp_path, rows):
    row_of(rows, "chile")["power_stamina"] = ""
    row_of(rows, "brazil", "CB")["pace"] = ""  # an outfield player cannot lack outfield attributes
    row_of(rows, "peru")["nationality_name"] = "Haiti"

    with pytest.raises(SeedError) as error:
        parse_catalog(write_catalogue(tmp_path / "p.csv", rows), QUOTAS)

    reasons = [p.reason for p in error.value.problems]
    assert "missing engine field power_stamina" in reasons
    assert "missing engine field pace" in reasons
    assert "unknown nation 'Haiti'" in reasons
    assert len([p for p in error.value.problems if p.line]) == 3
    # the refused rows also leave their squads a player short
    assert {p.name for p in error.value.problems if p.line is None} == {"chile", "brazil", "peru"}


def test_quotas_count_distinct_people(tmp_path, rows):
    # Two Uruguay forwards are the same person: 6 people at FW, one short of a call-up.
    first, second = row_of(rows, "uruguay", n=0), row_of(rows, "uruguay", n=1)
    second["person_key"] = first["person_key"]

    with pytest.raises(SeedError) as error:
        parse_catalog(write_catalogue(tmp_path / "p.csv", rows), QUOTAS)

    assert [str(p) for p in error.value.problems] == ["squad: uruguay: 6 distinct people at FW, a call-up needs 7"]


def test_the_real_catalogue_parses():
    catalog = parse_catalog(REAL_FILE, QUOTAS)

    assert len(catalog.squads) == 16
    assert "canada" in {player.squad_id for player in catalog.players}
    messi = [p for p in catalog.players if p.name == "L. Messi"]
    assert [(p.squad_id, p.is_current) for p in messi] == [("argentina", True)]
    assert all(len(p.attributes) == len(ENGINE_ATTRIBUTES) for p in catalog.players)


# --- Writing ------------------------------------------------------------------------------


def test_seeding_swaps_the_catalogue_in_and_keeps_the_indexes(csv_file):
    db = mock_mongo_db()
    create_mongo_repositories(db, seed_mock=True)  # a mock catalogue is replaced
    catalog = parse_catalog(csv_file, QUOTAS)

    assert seed_catalog(db, catalog) is True

    assert db.squads.count_documents({}) == 16
    assert db.players.count_documents({}) == 16 * 26
    assert db.players.find_one({"_id": 1})["attributes"]["pace"] == 0
    indexes = [index["key"] for index in db.players.index_information().values()]
    assert [("squad_id", 1), ("position", 1)] in indexes
    meta = db.catalog_meta.find_one({"_id": "catalog"})
    assert (meta["version"], meta["source_sha256"]) == (catalog.version, catalog.sha256)
    assert {"players_new", "squads_new"}.isdisjoint(db.list_collection_names())


def test_seeding_the_same_file_twice_is_a_no_op(csv_file):
    db = mock_mongo_db()
    catalog = parse_catalog(csv_file, QUOTAS)
    seed_catalog(db, catalog, now=datetime(2026, 1, 1, tzinfo=UTC))
    db.players.update_one({"_id": 1}, {"$set": {"name": "untouched"}})

    assert seed_catalog(db, parse_catalog(csv_file, QUOTAS)) is False

    assert db.players.find_one({"_id": 1})["name"] == "untouched"
    assert db.catalog_meta.find_one()["seeded_at"].year == 2026


def test_a_failed_seed_leaves_the_old_catalogue_intact(tmp_path, csv_file, rows, monkeypatch):
    db = mock_mongo_db()
    seed_catalog(db, parse_catalog(csv_file, QUOTAS))
    before = list(db.players.find().sort("_id"))
    row_of(rows, "peru")["sofifa_id"] = 1
    broken = write_catalogue(tmp_path / "broken.csv", rows)
    monkeypatch.setattr("api.seed.MongoClient", lambda *args, **kwargs: db.client)

    assert main(["--file", str(broken)]) == 1

    assert list(db.players.find().sort("_id")) == before


def test_the_cli_seeds_the_configured_database(csv_file, monkeypatch, capsys):
    db = mock_mongo_db()
    monkeypatch.setattr("api.seed.MongoClient", lambda *args, **kwargs: db.client)
    monkeypatch.setenv("MONGO_DB", db.name)

    assert main(["--file", str(csv_file)]) == 0
    assert main(["--file", str(csv_file)]) == 0

    out = capsys.readouterr().out
    assert "seeded; 16 squads, 416 players" in out
    assert "already seeded, nothing to do" in out


# --- The API on a seeded catalogue --------------------------------------------------------


def seeded_client(db) -> object:
    return make_client(build_container(repositories=create_mongo_repositories(db), rng=random.Random(5)))


def test_players_expose_their_positions(csv_file):
    db = mock_mongo_db()
    seed_catalog(db, parse_catalog(csv_file, QUOTAS))

    players = seeded_client(db).get("/brazil/players?position=MID").get_json()["players"]

    assert players and all(player["positions"] == ["CAM", "CM"] for player in players)


def test_two_versions_of_a_person_cannot_be_called_up_and_presets_skip_them(tmp_path, rows):
    # Brazil also has the legend version of its first forward: one more FW row, same person.
    forward = row_of(rows, "brazil")
    legend = {**forward, "sofifa_id": 9999, "short_name": "Brasil ST lenda", "camada": "historico", "overall": 95,
              "is_convocado_2024": False}
    rows.append(legend)
    db = mock_mongo_db()
    seed_catalog(db, parse_catalog(write_catalogue(tmp_path / "p.csv", rows), QUOTAS))
    client = seeded_client(db)
    cup = Cup(client, squad="brazil")

    for preset in client.get("/brazil/presets").get_json()["presets"]:
        ids = {player["id"] for player in preset["players"]}
        assert not {forward["sofifa_id"], 9999} <= ids, preset["id"]
    current = cup.preset("current")
    both = [9999 if player_id == current[-2] else player_id for player_id in current]
    assert forward["sofifa_id"] in both

    response = cup.post("call-up", {"squad": "brazil", "players": both})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_CALL_UP"
    assert "same person" in response.get_json()["error"]["message"]


def test_a_reseed_ends_the_sessions_created_on_the_old_catalogue(tmp_path, csv_file, rows):
    db = mock_mongo_db()
    seed_catalog(db, parse_catalog(csv_file, QUOTAS))
    client = seeded_client(db)
    cup = Cup(client, squad="peru")
    cup.start()
    row_of(rows, "peru")["overall"] = 80
    seed_catalog(db, parse_catalog(write_catalogue(tmp_path / "v2.csv", rows), QUOTAS))

    for method, path in (
        ("get", f"/session/{cup.id}"),
        ("post", f"/{cup.id}/call-up"),
        ("get", f"/{cup.id}/draw"),
        ("get", f"/{cup.id}/available-players"),
        ("post", f"/{cup.id}/simulate"),
        ("get", f"/{cup.id}/round-results"),
        ("get", f"/{cup.id}/playoffs-draw"),
        ("post", f"/{cup.id}/simulate-all"),
        ("get", f"/{cup.id}/history"),
    ):
        kwargs = {"json": {"squad": "peru", "players": [1] * 26}} if path.endswith("call-up") else {}
        if path.endswith("/simulate"):
            kwargs = {"json": {"players": list(range(1, 12))}}
        response = getattr(client, method)(path, **kwargs)
        assert (response.status_code, response.get_json()["error"]["code"]) == (409, "CATALOG_CHANGED"), path

    assert Cup(client, squad="peru").start()  # a new session works on the new catalogue
