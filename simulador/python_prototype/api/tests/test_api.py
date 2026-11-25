"""Testes de API (Issue #41). Rode de `simulador/`: python -m pytest api"""
import pytest
from fastapi.testclient import TestClient

from api.catalog import Catalog
from api.main import create_app
from api.settings import Settings
from api.store import GameStore
from simulador.python_prototype.cards import CardConfig
from python_prototype.tournament import (
    DEFAULT_NATIONS, SquadMember, TournamentConfig, uniform_player,
)

LAYOUT = ["RB", "CB", "CB", "LB", "CB", "RB", "CM", "CDM", "CAM", "CM", "ST", "LW",
          "RW", "CF", "ST", "LW", "RW", "CM", "CB", "LB", "CM", "ST", "CB", "CDM"]
USER = "Brazil"


def members(index, nation):
    base = 60 + 2 * index
    gks = [SquadMember(uniform_player(f"{nation} GK{i}", "GK", base - i), ("GK",)) for i in range(4)]
    out = [SquadMember(uniform_player(f"{nation} {i:02d}", pos, base - 3 - i % 7), (pos,))
           for i, pos in enumerate(LAYOUT)]
    return gks + out


@pytest.fixture(scope="module")
def catalog():
    return Catalog.from_members({n: members(i, n) for i, n in enumerate(DEFAULT_NATIONS)})


def make_client(catalog, no_red=True, **kw):
    cards = CardConfig(0.35, 0.0) if no_red else CardConfig(0.0, 1.0)
    app = create_app(catalog, Settings(), config_overrides={"cards": cards}, **kw)
    return TestClient(app)


def squad(nation=USER):
    return [f"{nation} GK{i}" for i in range(3)] + [f"{nation} {i:02d}" for i in range(20)]


def new_game(client, seed=2026, **body):
    r = client.post("/v1/games", json={"user_team": USER, "squad": squad(), "seed": seed, **body})
    assert r.status_code == 201, r.text
    return r.json()["game_id"]


def play_user(client, gid, halftime=False):
    played = 0
    while True:
        adv = client.post(f"/v1/games/{gid}/advance")
        assert adv.status_code == 200, adv.text
        if adv.json()["pending_match"] is None:
            break
        assert client.post(f"/v1/games/{gid}/match/start", json={}).status_code == 200
        if halftime:
            r = client.post(f"/v1/games/{gid}/match/play", json={"until": "halftime"}).json()
            assert r["phase"] == "HALFTIME" and not r["finished"]
            assert client.post(f"/v1/games/{gid}/match/second-half").status_code == 200
        r = client.post(f"/v1/games/{gid}/match/play", json={"until": "end"}).json()
        assert r["finished"] and r["view"] is not None
        played += 1
    if not client.get(f"/v1/games/{gid}").json()["is_finished"]:
        assert client.post(f"/v1/games/{gid}/simulate").status_code == 200
    return played


def test_nations_and_pool(catalog):
    c = make_client(catalog)
    nations = c.get("/v1/nations").json()
    assert len(nations) == 16 and {n["name"] for n in nations} == set(DEFAULT_NATIONS)
    assert next(n for n in nations if n["name"] == "Brazil")["display_name"] == "Brasil"
    pool = c.get("/v1/nations/brazil/players").json()
    assert pool["rules"]["size"] == 23 and len(pool["players"]) == 28
    assert c.get("/v1/nations/atlantis/players").json()["code"] == "nation_not_found"


@pytest.mark.parametrize("mutate", [
    lambda s: s[:-1],                                            # 22
    lambda s: s + [f"{USER} 20"],                                # 24
    lambda s: s[:-1] + [s[0]],                                   # repetido
    lambda s: s[:-1] + ["Ninguém"],                              # fora do pool
    lambda s: s[:2] + [f"{USER} 20"] + s[3:],                    # 2 goleiros
])
def test_invalid_squad_is_rejected(catalog, mutate):
    c = make_client(catalog)
    r = c.post("/v1/games", json={"user_team": USER, "squad": mutate(squad()), "seed": 1})
    assert r.status_code == 422 and r.json()["code"] in ("invalid_squad", "setup_error")


def test_full_tournament_and_reproducibility(catalog):
    c = make_client(catalog)
    results = []
    for _ in range(2):
        gid = new_game(c, seed=11)
        play_user(c, gid, halftime=True)
        results.append(c.get(f"/v1/games/{gid}/result").json())
    assert results[0] == results[1]
    res = results[0]
    assert len(res["group_matches"]) == 24 and len(res["knockout"]) == 8
    assert res["user_team"] == USER


def test_result_requires_finished_tournament_and_errors_are_coded(catalog):
    c = make_client(catalog)
    gid = new_game(c)
    r = c.get(f"/v1/games/{gid}/result")
    assert r.status_code == 409 and r.json()["code"] == "tournament_not_finished"
    assert c.post(f"/v1/games/{gid}/simulate").json()["code"] == "user_match_pending"
    assert c.post(f"/v1/games/{gid}/match/play", json={"until": "end"}).json()["code"] == "no_active_match"
    assert c.get("/v1/games/inexistente").json()["code"] == "game_not_found"


def test_view_is_consistent_with_match(catalog):
    c = make_client(catalog)
    gid = new_game(c)
    c.post(f"/v1/games/{gid}/advance")
    c.post(f"/v1/games/{gid}/match/start", json={})
    play = c.post(f"/v1/games/{gid}/match/play", json={"until": "end"}).json()
    mid = play["match_id"]
    view = c.get(f"/v1/games/{gid}/matches/{mid}").json()
    assert view == play["view"]
    goals = [e for e in view["timeline"] if e["type"] == "GOAL"]
    assert len(goals) == sum(view["score"].values())
    assert [e["minute"] for e in view["timeline"]] == sorted(e["minute"] for e in view["timeline"])
    assert all(e["type"] not in ("LESAO", "FALTA") for e in view["timeline"])
    # partida de máquina também tem view
    other = next(m for m in c.get(f"/v1/games/{gid}").json()["groups"][0]["matches"] if m["status"] == "ENCERRADA")
    assert c.get(f"/v1/games/{gid}/matches/{other['id']}").status_code == 200
    assert c.get(f"/v1/games/{gid}/matches/QF1").json()["code"] == "match_not_played"


def test_lineup_changes_only_before_start_and_at_halftime(catalog):
    c = make_client(catalog)
    gid = new_game(c)
    c.post(f"/v1/games/{gid}/advance")
    assert c.post(f"/v1/games/{gid}/match/start", json={}).status_code == 200
    state = c.get(f"/v1/games/{gid}").json()["active_match"]
    picks = state["lineup"]
    assert c.post(f"/v1/games/{gid}/match/lineup", json={"picks": picks}).status_code == 200
    c.post(f"/v1/games/{gid}/match/play", json={"until": "halftime"})
    assert c.post(f"/v1/games/{gid}/match/lineup", json={"picks": picks}).status_code == 200
    c.post(f"/v1/games/{gid}/match/second-half")
    r = c.post(f"/v1/games/{gid}/match/lineup", json={"picks": picks})
    assert r.status_code == 422
    bad = c.post(f"/v1/games/{gid}/match/lineup", json={"picks": picks[:-1]})
    assert bad.status_code == 422
    # cancelar mantém a partida pendente
    assert c.delete(f"/v1/games/{gid}/match").json()["pending_user_match"] is not None


def test_red_card_suspends_player_for_next_user_match_only(catalog):
    c = make_client(catalog, no_red=False)
    for seed in range(40):
        gid = new_game(c, seed=seed)
        c.post(f"/v1/games/{gid}/advance")
        c.post(f"/v1/games/{gid}/match/start", json={})
        play = c.post(f"/v1/games/{gid}/match/play", json={"until": "end"}).json()
        view = play["view"]
        side = "A" if view["team_a"] == USER else "B"
        reds = {e["player"] for e in view["timeline"] if e["type"] == "CARTAO_VERMELHO" and e["team"] == side}
        if not reds:
            continue
        assert set(play["suspended"]) == reds
        assert c.post(f"/v1/games/{gid}/advance").json()["pending_match"] is not None
        before = c.get(f"/v1/games/{gid}").json()
        r = c.post(f"/v1/games/{gid}/match/start", json={})
        assert r.status_code == 422 and r.json()["code"] == "suspended_player"
        assert c.get(f"/v1/games/{gid}").json() == before      # estado intacto
        return
    pytest.fail("nenhuma seed produziu vermelho do usuário")


def test_games_expire_after_ttl(catalog):
    now = [0.0]
    app = create_app(catalog, Settings(game_ttl_seconds=10), clock=lambda: now[0])
    c = TestClient(app)
    gid = new_game(c)
    now[0] = 5
    assert c.get(f"/v1/games/{gid}").status_code == 200
    now[0] = 100
    assert c.get(f"/v1/games/{gid}").json()["code"] == "game_not_found"


def test_store_rejects_when_full(catalog):
    app = create_app(catalog, Settings(max_games=1))
    c = TestClient(app)
    new_game(c)
    r = c.post("/v1/games", json={"user_team": USER, "squad": squad(), "seed": 2})
    assert r.status_code == 503 and r.json()["code"] == "server_busy"
