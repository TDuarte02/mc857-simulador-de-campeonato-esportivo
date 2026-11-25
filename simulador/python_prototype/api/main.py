"""API HTTP (FastAPI) sobre TournamentGame / UserMatchSession."""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from python_prototype.game import UserMatchPending
from python_prototype.tournament import SetupError

from .catalog import Catalog
from .errors import ApiError
from .schemas import (
    ActiveMatch, AdvanceOut, CreateGameIn, CreateGameOut, GameState, LineupIn,
    MatchView, NationOut, PlayIn, PlayOut, PoolOut, StartMatchIn,
)
from .service import GameService
from .settings import Settings
from .store import GameStore


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


def create_app(
    catalog: Catalog | None = None,
    settings: Settings | None = None,
    clock=time.monotonic,
    config_overrides: dict[str, Any] | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    catalog = catalog or Catalog.from_csv(settings.dataset_path)   # uma vez, na inicialização
    store = GameStore(settings.game_ttl_seconds, settings.max_games, clock)
    service = GameService(catalog, store, config_overrides)

    app = FastAPI(title="Copa América API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins),
        allow_methods=["*"], allow_headers=["*"],
    )
    app.state.service = service

    @app.exception_handler(ApiError)
    async def _api_error(_, exc: ApiError):
        return _error(exc.status, exc.code, exc.message)

    @app.exception_handler(UserMatchPending)
    async def _pending(_, exc: UserMatchPending):
        return _error(409, "user_match_pending", str(exc))

    @app.exception_handler(SetupError)
    async def _setup(_, exc: SetupError):
        return _error(422, "setup_error", str(exc))

    @app.exception_handler(ValueError)
    async def _rule(_, exc: ValueError):
        return _error(422, "rule_violation", str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation(_, exc: RequestValidationError):
        return _error(422, "validation_error", str(exc.errors()))

    r = APIRouter(prefix="/v1")

    @r.get("/nations", response_model=list[NationOut])
    def nations():
        return catalog.nations()

    @r.get("/nations/{nation}/players", response_model=PoolOut)
    def players(nation: str):
        name = catalog.resolve_nation(nation)
        return {"nation": name, "rules": catalog.rules(),
                "players": [catalog.player_out(m) for m in catalog.pools[name]]}

    @r.post("/games", response_model=CreateGameOut, status_code=201)
    def create_game(body: CreateGameIn):
        gs = service.create_game(body.user_team, body.squad, body.seed)
        with store.locked(gs.game_id):
            return {"game_id": gs.game_id, "seed": gs.seed, "state": service.state(gs)}

    @r.get("/games/{game_id}", response_model=GameState)
    def get_game(game_id: str):
        with store.locked(game_id) as gs:
            return service.state(gs)

    @r.post("/games/{game_id}/advance", response_model=AdvanceOut)
    def advance(game_id: str):
        with store.locked(game_id) as gs:
            return service.advance(gs)

    @r.post("/games/{game_id}/match/start", response_model=ActiveMatch)
    def start(game_id: str, body: StartMatchIn | None = None):
        with store.locked(game_id) as gs:
            return service.start_match(gs, body.picks if body else None)

    @r.post("/games/{game_id}/match/lineup", response_model=ActiveMatch)
    def lineup(game_id: str, body: LineupIn):
        with store.locked(game_id) as gs:
            return service.change_lineup(gs, body.picks, body.formation)

    @r.post("/games/{game_id}/match/play", response_model=PlayOut)
    def play(game_id: str, body: PlayIn):
        with store.locked(game_id) as gs:
            return service.play(gs, body.until)

    @r.post("/games/{game_id}/match/second-half", response_model=ActiveMatch)
    def second_half(game_id: str):
        with store.locked(game_id) as gs:
            return service.second_half(gs)

    @r.delete("/games/{game_id}/match", response_model=GameState)
    def cancel(game_id: str):
        with store.locked(game_id) as gs:
            return service.cancel(gs)

    @r.post("/games/{game_id}/simulate", response_model=GameState)
    def simulate(game_id: str):
        with store.locked(game_id) as gs:
            return service.simulate(gs)

    @r.get("/games/{game_id}/result", response_model=dict[str, Any])
    def result(game_id: str):
        with store.locked(game_id) as gs:
            if not gs.game.is_finished:
                raise ApiError(409, "tournament_not_finished", "O torneio ainda não terminou.")
            return gs.game.final_result()

    @r.get("/games/{game_id}/matches/{match_id}", response_model=MatchView)
    def match(game_id: str, match_id: str):
        with store.locked(game_id) as gs:
            return service.match_view(gs, match_id)

    app.include_router(r)
    return app
