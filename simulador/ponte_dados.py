"""Ponte entre o dataset do `pipeline-dados` e o motor de partida.

Lê o CSV exportado por `pipeline-dados` (formato do `Player` do motor), monta o XI de
cada seleção e joga uma partida.

Uso:
    python ponte_dados.py --jogadores ../pipeline-dados/artefatos/jogadores_para_motor.csv \
        --casa Argentina --fora Brasil --seed 42
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict

from python_prototype.collective_attributes import (
    Player,
    POSITION_SECTORS,
    canonical_position,
)
from python_prototype.match import create_match, play_match

CAMPOS = (
    "overall", "potential", "pace", "shooting", "passing", "dribbling", "defending", "physic",
    "attacking_heading_accuracy", "movement_agility", "movement_reactions", "movement_balance",
    "power_jumping", "power_stamina", "mentality_aggression", "mentality_penalties",
    "mentality_composure", "goalkeeping_reflexes",
)
# Escalação alvo: 1 GK, 4 DEF, 3 MID, 3 FW (a formação de referência do motor).
ALVO = {"GK": 1, "DEF": 4, "MID": 3, "FW": 3}


def carregar(caminho: str) -> dict[str, list[Player]]:
    """Lê o CSV exportado e devolve os jogadores agrupados por seleção."""
    por_pais: dict[str, list[Player]] = defaultdict(list)
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            jogador = Player.from_csv_row(linha["name"], linha["pos"], linha)
            por_pais[linha["pais"]].append(jogador)
    return dict(por_pais)


def setor(jogador: Player) -> str:
    return POSITION_SECTORS[canonical_position(jogador.pos)]


def escalar(jogadores: list[Player]) -> list[Player]:
    """Escolhe 11 titulares: preenche a cota por setor pelos melhores `overall`.

    Se algum setor não tiver jogadores suficientes, completa com os melhores restantes —
    a formação é derivada depois dos próprios titulares, então continua válida.
    """
    ordenados = sorted(jogadores, key=lambda j: -j.overall)
    escalados: list[Player] = []
    usados: set[str] = set()
    for alvo_setor, quantos in ALVO.items():
        for jogador in ordenados:
            if len([j for j in escalados if setor(j) == alvo_setor]) >= quantos:
                break
            if jogador.name in usados or setor(jogador) != alvo_setor:
                continue
            escalados.append(jogador)
            usados.add(jogador.name)
    for jogador in ordenados:
        if len(escalados) >= 11:
            break
        if jogador.name not in usados:
            escalados.append(jogador)
            usados.add(jogador.name)
    return escalados[:11]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jogadores", required=True)
    parser.add_argument("--casa", required=True)
    parser.add_argument("--fora", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    por_pais = carregar(args.jogadores)
    for pais in (args.casa, args.fora):
        if pais not in por_pais:
            raise SystemExit(f"seleção sem jogadores no CSV: {pais}")

    casa = escalar(por_pais[args.casa])
    fora = escalar(por_pais[args.fora])

    for rotulo, time in ((args.casa, casa), (args.fora, fora)):
        setores = defaultdict(int)
        for jogador in time:
            setores[setor(jogador)] += 1
        print(f"{rotulo}: {len(time)} titulares ({dict(setores)})")

    # A formação são os próprios slots dos titulares: os setores batem por construção,
    # e os bônus de formação saem relativos ao 4-3-3 de referência do motor.
    partida = create_match(casa, [j.pos for j in casa], fora, [j.pos for j in fora])
    play_match(partida, seed=args.seed)

    print(f"\n=== {args.casa} {partida.score['A']} x {partida.score['B']} {args.fora} (seed={args.seed}) ===")
    for evento in partida.events:
        quem = {"A": args.casa, "B": args.fora}.get(evento.team or "", "")
        marca = {"GOAL": " ⚽", "POSSESSION_LOST": "", "MD3_RESULT": ""}.get(evento.type.value, "")
        print(f"  {evento.minute:>2}' {evento.type.value:<16} {quem:<12} {evento.detail}{marca}")

    gols = [e for e in partida.events if e.type.value == "GOAL"]
    md3 = [e for e in partida.events if e.type.value == "MD3_RESULT"]
    print(f"\nresumo: {len(md3)} disputas de posse, {len(gols)} gols, {len(partida.events)} eventos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
