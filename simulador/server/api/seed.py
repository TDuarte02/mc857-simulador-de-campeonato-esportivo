"""Loads the real catalogue into MongoDB, offline: the data pipeline's players CSV -> squads and players.

    python -m api.seed --file ../../pipeline-dados/artefatos/jogadores_copa_america_2024_filtrado.csv

The connection comes from MONGO_URI and MONGO_DB, as for the API.

Each row is parsed with the engine's rules (see `parse_row`). The file is refused
as a whole, with a line / name / reason report, on a duplicate id, a missing or
out-of-range engine field, an unknown nation, or a squad without enough distinct
people for a call-up (3 GK, 8 DEF, 8 MID, 7 FW; two versions of a person count once).

Writing never leaves a half-loaded catalogue: everything goes to `squads_new` and
`players_new`, which then replace `squads` and `players` with a rename. The
`catalog_meta` document records the file's hash; seeding the same file again is a
no-op, and a different file changes the catalogue version, which ends the sessions
created on the old one (409 CATALOG_CHANGED).
"""

import argparse
import csv
import hashlib
import io
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pymongo import MongoClient
from pymongo.database import Database

from api.config import Settings
from api.domain.engine_data import ATTRIBUTE_MAX, ENGINE_ATTRIBUTES, LINE_ATTRIBUTES, canonical_position, sector_of
from api.domain.models import Player, Position, Squad
from api.repositories.mongo import CATALOG_META_ID, PLAYER_INDEX, player_doc, squad_doc
from api.repositories.nations import BY_DATASET_NAME, NATIONS

# The engine reads these as floats; every other engine field is an integer.
_FLOAT_FIELDS = set(LINE_ATTRIBUTES)
_REQUIRED_COLUMNS = ("sofifa_id", "nationality_name", "player_positions", "age", *ENGINE_ATTRIBUTES)
_TRUE = {"true", "1", "1.0", "yes"}


@dataclass(frozen=True)
class Problem:
    line: int | None  # None for a problem with a whole squad
    name: str
    reason: str

    def __str__(self) -> str:
        where = f"line {self.line}" if self.line is not None else "squad"
        return f"{where}: {self.name}: {self.reason}"


class SeedError(Exception):
    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__(f"{len(problems)} problem(s) in the catalogue file:\n" + "\n".join(f"  {p}" for p in problems))


class _RowError(Exception):
    pass


@dataclass(frozen=True)
class Catalog:
    squads: list[Squad]
    players: list[Player]
    sha256: str
    source: str = ""
    lines: dict[int, int] = field(default_factory=dict)  # player id -> line in the file

    @property
    def version(self) -> str:
        return self.sha256[:12]


# --- Parsing --------------------------------------------------------------------------


def _number(raw: str, name: str) -> float:
    try:
        value = float(raw)
    except ValueError:
        raise _RowError(f"{name} is not a number: {raw!r}") from None
    if not math.isfinite(value) or not 0 <= value <= ATTRIBUTE_MAX:
        raise _RowError(f"{name} is outside [0, {ATTRIBUTE_MAX}]: {raw!r}")
    return value


def _integer(raw: str, name: str) -> int:
    try:
        value = float(raw)
    except ValueError:
        raise _RowError(f"{name} is not a number: {raw!r}") from None
    if not value.is_integer():
        raise _RowError(f"{name} is not an integer: {raw!r}")
    return int(value)


def parse_row(row: Mapping[str, str | None]) -> Player:
    """One CSV row as a Player, by the rules of the engine's former dataset reader.

    - name: short_name, else long_name;
    - positions: the recognised codes, primary first; a goalkeeper is only a goalkeeper;
    - the 18 engine fields are required, in [0, 100]; a goalkeeper's empty outfield
      attributes become 0.
    """
    name = (row.get("short_name") or row.get("long_name") or "").strip()
    if not name:
        raise _RowError("empty name")
    nation = BY_DATASET_NAME.get((row.get("nationality_name") or "").strip())
    if nation is None:
        raise _RowError(f"unknown nation {row.get('nationality_name')!r}")
    player_id = _integer((row.get("sofifa_id") or "").strip(), "sofifa_id")

    recognised = []
    for raw in (row.get("player_positions") or "").split(","):
        raw = raw.strip()
        try:
            recognised.append((raw, canonical_position(raw)))
        except KeyError:
            continue  # unknown codes are ignored, as the engine does
    if not recognised:
        raise _RowError(f"no recognised position in {row.get('player_positions')!r}")
    goalkeeper = [raw for raw, canon in recognised if canon == "GK"]
    positions = (goalkeeper[0],) if goalkeeper else tuple(raw for raw, _ in recognised)

    attributes: dict[str, float] = {}
    for field_name in ENGINE_ATTRIBUTES:
        raw = (row.get(field_name) or "").strip()
        if raw == "":
            if field_name in LINE_ATTRIBUTES and goalkeeper:
                raw = "0"
            else:
                raise _RowError(f"missing engine field {field_name}")
        if field_name in _FLOAT_FIELDS:
            attributes[field_name] = _number(raw, field_name)
        else:
            attributes[field_name] = _integer(raw, field_name)
            _number(raw, field_name)

    age = (row.get("age") or "").strip()
    if not age:
        raise _RowError("missing age")
    return Player(
        id=player_id,
        squad_id=nation.id,
        name=name,
        age=_integer(age, "age"),
        position=sector_of(positions[0]),
        overall=int(attributes["overall"]),
        is_current=(row.get("is_convocado_2024") or "").strip().lower() in _TRUE,
        is_legend=(row.get("camada") or "").strip() == "historico",
        positions=positions,
        attributes=attributes,
        person_key=(row.get("person_key") or "").strip() or str(player_id),
    )


def parse_catalog(path: Path, quotas: Mapping[Position, int]) -> Catalog:
    """The whole file, or SeedError listing every problem found."""
    data = Path(path).read_bytes()
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    header = set(reader.fieldnames or [])
    missing = [c for c in _REQUIRED_COLUMNS if c not in header]
    if not header & {"short_name", "long_name"}:
        missing.append("short_name/long_name")
    if missing:
        raise SeedError([Problem(1, "header", f"missing columns {missing}")])

    problems: list[Problem] = []
    players: list[Player] = []
    lines: dict[int, int] = {}
    for row in reader:
        name = (row.get("short_name") or row.get("long_name") or "").strip() or "?"
        try:
            player = parse_row(row)
        except _RowError as error:
            problems.append(Problem(reader.line_num, name, str(error)))
            continue
        if player.id in lines:
            problems.append(Problem(reader.line_num, name, f"duplicate id {player.id} (also on line {lines[player.id]})"))
            continue
        lines[player.id] = reader.line_num
        players.append(player)

    people: dict[tuple[str, Position], set[str]] = defaultdict(set)
    for player in players:
        people[player.squad_id, player.position].add(player.person)
    for nation in NATIONS:
        for position, quota in quotas.items():
            found = len(people[nation.id, position])
            if found < quota:
                problems.append(
                    Problem(None, nation.id, f"{found} distinct people at {position}, a call-up needs {quota}")
                )
    if problems:
        raise SeedError(problems)

    squads = [Squad(n.id, n.name, n.flag, n.federation) for n in NATIONS]
    return Catalog(squads, players, hashlib.sha256(data).hexdigest(), str(path), lines)


# --- Writing ----------------------------------------------------------------------------


def seed_catalog(db: Database, catalog: Catalog, now: datetime | None = None) -> bool:
    """Replaces the catalogue with `catalog`. False, and nothing written, if it is already the one in use."""
    meta = db.catalog_meta.find_one({"_id": CATALOG_META_ID})
    if meta is not None and meta.get("source_sha256") == catalog.sha256:
        return False

    db.squads_new.drop()
    db.players_new.drop()
    db.squads_new.insert_many([squad_doc(squad) for squad in catalog.squads])
    db.players_new.insert_many([player_doc(player) for player in catalog.players])
    db.players_new.create_index(PLAYER_INDEX)
    db.squads_new.rename("squads", dropTarget=True)
    db.players_new.rename("players", dropTarget=True)
    db.catalog_meta.replace_one(
        {"_id": CATALOG_META_ID},
        {
            "_id": CATALOG_META_ID,
            "version": catalog.version,
            "source_sha256": catalog.sha256,
            "source": Path(catalog.source).name,
            "seeded_at": now or datetime.now(UTC),
            "players": len(catalog.players),
        },
        upsert=True,
    )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m api.seed", description=__doc__.splitlines()[0])
    parser.add_argument("--file", type=Path, required=True, help="players CSV written by the data pipeline")
    args = parser.parse_args(argv)
    settings = Settings.from_env()

    try:
        catalog = parse_catalog(args.file, settings.squad_quotas)
    except SeedError as error:
        print(error, file=sys.stderr)
        return 1

    client = MongoClient(settings.mongo_uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    try:
        changed = seed_catalog(client[settings.mongo_db], catalog)
    finally:
        client.close()
    per_squad = Counter(player.squad_id for player in catalog.players)
    state = "seeded" if changed else "already seeded, nothing to do"
    print(
        f"catalogue {catalog.version} ({args.file.name}): {state}; "
        f"{len(catalog.squads)} squads, {len(catalog.players)} players "
        f"({min(per_squad.values())}-{max(per_squad.values())} per squad)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
