# Plan: clean up `python_prototype`, plug the engine into the server, load the real dataset into MongoDB

*Revision 3: incorporates the validator's 22 round-1 findings, its 12 round-2 findings (N1–N12), and the decisions below.*

## Context

`simulador/python_prototype` holds the match engine the server needs, plus things it shouldn't:
- a second backend (`api/`), already broken: its tests don't collect;
- a Kotlin HTTP client for that backend (`app/`);
- a whole tournament orchestrator (`game.py`, `session.py`, `knockout.py`, most of `group_stage.py`);
- CSV loading meant for runtime.

The server (`simulador/server`) owns sessions, Mongo persistence, the OpenAPI contract and the tournament flow, and today it simulates with a random mock.

**Goal:** a user can simulate a whole cup through the server, with the real engine and the real players loaded from Mongo. That means one stdlib-only engine package that only simulates, one backend that orchestrates and persists, and a catalogue seeded offline from the data pipeline's output.

## Decisions (product owner)

| # | Topic | Decision |
|---|---|---|
| D1 | Lineup | Keep `POST /simulate {players, formation?}`; the **server assigns slots**. |
| D2 | Draw / bracket | **Engine's**: pots seeded by strength; fixed bracket QF1=1A×2B, QF2=1B×2A, QF3=1D×2C, QF4=1C×2D. `playoffs-draw` reveals it. |
| D3 | Suspensions | Red = 1 match, 2nd accumulated yellow = 1 match, injury = N matches (N from the match seed). |
| D4 | Dataset | Fix the pipeline so real 2024 call-ups are always kept; seed Mongo from the regenerated file. |
| D5 | Missing engine attributes | **Regression on the FIFA 22 base**, in the pipeline, flagged as estimated. |
| D6 | No fit goalkeeper | **An outfield player goes in goal**; the session always continues. |
| D7 | App ↔ server | **Separate follow-up**; this plan ends with a documented API on real data and lists what the app must use. |
| D8 | Same person twice | **One version per person** in a call-up and in presets. |
| D9 | Default formation | `4-4-2` when the client sends none (the app's default). Machine teams keep the engine's `4-3-3`. |
| D10 | Squad ids | Pinned table: `canada` added, `haiti` removed, **`usa` kept** (not `united_states`), all others as today. |

## Findings that shape the plan

### Engine
- 1,526 engine tests pass, with golden-seed characterization. Pure stdlib; a whole cup runs in ~31 ms.
- **Two import roots.** `python_prototype.*` and `simulador.python_prototype.*` (7 imports in 5 files, including `tests/test_cards.py` and `tests/test_match_view.py`). Two copies of `match.py` mean two `MatchEventType` enums, and the engine compares them with `is`: events would silently disappear.
- **The engine yields a possession log, not a football result.**
  - Scorers come from `match_view._pick_scorer` and minutes from `match_view.display_minute` (seeded).
  - Cards come from `cards.derive_cards`, called only from `api/service.py`.
  - Injuries (`LESAO`) have no duration and can hit the goalkeeper.
  - Red cards and injuries don't remove the player from the pitch during that match.
  - `derive_cards` emits the 1st yellow and then a RED for a second yellow.
- **There is no "weaker" model.** The other teams' matches use the same engine, at ~1 ms per match.
- The engine requires exactly one GK slot (`validate_lineup_matches_formation`, `penalties.goalkeeper_of`).

### Data (`jogadores_copa_america_2024_filtrado.csv`, 756 rows)

| Problem | Evidence | Fix (phase 2) |
|---|---|---|
| **9 engine attributes empty** in all 639 legend and researched rows (`attacking_heading_accuracy`, `movement_agility/reactions/balance`, `power_jumping/stamina`, `mentality_aggression/penalties/composure`), plus `goalkeeping_reflexes` for outfield players | only the 117 FIFA 22 rows are complete | regression (D5) |
| Most real call-ups dropped (Argentina: 3, no Messi) | the filter always keeps enriched players, and the quota is only a floor | always keep call-ups |
| 15 ids shared by a person's 2024 and legend versions | `alocar_id` keys on (country, name, date of birth) | the key includes the layer; legend versions get new ids |
| Call-up matching: 15 ambiguous (2024 vs legend), 1 miss (Andrés Cubas) | `identity.py:72-76` returns the empty filtered exact match without trying the token fallback | matching rules below |
| Jamaica and Panama list **25** call-ups | `convocacoes/*.csv` | check "all listed present", not "26" |
| Ecuador, Uruguay, Venezuela and Panama have only 3 forwards among the call-ups | primary positions | check quotas on the whole catalogue (call-ups + legends + base) |
| Ids not reproducible from a clean clone | the registry doesn't exist locally (only `.gitkeep`) and both registry paths are gitignored; without it `alocar_id` restarts at -1 | rebuild it from the ids in the artefacts, then commit it |
| Legends have `age = 27`; GKs have empty outfield attributes | pipeline conventions | carried as they are (GK outfield attributes → 0) |

### Repo hygiene
- **Tracked build artifacts:** root `app/.gradle/**`, `app/build/reports/**` and `.coverage` are tracked (`.coverage` despite `.gitignore`).
- **Local leftovers:** root `server/` holds only caches.
- **Misplaced root files:** root `requirements.txt` belongs to `pipeline-dados`; the root `pytest.ini` has `pythonpath = . simulador pipeline-dados`.
- **Golden test flag:** `test_characterization.py` hard-codes `UPDATE_GOLDEN = 0`, but its docstring says to set the env var.

## Target layout

```
simulador/
  engine/                         # stdlib only, installable
    pyproject.toml                # pytest config: pythonpath ["."]; pytest as dev dependency
    copa_engine/
      __init__.py
      common.py control.py dispute.py attack.py dynamics.py
      collective_attributes.py match.py penalties.py cards.py
      config.py      # EngineConfig: attack, recovery bonus, possessions, dynamics, penalties, cards
      derive.py      # pick_scorer, display_minute, derive_cards wrapper, injury duration
      rules.py       # derive_seed, draw_groups, GROUP_ROUNDS, compute_standings, KNOCKOUT_BRACKET
      lineup.py      # default_lineup, assign_slots (matching), covers_sectors, FORMATIONS
      testing.py     # synthetic_team(s), importable by the server's tests until phase 5
    tests/                        # match-level tests + golden match seeds; import `tests.helpers`
    tools/compare_dynamics.py     # calibration CLI, not shipped
  server/
    api/simulation/engine.py      # EngineMatchSimulator (domain <-> copa_engine)
    api/seed.py                   # offline CLI: pipeline CSV -> Mongo catalogue
    api/repositories/nations.py   # pinned squad table (from api/names.py)
```

`rules.draw_groups` takes any objects with `name` and `strength` (a `Protocol`), so it no longer depends on `NationalTeam`.

## Inventory

| Path | Action | When | Notes |
|---|---|---|---|
| `api/names.py` | port → `server/api/repositories/nations.py` | phase 1 | apply D10 ids |
| `api/catalog.covers_sectors` | port → `copa_engine/lineup.py` | phase 1 | |
| `api/service._finalize` | logic documented here, implemented in the adapter | phase 4 | constant lineups → `derive_cards` → red-card suspension |
| `python_prototype/api/`, `app/`, `Dockerfile` | **delete** | phase 1, after the two ports above | |
| `match_view.py` | slim → `derive.py` | phase 1 | drop the dict/stat building |
| `tournament.py` | split | phase 1 | `derive_seed`, `draw_groups` → `rules.py`; `build_default_lineup` → `lineup.py`; model params → `config.py`; `_parse_row` rules → `server/api/seed.py` (phase 3, switched to import `copa_engine` in phase 4); `synthetic_team(s)` → `copa_engine/testing.py` (inside the package, so the server's cross-check can import it) |
| `group_stage.py` | split | phase 1 | `GROUP_ROUNDS`, `compute_standings`, `KNOCKOUT_BRACKET` → `rules.py` |
| `game.py`, `session.py`, `knockout.py`, `tournament.py`, `group_stage.py` (what's left after phase 1: state classes, `TournamentConfig`, `NationalTeam`, `build_squad`, `build_national_team`, CSV reading), `testing.py` | **delete** | phase 5, after the cross-check | with their tests: `test_game.py`, `test_knockout.py`, `test_tournament_characterization.py`, `golden/tournament_seeds.json`, and the parts of `test_tournament.py`/`test_group_stage.py` that test deleted code |
| `compare_dynamics.py` | move → `engine/tools/` | phase 1 | |
| `server/.../mock_data.py` | keep for tests/dev; **generate `positions` + the 18 attributes** | phase 3 | so the engine runs on mock data |
| `server/.../domain/rules.py` | shrink | phase 4 | `round_robin`, `compute_standings`, `best_lineup` replaced by the engine's; `apply_match_events` stays |
| `server/.../simulation/mock.py` | keep as `SIMULATOR=mock` | — | |
| root build artifacts | untrack + `.gitignore` | phase 0 | |

In phase 1 the old modules **re-export** from the new ones (`from copa_engine.rules import compute_standings`), so `game.py`/`session.py` and the golden files keep working until phase 5.

## Phases

Each phase is one PR. All suites stay green at the end of each, including Docker and the functional tests.

### Phase 0: hygiene
1. `git rm --cached` root `app/.gradle`, `app/build`, `.coverage`; extend `.gitignore`; delete the local root `server/`.
2. Move root `requirements.txt` into `pipeline-dados/`.
3. `UPDATE_GOLDEN` reads the env var.

### Phase 1: engine package, no behaviour change
The server's code is not changed; it only gains one data file (`nations.py`) that phase 3 starts using.

1. Exact moves (`git mv` does not create missing parent folders; verified):
   ```
   mkdir -p simulador/engine/tools
   git mv simulador/python_prototype/tests  simulador/engine/tests
   git mv simulador/python_prototype/compare_dynamics.py  simulador/engine/tools/compare_dynamics.py
   git mv simulador/python_prototype  simulador/engine/copa_engine
   ```
2. **Imports:**
   - One import root (`copa_engine.*`) everywhere, including the 2 test files.
   - Add `copa_engine/__init__.py`; the folders are namespace packages today.
   - Tests import their helpers as `tests.helpers` (was `python_prototype.tests.helpers`).
3. **`engine/pyproject.toml`:** no runtime dependencies; pytest as a dev dependency; `[tool.pytest.ini_options] pythonpath = ["."]`. The root `pytest.ini` drops `simulador` (→ `pythonpath = . pipeline-dados`); the engine tests run from their own folder.
4. Create `config.py`, `rules.py`, `lineup.py`, `derive.py` and `testing.py` (moving code); the old modules re-export.
5. Port `names.py` → `server/api/repositories/nations.py` and `covers_sectors` → `lineup.py`; then delete `api/`, `app/` and `Dockerfile`.
6. **Gate:** `cd simulador/engine && uv run pytest` green; `git diff simulador/engine/tests/golden` empty. The phase 6 hook uses the same command.

### Phase 2: dataset (pipeline-dados)
1. **Call-up matching** (`identity.py`):
   - exclude `historico` rows;
   - prefer `convocado_2024` over `base_22`;
   - if exact matching plus the date-of-birth filter returns nothing, fall back to token matching;
   - any call-up still ambiguous or missing **fails** the run with a report.
2. **Filter** (`filtro.py`): matched call-ups are always kept. New columns:
   - `is_convocado_2024`;
   - `person_key`, shared by the 2024 and legend versions of a person (D8).
3. **Ids**, in this order:
   1. Rebuild `artefatos/autoresearch/registry/player_ids.csv` from the ids already in the artefacts, with the layer in the key. Today it doesn't exist locally, and without it `alocar_id` restarts at -1.
   2. Remove both registry paths from `.gitignore` and commit the file.
   3. Only then give the 15 legend duplicates new ids.
4. **Imputation (D5):**
   - For each missing engine attribute, fit a regression on the complete FIFA 22 rows. Features: the 6 main attributes, overall and position group (outfield) or the GK attributes (keepers). The same technique `posicoes.py` uses.
   - Imputed values are rounded, clamped to [0, 99], and the row gets `atributos_imputados` (the list of imputed fields).
   - Report the error per attribute on a held-out split in the PR, as `posicoes.py` does (15k/4k).
5. **New validations (`validation.py`):**
   - every row has all 18 engine fields in [0, 100];
   - ids are unique;
   - each nation's catalogue has ≥ 3 GK / 8 DEF / 8 MID / 7 FW by primary sector, counting **distinct `person_key`s**, not rows (D8: two versions of a person count once);
   - every listed call-up is present (Jamaica and Panama: 25).
6. Regenerate `jogadores_copa_america_2024_filtrado.csv`; the PR lists per-nation counts and imputation errors.

### Phase 3: real catalogue in Mongo (server; engine not yet a dependency)
1. **Player model:** adds `positions` (dataset codes), `attributes` (the 18 engine fields), `is_current`, `is_legend`, `person_key`.
   - `position` (GK/DEF/MID/FW) stays = sector of the primary position, so the 3/8/8/7 quotas keep working.
   - Engine sectors: CDM/CM/CAM/LM/RM → MID; LW/RW/ST/CF → FW; CB/LB/RB/LWB/RWB → DEF.
2. **`mock_data`** generates positions + attributes (deterministic, from the synthetic-team logic).
3. **`python -m api.seed --file <csv>`:**
   - Parses with the engine's rules.
   - Fails with a line/name/reason report on: duplicate ids, missing engine fields, unknown nation, quota per position not met (counting distinct `person_key`s).
   - Writes `players_new`/`squads_new`, creates their indexes, then `rename(dropTarget=True)` (verified on mongomock).
   - `catalog_meta {version, source_sha256, seeded_at}`; the same file twice is a no-op.
4. **Squads:** the pinned table (D10) with Portuguese names, `flagcdn.com` URLs and federations.
5. **Call-up validation (D8):** rejects two players sharing a `person_key` (`INVALID_CALL_UP`). Presets skip a second version of a person.
6. **Presets:**
   - `current` = call-ups first, completed by overall to fit 3/8/8/7. Some real call-ups can be left out; the preset description says so.
   - `legends` = legends first by overall, completed by overall to fit 3/8/8/7.
   - `random` = shuffled with a generator passed in: the session's (see phase 4.3) when building an opponent's squad, the shared one for `GET /{squad}/presets`.
7. **No silent mock in production.** `SEED_MOCK_CATALOG` (default off; on in tests/dev). With an empty catalogue and the flag off, the API exits with a clear message.
8. **Sessions pin `catalog_version`.** On mismatch, `409 CATALOG_CHANGED` on every session endpoint.
9. **OpenAPI:** `positions`, `CATALOG_CHANGED` on every session endpoint, the person rule in the `INVALID_CALL_UP` description.
10. **Compose:** a one-shot `seed` service mounting `pipeline-dados/artefatos` read-only. `api` depends on it with `condition: service_completed_successfully`, so a fresh `docker compose up` seeds first and re-seeding is a no-op. This removes the API restart loop.
11. **Functional tests:** real-data assertions (Messi in Argentina, Canada present, 16 nations) are skipped when `catalog_meta` is absent.

### Phase 4: the engine becomes the server's simulator
1. **Dependency and Docker in the same PR:**
   - `uv add --editable ../engine`;
   - compose build context `simulador/`;
   - the Dockerfile copies only `engine/copa_engine`, `engine/pyproject.toml`, `server/main.py`, `server/api` and the server's `pyproject.toml`/`uv.lock`. Layer order: `engine/` (pyproject + package) must be copied **before** `uv sync`, because the editable `../engine` dependency is installed from source; the server's own code is copied after, as today;
   - `.dockerignore` excludes `app/`, `**/.venv`, `**/__pycache__`, `**/.pytest_cache`, `server/tests`, `engine/tests` and `engine/tools`.
   - The seed CLI and `mock_data` switch to importing the engine's position aliases and sectors (they were copied in phase 3). A test checks that the server's code-to-sector mapping equals `POSITION_SECTORS[canonical_position(code)]` for every code in the dataset.
2. **Activate it:** `SIMULATORS["engine"]` (its factory ignores the shared random generator); `SIMULATOR=engine` in the Dockerfile and compose. New `GET /meta` → `{simulator, catalogVersion}` (documented), so functional tests and operators can see what runs.
3. **Deterministic sessions:**
   - `POST /session` stores a **63-bit** seed (fits BSON int64), never exposed.
   - Every random choice derives from it. The engine's derivations must be reproduced **exactly**: any change, such as adding a `"match"` label, changes every result and breaks the phase 4.10 cross-check.

     | Draw | Derivation | Source |
     |---|---|---|
     | Match generator | `derive_seed(seed, match_id)`, **no label** | group_stage.py:265, session.py:170 |
     | Dynamics (fouls, injuries) | `derive_seed(seed, match_id, "dynamics")` | group_stage.py:270 |
     | Penalties | `derive_seed(seed, match_id, "penalties")` | knockout.py:63 |
     | Cards | `derive_seed(seed, match_id, "cards")` | api/service.py (being deleted) |
     | Scorers | `derive_seed(seed, match_id, "scorers")` | match_view.py |
     | Group tie-break | `derive_seed(seed, "tiebreak", group)` | group_stage.py:425 |
     | Group draw, per pot | `derive_seed(seed, "draw", pot)` | inside `draw_groups` |
     | Injury duration (new) | `derive_seed(seed, match_id, "injury", player_id)` | — |
     | Opponents' squad (new): which preset, **and** the shuffle of the `random` preset | one `Random(derive_seed(seed, "preset", squad_id))` used for both | — |

     `SquadService` gains a way to build a preset with a given generator; the session-less `GET /{squad}/presets` keeps the shared container generator.
4. **`MatchContext`** gains `seed`, `match_id`, and per-team players **with slots**.
5. **`EngineMatchSimulator`:**
   - Engine `Player.name = str(player_id)` (real names repeat inside a team; ids round-trip).
   - `create_match` + `play_match`; penalties if `needs_winner` and the score is level (lineups at full time).
   - Derivation: `derive_cards` (constant lineups), a scorer per goal, a display minute.
   - **Injury:** N = `1 + Random(derive_seed(seed, match_id, "injury", player_id)).randrange(3)`.
   - **Two yellows in one match:** the report keeps the yellow and the red. The domain `Card` gains `second_yellow: bool` (also in the Mongo card mapping and in the OpenAPI `Card` schema as `secondYellow`). `apply_match_events` does not count that player's yellow towards accumulation, since the red already suspends.
   - `simulate_quick` = the same engine, both teams with `lineup.default_lineup` in `4-3-3`.
   - In the user's matches **the opponent also plays its default lineup** (replaces `best_lineup`), so an opponent plays the same way in every match.
6. **Slot assignment (`lineup.assign_slots`, D1/D6/D9):**
   - Pinned slot lists (sector counts match the app's `MockFormations.kt`):
     - `4-4-2` = GK FB CB CB FB CM CM CM CM ST ST
     - `4-3-3` = GK FB CB CB FB CM CM CM ST W W (exactly the engine's `DEFAULT_FORMATION`; slot order decides who `derive_cards` books and the order `_pick_scorer` walks, so the user's 4-3-3 and the machine teams' must be the same list)
     - `3-5-2` = GK CB CB CB CM CM CM CM AM ST ST
     - `4-2-3-1` = GK FB CB CB FB DM DM AM AM AM ST
   - Default `4-4-2`; unknown formation → `400 INVALID_FORMATION`.
   - Goalkeeper: a fit goalkeeper in the XI goes to GK.
   - **No fit goalkeeper (D6):** the XI is 11 outfield players, and one of them plays GK with `pos="GK"`. The choice is part of the matching:
     - try the candidates in order of `goalkeeping_reflexes` (highest first, tie → lowest id);
     - take the first one whose removal leaves a valid placement for the other ten;
     - only if no candidate works, return 400.

     Documented for the client: in this case send ten players shaped like the formation plus one extra.
   - The engine accepts the stand-in (`validate_lineup_matches_formation`, `calculate_team_attributes` and `penalties.goalkeeper_of` all read `pos`). `derive_cards` and `_pick_scorer` skip the GK slot, so the stand-in can't be booked or score.
   - The existing `_validate_lineup` 0-GK rule stays. Tests: a whole session with all goalkeepers out, and a case where the highest-reflexes candidate doesn't fit but another does.
   - Outfield: exact position preferred, else the same sector, solved by **augmenting-path matching** (not the greedy `build_default_lineup`).
   - No valid placement → `400 LINEUP_DOES_NOT_FIT_FORMATION`, naming the players that don't fit.
   - The simulate response returns `match.lineup` (who played where).
   - The check runs in `MatchService` before any state change. The `conftest` helper picks an XI shaped like its formation (1 GK, 4 DEF, 4 MID, 2 FW).
7. **Draw and bracket (D2):**
   - `DrawService` uses `rules.draw_groups` (strength from each squad's default lineup) and `GROUP_ROUNDS`.
   - `playoffs-draw` fills `KNOCKOUT_BRACKET` from final standings; same route, response and idempotency.
8. **Standings:**
   - The engine's `compute_standings` (head-to-head, then a seeded draw) decides the **order only**.
   - It is called with **only played matches** and the **session seed** at every call site: `MatchService._complete_round`, `DrawService.playoffs_draw` / `ensure_playoffs`, `ResultsService.round_results` / `history`.
   - Squad ids replace names in the tie-break sort.
   - The engine's `StandingRow` has no cards, so the adapter still counts `yellowCards`/`redCards` from the played matches; the API and spec keep them.
9. **OpenAPI:** `match.lineup`, `Card.secondYellow`, `INVALID_FORMATION`, `LINEUP_DOES_NOT_FIT_FORMATION`, `/meta`.
10. **Cross-check before deleting the orchestrator:**
    - Test catalogue: `copa_engine.testing.synthetic_teams`, with squad id = engine name and each opponent's squad = its engine squad (injected through the repositories).
    - The engine's 23-player squads (3/8/6/6) can't pass `POST /call-up`'s 26 at 3/8/8/7, so the user's call-up is written through the repositories, not the API.
    - `build_container` gains an injectable session-seed factory, so the test can use seed 7 while the API never exposes it.
    - Every match not involving the user must equal `TournamentGame` with a user auto-playing (golden scenario `user_autoplay_seed_7`).
    - The user's matches run through the adapter with the engine's default slots.
    - Slot assignment is tested separately.
11. **Functional:** a test checks `GET /meta` says `engine`, and that goal minutes fall within the engine's cycles.

### Phase 5: remove the orchestrator from the engine
1. Delete `game.py`, `session.py`, `knockout.py`, `tournament.py`, `group_stage.py` and `testing.py` (every function still needed already lives in `rules.py`/`lineup.py`/`config.py` since phase 1), with `test_game.py`, `test_knockout.py`, `test_tournament_characterization.py`, `golden/tournament_seeds.json` and the phase 4 cross-check.
2. `test_tournament.py` and `test_group_stage.py`: keep only the tests of functions that now live in `rules.py`/`lineup.py` (draw, schedule, standings, bracket, default lineup), moved to `test_rules.py`/`test_lineup.py`; drop the rest.
3. Those tests need synthetic teams without `TournamentConfig`: rewrite `synthetic_team(s)` in `tests/helpers.py` to take the formation and squad shape as parameters and build the lineup with `lineup.default_lineup`, returning a small dataclass with `name`, `squad`, `lineup` and `strength` (what `rules.draw_groups` needs).

**Gate:** golden match seeds unchanged; server suite green.

### Phase 6: deployment and tooling
1. The pre-commit hook also runs the engine tests (`cd simulador/engine && uv run pytest`) when `simulador/engine/` is staged.
2. Functional tests on the stack seeded with the real file.
3. README: startup order (compose runs `seed` before `api` automatically), re-seeding, `GET /meta`.

## Behaviour changes for the app (follow-up, D7)

The app currently has no HTTP client. Its follow-up must use:
- **Squad ids:** `canada` instead of `haiti`; `usa` unchanged.
- **Players:** `positions`; legends are 27 years old by convention; one version per person in a call-up (`INVALID_CALL_UP`).
- **Lineup:** `formation` ∈ {4-4-2, 4-3-3, 3-5-2, 4-2-3-1} (default 4-4-2); errors `INVALID_FORMATION` and `LINEUP_DOES_NOT_FIT_FORMATION`; read `match.lineup` for who played where.
- **Standings:** show the server's order, without re-sorting by `standingComparator`. Tie-breaks are now head-to-head, then a seeded draw.
- **Playoffs:** the bracket follows group positions; `playoffs-draw` just reveals it.
- **Results:** minutes are approximate (inside a 15-minute block); a sent-off or injured player finishes that match.
- **Sessions:** `409 CATALOG_CHANGED` means the session predates a re-seed and can't continue.

## Risks and open points
- **Imputed attributes** for 639 players are estimates. Report the per-attribute error alongside the existing methodology caveat in `pipeline-dados/README.md`.
- **Score distribution:** `possessions_per_cycle = 1` means 6 possessions per match. Calibration is out of scope, but the functional tests log the average goals per match.
- **Tournament-level determinism:** after phase 5 the golden tournament files are gone, and server seeded tests are the tournament-level guard.
- **Data volume:** ~40 MB of CSVs in git; decide on LFS before regenerating more.

## Verification per phase
- **Phase 0/1:** engine suite green; golden files byte-identical; server untouched and green.
- **Phase 2:** pipeline tests, including the new validations (18 fields, unique ids, quotas, every call-up present) and matching cases (Turner, Isla, Cubas).
- **Phase 3:**
  - Seed tests: duplicate id rejected; missing field rejected; GK outfield attributes → 0; accents preserved; same file twice is a no-op; a failed seed leaves the old catalogue intact; indexes survive the swap.
  - Two versions of a person in a call-up are rejected.
  - Spec checks for the new fields.
  - Docker: `compose up` on an empty volume seeds, then serves.
- **Phase 4:**
  - Adapter: goals listed == score; scorers come from the lineup; minutes fall within their cycle; penalties only on knockout draws; injury N reproducible; the second-yellow rule.
  - Slot assignment: the case where greedy fails but matching succeeds; impossible → 400; all goalkeepers out → a session finishes; highest-reflexes stand-in doesn't fit but another does → 200.
  - Server sector mapping equals the engine's for every dataset position code.
  - Standings keep card counts; `secondYellow` round-trips through Mongo.
  - The cross-check.
  - The full flow on the real engine with a fixed seed.
  - Functional: `/meta` says engine.
- **Phase 5/6:** engine and server suites green; functional on the real-data stack.
