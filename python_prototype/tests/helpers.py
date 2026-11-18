"""Helpers e constantes compartilhados pelos testes."""
from __future__ import annotations

from dataclasses import fields

from python_prototype.collective_attributes import Player

import random

# Posições dos jogadores (uma por jogador) e slots da formação (uma por vaga).
POSITIONS_433 = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "RW", "ST", "LW"]
POSITIONS_442 = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "CM", "ST", "ST"]
POSITIONS_532 = ["GK", "CB", "CB", "FB", "FB", "CB", "CM", "CM", "CM", "ST", "ST"]

FORMATION_433 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]
FORMATION_442 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "CM", "ST", "ST"]


def make_player(name: str, pos: str, rating: int = 70, **overrides: float) -> Player:
    """
    Cria um Player com todos os atributos iguais a `rating`.

    `overrides` sobrescreve atributos específicos, p. ex.
    make_player("X", "ST", shooting=95, defending=20). Os campos vêm de
    `dataclasses.fields`, então novos campos de Player não exigem ajuste aqui.
    """
    values = {
        f.name: rating for f in fields(Player) if f.name not in ("name", "pos")
    }
    unknown = set(overrides) - set(values)
    if unknown:
        raise TypeError(f"Atributos desconhecidos para Player: {sorted(unknown)}")
    values.update(overrides)
    return Player(name=name, pos=pos, **values)


def make_lineup(
    positions: list[str], rating: int = 70, prefix: str = "Player "
) -> list[Player]:
    """Um jogador por posição, nomeados `{prefix}{índice}`."""
    return [make_player(f"{prefix}{i}", pos, rating) for i, pos in enumerate(positions)]


def squad(prefix: str, rating: int, positions: list[str] = POSITIONS_433) -> list[Player]:
    """Escalação com nomes `{prefix}0..10` (padrão 4-3-3)."""
    return make_lineup(positions, rating, prefix)

class ScriptedRandom(random.Random):
    """
    RNG que devolve uma sequência fixa de sorteios, na ordem dada.

    `used` conta os sorteios consumidos e `remaining` os que sobraram. Se o
    código consumir mais do que o roteiro, levanta AssertionError.
    """

    def __init__(self, draws):
        super().__init__()
        self._draws = list(draws)
        self.used = 0

    def random(self) -> float:
        if self.used >= len(self._draws):
            raise AssertionError("ScriptedRandom: sequência de sorteios esgotada.")
        value = self._draws[self.used]
        self.used += 1
        return value

    @property
    def remaining(self) -> int:
        return len(self._draws) - self.used