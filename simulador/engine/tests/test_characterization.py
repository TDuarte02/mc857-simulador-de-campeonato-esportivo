"""
Teste de caracterização: congela o resultado de partidas completas com seeds
fixas e times heterogêneos. Falha se a ordem de consumo do RNG ou qualquer
fórmula mudar, mesmo de forma sutil.

Para regenerar o snapshot (só após mudança INTENCIONAL de regra, já registrada
na spec):  UPDATE_GOLDEN=1 uv run pytest tests/test_characterization.py
"""
import json
import os
from pathlib import Path

from copa_engine.match import create_match, play_match
from tests.helpers import (
    FORMATION_433,
    FORMATION_442,
    POSITIONS_433,
    POSITIONS_442,
    make_player,
)

# Regrava o gabarito com UPDATE_GOLDEN=1 no ambiente (só após mudança intencional).
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"
GOLDEN = Path(__file__).parent / "golden" / "match_seeds.json"
SEEDS = (0, 1, 7, 42, 2026)


def _squad(prefix, positions, base):
    players = []
    for i, pos in enumerate(positions):
        rating = base + (i * 7) % 15
        boosted = min(100, rating + 10)
        overrides = {}
        if pos in ("ST", "RW", "LW"):
            overrides["shooting"] = boosted
        if pos in ("CB", "RB", "LB"):
            overrides["defending"] = boosted
        players.append(make_player(f"{prefix}{i}", pos, rating, **overrides))
    return players


def _run(seed):
    state = create_match(
        _squad("A", POSITIONS_433, 66), FORMATION_433,
        _squad("B", POSITIONS_442, 62), FORMATION_442,
    )
    play_match(state, seed=seed)
    return {
        "score": state.score,
        "events": [[e.minute, e.type.value, e.team, dict(e.data)] for e in state.events],
    }


def test_match_outcomes_match_golden_snapshot():
    current = {str(seed): _run(seed) for seed in SEEDS}

    if UPDATE_GOLDEN:
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    assert GOLDEN.exists(), "Snapshot ausente: gere com UPDATE_GOLDEN=1 e versione o arquivo."
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert json.loads(json.dumps(current)) == expected