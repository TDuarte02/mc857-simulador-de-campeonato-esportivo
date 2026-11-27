"""
Escalação: membros do elenco com as suas posições, escalação padrão
automática, encaixe de uma escalação escolhida nos slots de uma formação e a
checagem de cobertura de setores de um elenco.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from copa_engine.collective_attributes import (
    POSITION_SECTORS,
    Player,
    canonical_position,
)

DEFAULT_FORMATION: tuple[str, ...] = (
    "GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W",
)

# As formações que o app oferece, slot a slot. A contagem por setor bate com
# MockFormations.kt. A ordem importa: é a ordem em que `derive_cards` sorteia o
# jogador punido e em que `pick_scorer` percorre os candidatos, por isso o 4-3-3
# é exatamente a DEFAULT_FORMATION das seleções da máquina.
FORMATIONS: dict[str, tuple[str, ...]] = {
    "4-4-2": ("GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "CM", "ST", "ST"),
    "4-3-3": DEFAULT_FORMATION,
    "3-5-2": ("GK", "CB", "CB", "CB", "CM", "CM", "CM", "CM", "AM", "ST", "ST"),
    "4-2-3-1": ("GK", "FB", "CB", "CB", "FB", "DM", "DM", "AM", "AM", "AM", "ST"),
}

# Ordem de preenchimento dos slots da escalação.
SECTOR_ORDER = {"GK": 0, "DEF": 1, "MID": 2, "FW": 3}

# Mínimos entre os jogadores de linha para suportar as 4 formações do app
# (máximos: 4 DEF, 5 MID, 3 FW).
MIN_DEFENDERS, MIN_MIDFIELDERS, MIN_FORWARDS = 4, 5, 3


class SetupError(ValueError):
    """Erro explícito de preparação do torneio (dataset, elenco ou escalação)."""


class LineupDoesNotFit(SetupError):
    """A escalação escolhida não cabe na formação; `players` são os que sobram."""

    def __init__(self, message: str, players: Sequence[str] = ()):
        super().__init__(message)
        self.players = tuple(players)


@dataclass(frozen=True)
class SquadMember:
    """Jogador do elenco com todas as suas posições reconhecidas."""

    player: Player
    positions: tuple[str, ...]  # texto original das posições reconhecidas

    @property
    def canonical_positions(self) -> frozenset[str]:
        return frozenset(canonical_position(p) for p in self.positions)

    @property
    def sectors(self) -> frozenset[str]:
        return frozenset(POSITION_SECTORS[c] for c in self.canonical_positions)

    @property
    def is_goalkeeper(self) -> bool:
        return "GK" in self.canonical_positions


def _rank(member: SquadMember) -> tuple[int, str]:
    return (-member.player.overall, member.player.name)


# ============================================================
# Escalação padrão
# ============================================================

def default_lineup(
    nation: str, squad: Sequence[SquadMember], formation: Sequence[str] = DEFAULT_FORMATION
) -> tuple[Player, ...]:
    """
    Escalação determinística: slots preenchidos por setor (GK, DEF, MID, FW);
    em cada slot, o melhor não utilizado com a mesma posição canônica; na
    falta, o melhor do mesmo setor, recriado com a posição do slot. O goleiro
    nunca é improvisado. Devolve os jogadores na ordem dos slots.
    """
    slots = list(formation)
    canon = [canonical_position(s) for s in slots]
    order = sorted(range(len(slots)), key=lambda i: SECTOR_ORDER[POSITION_SECTORS[canon[i]]])
    ranked = sorted(squad, key=_rank)

    used: set[int] = set()
    chosen: dict[int, Player] = {}

    for i in order:
        slot, slot_canon = slots[i], canon[i]
        sector = POSITION_SECTORS[slot_canon]

        if slot_canon == "GK":
            pick = next(
                (k for k, m in enumerate(ranked) if k not in used and m.is_goalkeeper), None
            )
            if pick is None:
                raise SetupError(f"{nation}: não há goleiro disponível para a escalação.")
            used.add(pick)
            chosen[i] = ranked[pick].player
            continue

        candidates = [(k, m) for k, m in enumerate(ranked) if k not in used and not m.is_goalkeeper]
        exact = next(((k, m) for k, m in candidates if slot_canon in m.canonical_positions), None)
        if exact is not None:
            k, member = exact
            pos = next(p for p in member.positions if canonical_position(p) == slot_canon)
        else:
            same_sector = next(((k, m) for k, m in candidates if sector in m.sectors), None)
            if same_sector is None:
                raise SetupError(
                    f"{nation}: não há jogador disponível do setor {sector} "
                    f"para o slot {slot}."
                )
            k, member = same_sector
            pos = slot
        used.add(k)
        chosen[i] = member.player if member.player.pos == pos else replace(member.player, pos=pos)

    return tuple(chosen[i] for i in range(len(slots)))


# ============================================================
# Escalação escolhida -> slots da formação
# ============================================================

_NO_EDGE = 10**6  # custo de um encaixe proibido (setor diferente)


def _slot_cost(member: SquadMember, slot: str) -> int:
    """0: posição exata; 1: mesmo setor; _NO_EDGE: não pode jogar ali."""
    canon = canonical_position(slot)
    if canon in member.canonical_positions:
        return 0
    return 1 if POSITION_SECTORS[canon] in member.sectors else _NO_EDGE


def _min_cost_assignment(cost: list[list[int]]) -> list[int]:
    """
    Emparelhamento perfeito de custo mínimo (algoritmo húngaro, por caminhos
    aumentantes mais curtos), matriz quadrada. Devolve, por linha, a coluna.
    """
    n = len(cost)
    u, v = [0.0] * (n + 1), [0.0] * (n + 1)
    owner, way = [0] * (n + 1), [0] * (n + 1)   # owner[coluna] = linha (base 1)
    for row in range(1, n + 1):
        owner[0] = row
        col0 = 0
        best = [float("inf")] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[col0] = True
            r, delta, col1 = owner[col0], float("inf"), 0
            for col in range(1, n + 1):
                if used[col]:
                    continue
                reduced = cost[r - 1][col - 1] - u[r] - v[col]
                if reduced < best[col]:
                    best[col], way[col] = reduced, col0
                if best[col] < delta:
                    delta, col1 = best[col], col
            for col in range(n + 1):
                if used[col]:
                    u[owner[col]] += delta
                    v[col] -= delta
                else:
                    best[col] -= delta
            col0 = col1
            if owner[col0] == 0:
                break
        while col0:
            col1 = way[col0]
            owner[col0] = owner[col1]
            col0 = col1
    assignment = [0] * n
    for col in range(1, n + 1):
        assignment[owner[col] - 1] = col - 1
    return assignment


def _unplaced(members: Sequence[SquadMember], slots: Sequence[str]) -> list[SquadMember]:
    """Quem fica sem slot num emparelhamento máximo (caminhos aumentantes, Kuhn)."""
    owner: dict[int, int] = {}

    def place(m: int, seen: set[int]) -> bool:
        for s, slot in enumerate(slots):
            if s in seen or _slot_cost(members[m], slot) >= _NO_EDGE:
                continue
            seen.add(s)
            if s not in owner or place(owner[s], seen):
                owner[s] = m
                return True
        return False

    placed = {m for m in range(len(members)) if place(m, set())}
    return [members[m] for m in range(len(members)) if m not in placed]


def _place_outfield(
    members: Sequence[SquadMember], slots: Sequence[str]
) -> list[Player] | None:
    """Jogadores na ordem de `slots`, preferindo a posição exata; None se não couber."""
    cost = [[_slot_cost(m, slot) for slot in slots] for m in members]
    assignment = _min_cost_assignment(cost)
    if any(cost[m][s] >= _NO_EDGE for m, s in enumerate(assignment)):
        return None
    placed: list[Player] = [members[0].player] * len(slots)
    for m, s in enumerate(assignment):
        member, canon = members[m], canonical_position(slots[s])
        pos = next((p for p in member.positions if canonical_position(p) == canon), slots[s])
        placed[s] = member.player if member.player.pos == pos else replace(member.player, pos=pos)
    return placed


def assign_slots(xi: Sequence[SquadMember], formation: Sequence[str]) -> tuple[Player, ...]:
    """
    Encaixa 11 jogadores escolhidos nos slots da formação (decisões D1 e D6).

    - Um goleiro apto da escalação vai para o gol.
    - Sem goleiro (todos fora), um jogador de linha vai para o gol com
      pos="GK": os candidatos são tentados por `goalkeeping_reflexes` (maior
      primeiro; empate pela ordem de `xi`) e fica o primeiro cuja saída deixa
      os outros dez encaixáveis.
    - Linha: emparelhamento de custo mínimo, posição exata (custo 0) antes do
      mesmo setor (custo 1); outro setor não é permitido.

    Devolve os jogadores na ordem dos slots, com `pos` = a posição exata do
    jogador ou, fora dela, o slot. Levanta LineupDoesNotFit, com os jogadores
    que sobram, se não houver encaixe.
    """
    xi, formation = list(xi), list(formation)
    if len(xi) != len(formation):
        raise LineupDoesNotFit(
            f"A escalação tem {len(xi)} jogadores e a formação, {len(formation)} slots."
        )
    goal = [i for i, slot in enumerate(formation) if canonical_position(slot) == "GK"]
    if len(goal) != 1:
        raise LineupDoesNotFit("A formação deve ter exatamente um goleiro.")
    goal_slot = goal[0]
    outfield_slots = [slot for i, slot in enumerate(formation) if i != goal_slot]
    keepers = [m for m in xi if m.is_goalkeeper]
    if len(keepers) > 1:
        raise LineupDoesNotFit(
            "Só um goleiro pode ser escalado; goleiro não joga na linha.",
            [m.player.name for m in keepers[1:]],
        )

    def build(keeper: Player, outfield: list[Player]) -> tuple[Player, ...]:
        return (*outfield[:goal_slot], keeper, *outfield[goal_slot:])

    if keepers:
        outfield = [m for m in xi if not m.is_goalkeeper]
        placed = _place_outfield(outfield, outfield_slots)
        if placed is None:
            stuck = [m.player.name for m in _unplaced(outfield, outfield_slots)]
            raise LineupDoesNotFit(
                f"A escalação não cabe na formação; sobram: {', '.join(stuck)}.", stuck
            )
        return build(keepers[0].player, placed)

    # D6: ninguém apto no gol; um jogador de linha improvisa.
    order = sorted(range(len(xi)), key=lambda i: -xi[i].player.goalkeeping_reflexes)
    for i in order:
        placed = _place_outfield(xi[:i] + xi[i + 1:], outfield_slots)
        if placed is not None:
            return build(replace(xi[i].player, pos="GK"), placed)
    stuck = [m.player.name for m in _unplaced(xi, outfield_slots)] or [m.player.name for m in xi]
    raise LineupDoesNotFit(
        "Sem goleiro, nenhum jogador de linha pode ir para o gol deixando os outros "
        f"dez encaixados na formação; sobram: {', '.join(stuck)}.",
        stuck,
    )


# ============================================================
# Cobertura de setores do elenco
# ============================================================

def covers_sectors(outfield: Sequence[SquadMember]) -> bool:
    """Existe atribuição de jogadores a vagas de setor (4 DEF, 5 MID, 3 FW), um por vaga?"""
    slots = ["DEF"] * MIN_DEFENDERS + ["MID"] * MIN_MIDFIELDERS + ["FW"] * MIN_FORWARDS
    owner: dict[int, int] = {}

    def assign(slot: int, seen: set[int]) -> bool:
        for p, member in enumerate(outfield):
            if slots[slot] in member.sectors and p not in seen:
                seen.add(p)
                if p not in owner or assign(owner[p], seen):
                    owner[p] = slot
                    return True
        return False

    return all(assign(s, set()) for s in range(len(slots)))
