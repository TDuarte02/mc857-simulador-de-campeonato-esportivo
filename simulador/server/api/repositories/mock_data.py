"""Mock squads and players, standing in for the real dataset in tests and development.

The squads are the pinned 16 (nations.py). Players are generated from name pools
with an RNG seeded by the squad id, so ids and attributes are identical on every
start. Like the engine's synthetic teams, every engine attribute of a player
equals their overall.
"""

import random

from api.domain.engine_data import ENGINE_ATTRIBUTES
from api.domain.models import Player, Position, Squad
from api.repositories.nations import NATIONS

# Per squad id: (base overall, name pool).
_STRENGTH = {
    "argentina": (84, "es"),
    "bolivia": (68, "es"),
    "brazil": (84, "pt"),
    "colombia": (79, "es"),
    "chile": (75, "es"),
    "ecuador": (76, "es"),
    "paraguay": (74, "es"),
    "venezuela": (73, "es"),
    "uruguay": (80, "es"),
    "usa": (77, "en"),
    "mexico": (77, "es"),
    "costa_rica": (72, "es"),
    "panama": (71, "es"),
    "canada": (70, "en"),
    "jamaica": (71, "en"),
    "peru": (73, "es"),
}

# Dataset position codes handed out, in turn, to each sector's players.
_CODES = {
    Position.GK: ("GK",),
    Position.DEF: ("CB", "RB", "CB", "LB"),
    Position.MID: ("CM", "CDM", "CAM", "CM"),
    Position.FW: ("ST", "LW", "RW", "ST"),
}

# Per position: (players tagged current, players tagged legend). The current ones
# add up to exactly one valid 26-player call-up.
_POOL = {
    Position.GK: (3, 2),
    Position.DEF: (8, 4),
    Position.MID: (8, 4),
    Position.FW: (7, 4),
}

_NAMES = {
    "es": (
        [
            "Santiago", "Mateo", "Lautaro", "Nicolás", "Emiliano", "Julián", "Rodrigo", "Facundo",
            "Gonzalo", "Cristian", "Sebastián", "Diego", "Luis", "Carlos", "Andrés", "Jorge",
            "Miguel", "Javier", "Fernando", "Pablo", "Ángel", "Enzo", "Leandro", "Marcos",
            "Darwin", "Federico", "José", "Juan", "Raúl", "Kevin", "Bryan", "Wilmar",
            "Alexis", "Arturo", "Claudio", "Paolo", "Renato", "Óscar", "Héctor", "Iván",
        ],
        [
            "González", "Rodríguez", "Martínez", "Fernández", "López", "Díaz", "Pérez", "Sánchez",
            "Romero", "Álvarez", "Torres", "Ruiz", "Ramírez", "Flores", "Acosta", "Benítez",
            "Medina", "Herrera", "Suárez", "Aguirre", "Giménez", "Molina", "Castro", "Ortiz",
            "Núñez", "Rojas", "Vargas", "Cardozo", "Vega", "Cabrera", "Valencia", "Mina",
            "Zambrano", "Guerrero", "Vidal", "Bravo", "Chávez", "Paredes", "Navarro", "Salazar",
        ],
    ),
    "pt": (
        [
            "Gabriel", "Lucas", "Vinícius", "Rafael", "Thiago", "Bruno", "Matheus", "Pedro",
            "João", "Éder", "Danilo", "Marcos", "Renan", "Douglas", "Wesley", "Igor",
            "Caio", "André", "Felipe", "Guilherme", "Leonardo", "Gustavo", "Diego", "Fábio",
            "Murilo", "Samuel", "Vitor", "Henrique", "Rodrigo", "Luan",
        ],
        [
            "Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Ferreira",
            "Almeida", "Ribeiro", "Carvalho", "Gomes", "Martins", "Araújo", "Barbosa", "Rocha",
            "Dias", "Moreira", "Nunes", "Marques", "Machado", "Mendes", "Freitas", "Cardoso",
            "Teixeira", "Correia", "Monteiro", "Moura", "Cavalcanti", "Rezende",
        ],
    ),
    "en": (
        [
            "James", "Michael", "Tyler", "Jordan", "Chris", "Aaron", "Ethan", "Josh",
            "Matt", "Brandon", "Kyle", "Ryan", "Justin", "Kevin", "Andre", "Damion",
            "Shamar", "Kemar", "Leon", "Bobby", "Miles", "Walker", "Zack", "Tim",
            "Cameron", "Jalen", "Malik", "Darnell", "Tyrone", "Marcus",
        ],
        [
            "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson",
            "Taylor", "Thomas", "Moore", "Jackson", "Martin", "Thompson", "White", "Harris",
            "Clark", "Lewis", "Robinson", "Young", "Allen", "King", "Wright", "Scott",
            "Green", "Baker", "Campbell", "Morrison", "Bailey", "Lowe",
        ],
    ),
}


def build_squads() -> list[Squad]:
    return [Squad(id=n.id, name=n.name, flag=n.flag, federation=n.federation) for n in NATIONS]


def build_players() -> list[Player]:
    players = []
    for index, nation in enumerate(NATIONS):
        strength, language = _STRENGTH[nation.id]
        players += _generate_squad(index, nation.id, strength, language)
    return players


def _generate_squad(index: int, squad_id: str, strength: int, language: str) -> list[Player]:
    rng = random.Random(squad_id)
    first_names, last_names = _NAMES[language]
    used_names: set[str] = set()
    players: list[Player] = []
    for position, (current, legends) in _POOL.items():
        for n in range(current + legends):
            is_legend = n >= current
            name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
            while name in used_names:
                name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
            used_names.add(name)
            boost = rng.randint(3, 10) if is_legend else rng.randint(-6, 5)
            player_id = (index + 1) * 100 + len(players) + 1
            overall = max(50, min(99, strength + boost))
            players.append(
                Player(
                    id=player_id,
                    squad_id=squad_id,
                    name=name,
                    age=rng.randint(36, 48) if is_legend else rng.randint(19, 34),
                    position=position,
                    overall=overall,
                    is_current=not is_legend,
                    is_legend=is_legend,
                    positions=(_CODES[position][n % len(_CODES[position])],),
                    attributes={field: overall for field in ENGINE_ATTRIBUTES},
                    person_key=str(player_id),
                )
            )
    return players
