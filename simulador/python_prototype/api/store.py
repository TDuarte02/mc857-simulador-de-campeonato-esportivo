"""Sessões em memória com TTL e lock por jogo."""
from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from python_prototype.game import TournamentGame
from python_prototype.match import MatchEvent
from simulador.python_prototype.match_view import MatchLineups

from .errors import ApiError


class GameSession:
    def __init__(self, game_id: str, game: TournamentGame, seed: int, now: float) -> None:
        self.game_id = game_id
        self.game = game
        self.seed = seed
        self.lock = threading.RLock()
        self.suspended: set[str] = set()          # só valem para a próxima partida do usuário
        self.lineups: dict[str, MatchLineups] = {}
        self.cards: dict[str, tuple[MatchEvent, ...]] = {}
        self.first_half: dict | None = None       # escalação do 1º tempo da partida em curso
        self.touched = now


class GameStore:
    def __init__(
        self,
        ttl_seconds: float = 3600.0,
        max_games: int = 1000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl, self._max, self._clock = ttl_seconds, max_games, clock
        self._games: dict[str, GameSession] = {}
        self._guard = threading.Lock()

    def _purge(self) -> None:
        now = self._clock()
        for key in [k for k, g in self._games.items() if now - g.touched > self._ttl]:
            del self._games[key]

    def add(self, game: TournamentGame, seed: int) -> GameSession:
        with self._guard:
            self._purge()
            if len(self._games) >= self._max:
                raise ApiError(503, "server_busy", "Servidor no limite de torneios simultâneos.")
            gs = GameSession(uuid.uuid4().hex, game, seed, self._clock())
            self._games[gs.game_id] = gs
            return gs

    def get(self, game_id: str) -> GameSession:
        with self._guard:
            self._purge()
            gs = self._games.get(game_id)
            if gs is None:
                raise ApiError(404, "game_not_found", "Torneio não encontrado ou expirado.")
            gs.touched = self._clock()
            return gs

    @contextmanager
    def locked(self, game_id: str) -> Iterator[GameSession]:
        """Uma ação por vez por torneio."""
        gs = self.get(game_id)
        with gs.lock:
            try:
                yield gs
            finally:
                gs.touched = self._clock()
