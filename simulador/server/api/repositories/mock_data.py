"""Mock squads and players, standing in for the real dataset.

The 16 nations mirror the app's MockTeams.kt. Players are generated from name
pools with an RNG seeded by the squad id, so ids and attributes are identical on
every start.
"""

import random

from api.domain.models import Federation, Player, Position, Squad

_CONMEBOL, _CONCACAF = Federation.CONMEBOL, Federation.CONCACAF

# (id, name, ISO code for the flag, federation, base overall, name pool)
_SQUADS = [
    ("argentina", "Argentina", "ar", _CONMEBOL, 84, "es"),
    ("bolivia", "Bolívia", "bo", _CONMEBOL, 68, "es"),
    ("brazil", "Brasil", "br", _CONMEBOL, 84, "pt"),
    ("colombia", "Colômbia", "co", _CONMEBOL, 79, "es"),
    ("chile", "Chile", "cl", _CONMEBOL, 75, "es"),
    ("ecuador", "Equador", "ec", _CONMEBOL, 76, "es"),
    ("paraguay", "Paraguai", "py", _CONMEBOL, 74, "es"),
    ("venezuela", "Venezuela", "ve", _CONMEBOL, 73, "es"),
    ("uruguay", "Uruguai", "uy", _CONMEBOL, 80, "es"),
    ("usa", "Estados Unidos", "us", _CONCACAF, 77, "en"),
    ("mexico", "México", "mx", _CONCACAF, 77, "es"),
    ("costa_rica", "Costa Rica", "cr", _CONCACAF, 72, "es"),
    ("panama", "Panamá", "pa", _CONCACAF, 71, "es"),
    ("haiti", "Haiti", "ht", _CONCACAF, 66, "fr"),
    ("jamaica", "Jamaica", "jm", _CONCACAF, 71, "en"),
    ("peru", "Peru", "pe", _CONMEBOL, 73, "es"),
]

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
    "fr": (
        [
            "Jean", "Pierre", "Frantzdy", "Duckens", "Wilde", "Carlens", "Ricardo", "Steeven",
            "Derrick", "Johny", "Mechack", "Kévin", "Alex", "Bryan", "Danley", "Leverton",
            "Garven", "Josué", "Fabrice", "Stéphane", "Louicius", "Mikaël", "Zachary", "Martin",
            "Jems", "Djimy", "Carl", "Don", "Christopher", "Ronaldo",
        ],
        [
            "Pierre", "Nazon", "Arcus", "Étienne", "Lafrance", "Jérôme", "Alceus", "Sainté",
            "Guerrier", "Bazile", "Cantave", "Duverger", "Placide", "Lambese", "Métusala", "Deedson",
            "Dorsainvil", "Désiré", "Joseph", "Louis", "Charles", "François", "Michel", "Baptiste",
            "Toussaint", "Dorival", "Belfort", "Geffrard", "Sanon", "Vorbe",
        ],
    ),
}


def build_squads() -> list[Squad]:
    return [
        Squad(id=squad_id, name=name, flag=f"https://flagcdn.com/w320/{iso}.png", federation=federation)
        for squad_id, name, iso, federation, _, _ in _SQUADS
    ]


def build_players() -> list[Player]:
    players = []
    for index, (squad_id, _, _, _, strength, language) in enumerate(_SQUADS):
        players += _generate_squad(index, squad_id, strength, language)
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
            players.append(
                Player(
                    id=(index + 1) * 100 + len(players) + 1,
                    squad_id=squad_id,
                    name=name,
                    age=rng.randint(36, 48) if is_legend else rng.randint(19, 34),
                    position=position,
                    overall=max(50, min(99, strength + boost)),
                    is_current=not is_legend,
                    is_legend=is_legend,
                )
            )
    return players
