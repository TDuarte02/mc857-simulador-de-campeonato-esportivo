import random
from collections.abc import Callable

import pytest

from api import create_app
from api.container import build_container
from api.domain.models import Card, CardType, Goal, MatchResult, Position, Stage
from api.simulation.base import MatchContext, MatchSimulator

USER_SQUAD = "brazil"


class ScriptedSimulator(MatchSimulator):
    """Deterministic model: the user's results follow a script, every other match is a 1-0 home win.

    Plugging it in through build_container is the same swap the real model will use.
    """

    def __init__(self, user_wins: Callable[[Stage], bool] = lambda stage: True):
        self.user_wins = user_wins
        self.red_card_for: int | None = None  # sent off in the user's next match

    def simulate_match(self, context: MatchContext) -> MatchResult:
        user_is_home = context.home.squad_id == USER_SQUAD
        user, rival = (context.home, context.away) if user_is_home else (context.away, context.home)
        if self.user_wins(context.stage):
            scorer, goals = user, (2, 0) if user_is_home else (0, 2)
        else:
            scorer, goals = rival, (0, 1) if user_is_home else (1, 0)
        striker = next(p for p in scorer.players if p.position is not Position.GK)
        result = MatchResult(
            home_goals=goals[0],
            away_goals=goals[1],
            goals=[Goal(10 * n, striker.id, scorer.squad_id) for n in range(1, max(goals) + 1)],
        )
        if self.red_card_for is not None:
            result.cards.append(Card(55, self.red_card_for, USER_SQUAD, CardType.RED))
            self.red_card_for = None
        return result

    def simulate_quick(self, context: MatchContext) -> MatchResult:
        scorer = context.home.players[-1]
        return MatchResult(home_goals=1, away_goals=0, goals=[Goal(30, scorer.id, context.home.squad_id)])


@pytest.fixture
def simulator() -> ScriptedSimulator:
    return ScriptedSimulator()


@pytest.fixture
def client(simulator):
    app = create_app(build_container(simulator=simulator, rng=random.Random(7)))
    return app.test_client()


class Cup:
    """Drives one session through the API the way the mobile app would."""

    def __init__(self, client, squad: str = USER_SQUAD):
        self.client = client
        self.squad = squad
        self.id = client.post("/session").get_json()["sessionId"]

    def get(self, path: str):
        return self.client.get(f"/{self.id}/{path}")

    def post(self, path: str, body: dict | None = None):
        return self.client.post(f"/{self.id}/{path}", json=body)

    def preset(self, preset_id: str = "current") -> list[int]:
        presets = self.client.get(f"/{self.squad}/presets").get_json()["presets"]
        chosen = next(preset for preset in presets if preset["id"] == preset_id)
        return [player["id"] for player in chosen["players"]]

    def call_up(self):
        return self.post("call-up", {"squad": self.squad, "players": self.preset()})

    def start(self) -> dict:
        """Call-up and group draw."""
        assert self.call_up().status_code == 200
        response = self.get("draw")
        assert response.status_code == 200
        return response.get_json()

    def lineup(self) -> list[int]:
        available = self.get("available-players").get_json()["available"]
        goalkeeper = next(p for p in available if p["position"] == "GK")
        outfield = [p for p in available if p["position"] != "GK"][:10]
        return [goalkeeper["id"], *(p["id"] for p in outfield)]

    def play(self) -> dict:
        response = self.post("simulate", {"players": self.lineup(), "formation": "4-4-2"})
        assert response.status_code == 200, response.get_json()
        return response.get_json()

    def play_group_stage(self) -> dict:
        outcome = {}
        for _ in range(3):
            outcome = self.play()
        return outcome


@pytest.fixture
def cup(client) -> Cup:
    return Cup(client)
