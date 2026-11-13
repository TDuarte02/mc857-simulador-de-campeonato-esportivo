import math
import random

from api.domain.models import Card, CardType, Goal, Injury, MatchResult, Player, Position
from api.simulation.base import MatchContext, MatchSimulator, TeamSheet

# How likely each position is to score, relative to the others.
_SCORING_WEIGHT = {Position.GK: 0, Position.DEF: 1, Position.MID: 3, Position.FW: 6}


class RandomMatchSimulator(MatchSimulator):
    """Stand-in for the real model: random outcomes, nudged by the lineups' overall."""

    def __init__(self, rng: random.Random | None = None):
        self._rng = rng or random.Random()

    def simulate_match(self, context: MatchContext) -> MatchResult:
        return self._play(context, detailed=True)

    def simulate_quick(self, context: MatchContext) -> MatchResult:
        return self._play(context, detailed=False)

    def _play(self, context: MatchContext, detailed: bool) -> MatchResult:
        home, away = context.home, context.away
        gap = _strength(home) - _strength(away)
        home_goals = self._goals(home, 1.35 + gap / 10)
        away_goals = self._goals(away, 1.35 - gap / 10)

        result = MatchResult(
            home_goals=len(home_goals),
            away_goals=len(away_goals),
            goals=sorted(home_goals + away_goals, key=lambda goal: goal.minute),
            cards=sorted(self._cards(home) + self._cards(away), key=lambda card: card.minute),
        )
        if detailed:  # the quick model does not track injuries
            result.injuries = self._injuries(home) + self._injuries(away)
        if context.needs_winner and result.home_goals == result.away_goals:
            result.home_penalties, result.away_penalties = self._shootout()
        return result

    def _goals(self, team: TeamSheet, expected: float) -> list[Goal]:
        if not team.players:
            return []
        count = self._poisson(max(0.2, min(3.5, expected)))
        weights = [_SCORING_WEIGHT[player.position] for player in team.players]
        scorers = self._rng.choices(team.players, weights=weights, k=count) if any(weights) else []
        return [Goal(self._minute(), scorer.id, team.squad_id) for scorer in scorers]

    def _cards(self, team: TeamSheet) -> list[Card]:
        booked = self._pick(team.players, min(self._poisson(1.3), 4))
        cards = [Card(self._minute(), player.id, team.squad_id, CardType.YELLOW) for player in booked]
        if self._rng.random() < 0.07:
            for player in self._pick([p for p in team.players if p not in booked], 1):
                cards.append(Card(self._minute(), player.id, team.squad_id, CardType.RED))
        return cards

    def _injuries(self, team: TeamSheet) -> list[Injury]:
        if self._rng.random() >= 0.08:
            return []
        return [
            Injury(self._minute(), player.id, team.squad_id, matches_out=self._rng.randint(1, 3))
            for player in self._pick(team.players, 1)
        ]

    def _shootout(self) -> tuple[int, int]:
        while True:
            home, away = self._rng.randint(2, 5), self._rng.randint(2, 5)
            if home != away:
                return home, away

    def _pick(self, players: list[Player], count: int) -> list[Player]:
        return self._rng.sample(players, min(count, len(players)))

    def _minute(self) -> int:
        return self._rng.randint(1, 90)

    def _poisson(self, mean: float) -> int:
        threshold, count, product = math.exp(-mean), 0, self._rng.random()
        while product > threshold:
            count += 1
            product *= self._rng.random()
        return count


def _strength(team: TeamSheet) -> float:
    if not team.players:
        return 0.0
    return sum(player.overall for player in team.players) / len(team.players)
