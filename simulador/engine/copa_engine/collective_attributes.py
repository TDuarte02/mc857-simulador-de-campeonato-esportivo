from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields

from copa_engine.common import ATTRIBUTE_MAX, clamp

# Tolerância para erro de ponto flutuante nas somas ponderadas
# (p. ex. 100.00000000000001 com todos os atributos em 100).
SCORE_TOLERANCE = 1e-9

@dataclass(frozen=True)
class Player:
    name: str
    pos: str
    overall: int
    potential: int
    pace: float
    shooting: float
    passing: float
    dribbling: float
    defending: float
    physic: float
    attacking_heading_accuracy: int
    movement_agility: int
    movement_reactions: int
    movement_balance: int
    power_jumping: int
    power_stamina: int
    mentality_aggression: int
    mentality_penalties: int
    mentality_composure: int
    goalkeeping_reflexes: int

    def __post_init__(self) -> None:
        """Exige todos os atributos numéricos finitos e em [0, ATTRIBUTE_MAX]."""
        for f in fields(self):
            if f.name in ("name", "pos"):
                continue
            value = getattr(self, f.name)
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and 0 <= value <= ATTRIBUTE_MAX  # NaN falha aqui
            )
            if not valid:
                raise ValueError(
                    f"Atributo {f.name!r} de {self.name!r} fora da escala "
                    f"[0, {ATTRIBUTE_MAX:g}]: {value!r}"
                )

    @classmethod
    def from_csv_row(cls, name: str, pos: str, row: Mapping[str, str]) -> "Player":
        """
        Cria um Player a partir de uma linha de CSV (valores em texto).

        Todas as colunas dos atributos são obrigatórias, inclusive `overall`.
        Levanta ValueError se faltar coluna ou se um valor não for numérico
        ou estiver fora da escala.
        """
        numeric = [f for f in fields(cls) if f.name not in ("name", "pos")]

        missing = [f.name for f in numeric if f.name not in row]
        if missing:
            raise ValueError(f"Linha de {name!r} sem as colunas: {missing}")

        values: dict[str, float] = {}
        for f in numeric:
            convert = float if f.type == "float" else int
            try:
                values[f.name] = convert(row[f.name])
            except (TypeError, ValueError):
                raise ValueError(
                    f"Valor inválido na coluna {f.name!r} de {name!r}: {row[f.name]!r}"
                ) from None

        return cls(name=name, pos=pos, **values)

# ============================================================
# Configuração dos pesos dos atributos individuais
# ============================================================

ATTACK_WEIGHTS = {
    "shooting": 0.25,
    "passing": 0.20,
    "dribbling": 0.15,
    "pace": 0.10,
    "attacking_heading_accuracy": 0.10,
    "movement_reactions": 0.10,
    "mentality_composure": 0.10,
}

DEFENSE_WEIGHTS = {
    "defending": 0.35,
    "physic": 0.15,
    "movement_reactions": 0.15,
    "pace": 0.10,
    "movement_agility": 0.10,
    "power_jumping": 0.05,
    "mentality_aggression": 0.05,
    "movement_balance": 0.05,
}

CONTROL_WEIGHTS = {
    "passing": 0.25,
    "dribbling": 0.20,
    "movement_agility": 0.15,
    "movement_balance": 0.10,
    "movement_reactions": 0.10,
    "mentality_composure": 0.10,
    "physic": 0.05,
    "pace": 0.05,
}


# ============================================================
# Pesos posicionais
# ============================================================

# Valores relativos à contribuição de cada posição para
# os atributos coletivos. Não são probabilidades.
POSITION_WEIGHTS = {
    "GK": {"attack": 0.00, "defense": 1.00, "control": 0.00},
    "CB": {"attack": 0.10, "defense": 0.65, "control": 0.25},
    "FB": {"attack": 0.25, "defense": 0.45, "control": 0.30},
    "DM": {"attack": 0.20, "defense": 0.40, "control": 0.40},
    "CM": {"attack": 0.30, "defense": 0.25, "control": 0.45},
    "AM": {"attack": 0.50, "defense": 0.10, "control": 0.40},
    "W":  {"attack": 0.55, "defense": 0.10, "control": 0.35},
    "ST": {"attack": 0.75, "defense": 0.05, "control": 0.20},
}


# ============================================================
# Normalização de posições
# ============================================================

POSITION_ALIASES = {
    "GK": "GK",
    "GOALKEEPER": "GK",

    "CB": "CB",
    "LCB": "CB",
    "RCB": "CB",
    "SW": "CB",
    "DEF": "CB",
    "DEFENDER": "CB",

    "LB": "FB",
    "RB": "FB",
    "LWB": "FB",
    "RWB": "FB",
    "FB": "FB",
    "WB": "FB",
    "FULLBACK": "FB",

    "CDM": "DM",
    "DM": "DM",
    "LDM": "DM",
    "RDM": "DM",

    "CM": "CM",
    "LCM": "CM",
    "RCM": "CM",
    "LM": "CM",
    "RM": "CM",
    "MID": "CM",
    "MIDFIELDER": "CM",

    "CAM": "AM",
    "AM": "AM",
    "LAM": "AM",
    "RAM": "AM",

    "LW": "W",
    "RW": "W",
    "LF": "W",
    "RF": "W",
    "W": "W",
    "WINGER": "W",

    "ST": "ST",
    "CF": "ST",
    "LS": "ST",
    "RS": "ST",
    "FW": "ST",
    "FWD": "ST",
    "FORWARD": "ST",
}


# Setores do campo. Taxonomia única, usada tanto para validar a escalação
# quanto para calcular os modificadores de formação.
SECTORS = ("GK", "DEF", "MID", "FW")

POSITION_SECTORS = {
    "GK": "GK",
    "CB": "DEF",
    "FB": "DEF",
    "DM": "MID",
    "CM": "MID",
    "AM": "MID",
    "W": "FW",
    "ST": "FW",
}


# ============================================================
# Estruturas de resultado
# ============================================================

@dataclass(frozen=True)
class PlayerScores:
    attack: float
    defense: float
    control: float


@dataclass(frozen=True)
class TeamAttributes:
    attack: float
    defense: float
    control: float


@dataclass(frozen=True)
class FormationBonusConfig:
    """
    Bônus por jogador acima ou abaixo da formação de referência.

    A formação de referência é 4-3-3:
    4 defensores, 3 meio-campistas e 3 atacantes.
    O goleiro não entra nessa contagem.
    """

    baseline_defenders: int = 4
    baseline_midfielders: int = 3
    baseline_forwards: int = 3

    defender_attack: float = -1.0
    defender_defense: float = 2.0
    defender_control: float = -0.5

    midfielder_attack: float = 0.5
    midfielder_defense: float = -0.5
    midfielder_control: float = 2.0

    forward_attack: float = 2.0
    forward_defense: float = -1.0
    forward_control: float = -0.5


DEFAULT_FORMATION_BONUS = FormationBonusConfig()

# ============================================================
# Validação da formação
# ============================================================
def validate_lineup_matches_formation(
    players: Sequence[Player],
    formation: Sequence[str],
) -> None:
    """
    Garante que a escalação é coerente com a formação.

    Os pesos posicionais vêm de `player.pos`, mas os bônus de formação vêm
    dos slots de `formation`. Para que as duas fontes não divirjam:

    - a formação deve conter exatamente um goleiro;
    - a contagem de jogadores por setor (GK/DEF/MID/FW) deve ser igual à
      contagem de slots da formação.

    A comparação é por setor, não por slot: um jogador "RB" num slot "CB"
    é aceito (ambos são defesa), pois os modificadores de formação só
    dependem da contagem por setor.
    """
    formation_counts = formation_distribution(formation)

    if formation_counts["GK"] != 1:
        raise ValueError(
            "A formação deve conter exatamente um goleiro; "
            f"encontrado: {formation_counts['GK']}"
        )

    lineup_counts = formation_distribution([player.pos for player in players])

    if lineup_counts != formation_counts:
        raise ValueError(
            "A escalação não corresponde à formação: "
            f"jogadores {_describe_counts(lineup_counts)}, "
            f"formação {_describe_counts(formation_counts)}."
        )


def _describe_counts(counts: dict[str, int]) -> str:
    return (
        f"GK={counts['GK']} DEF={counts['DEF']} "
        f"MID={counts['MID']} FW={counts['FW']}"
    )

# ============================================================
# Cálculo das pontuações individuais
# ============================================================

def weighted_score(player: Player, weights: Mapping[str, float]) -> float:
    """Calcula uma média ponderada dos atributos de um jogador."""
    return sum(
        getattr(player, attribute) * weight
        for attribute, weight in weights.items()
    )


def canonical_position(pos: str) -> str:
    """Converte uma posição para sua categoria canônica."""
    normalized = pos.strip().upper().replace("-", "").replace(" ", "")
    try:
        return POSITION_ALIASES[normalized]
    except KeyError:
        raise ValueError(f"Posição desconhecida: {pos!r}") from None


def calculate_player_scores(player: Player) -> PlayerScores:
    """
    Calcula as pontuações individuais de Ataque, Defesa e Controle.

    Potential, overall, power_stamina e mentality_penalties
    não entram diretamente nos atributos coletivos.

    Como os atributos do Player são validados na construção e cada
    conjunto de pesos soma 1, o resultado cabe em [0, ATTRIBUTE_MAX].
    A checagem abaixo é defensiva (pesos mal configurados) e tolera
    erro de ponto flutuante; o valor devolvido é limitado à escala.
    """
    position = canonical_position(player.pos)

    raw = {
        "attack": weighted_score(player, ATTACK_WEIGHTS),
        "control": weighted_score(player, CONTROL_WEIGHTS),
        # O dataset só tem um atributo específico de goleiro.
        "defense": (
            float(player.goalkeeping_reflexes)
            if position == "GK"
            else weighted_score(player, DEFENSE_WEIGHTS)
        ),
    }

    for attribute, value in raw.items():
        if not -SCORE_TOLERANCE <= value <= ATTRIBUTE_MAX + SCORE_TOLERANCE:
            raise ValueError(
                f"Pontuação {attribute} inválida para {player.name}: {value}"
            )

    return PlayerScores(
        attack=clamp(raw["attack"]),
        defense=clamp(raw["defense"]),
        control=clamp(raw["control"]),
    )


# ============================================================
# Agregação dos 11 jogadores
# ============================================================

def aggregate_player_scores(
    players: Sequence[Player],
) -> TeamAttributes:
    """
    Agrega as pontuações individuais usando os pesos posicionais.

    Não aplica bônus de formação.
    """
    weighted_sums = {
        "attack": 0.0,
        "defense": 0.0,
        "control": 0.0,
    }
    weight_totals = {
        "attack": 0.0,
        "defense": 0.0,
        "control": 0.0,
    }

    for player in players:
        position = canonical_position(player.pos)
        position_weights = POSITION_WEIGHTS[position]
        scores = calculate_player_scores(player)

        for attribute in weighted_sums:
            weight = position_weights[attribute]

            weighted_sums[attribute] += (
                getattr(scores, attribute) * weight
            )
            weight_totals[attribute] += weight

    result = {}

    for attribute in weighted_sums:
        denominator = weight_totals[attribute]

        if denominator == 0:
            raise ValueError(
                f"Não há contribuições para o atributo {attribute}"
            )

        result[attribute] = weighted_sums[attribute] / denominator

    return TeamAttributes(**result)


# ============================================================
# Setores e validação da escalação
# ============================================================

def formation_distribution(formation: Sequence[str]) -> dict[str, int]:
    """Conta os slots (ou posições) por setor: GK, DEF, MID e FW."""
    counts = dict.fromkeys(SECTORS, 0)

    for slot in formation:
        counts[POSITION_SECTORS[canonical_position(slot)]] += 1

    return counts


def _describe_counts(counts: dict[str, int]) -> str:
    return (
        f"GK={counts['GK']} DEF={counts['DEF']} "
        f"MID={counts['MID']} FW={counts['FW']}"
    )


def validate_lineup_matches_formation(
    players: Sequence[Player],
    formation: Sequence[str],
) -> None:
    """
    Garante que a escalação é coerente com a formação.

    - a formação deve conter exatamente um goleiro;
    - a contagem de jogadores por setor deve ser igual à contagem de slots.

    A comparação é por setor, não por slot: um "RB" num slot "CB" é aceito,
    pois os modificadores de formação só dependem da contagem por setor.
    """
    formation_counts = formation_distribution(formation)

    if formation_counts["GK"] != 1:
        raise ValueError(
            "A formação deve conter exatamente um goleiro; "
            f"encontrado: {formation_counts['GK']}"
        )

    lineup_counts = formation_distribution([player.pos for player in players])

    if lineup_counts != formation_counts:
        raise ValueError(
            "A escalação não corresponde à formação: "
            f"jogadores {_describe_counts(lineup_counts)}, "
            f"formação {_describe_counts(formation_counts)}."
        )


# ============================================================
# Bônus e penalidades da formação
# ============================================================


def _formation_deltas(
    formation: Sequence[str],
    config: FormationBonusConfig,
) -> dict[str, float]:
    """Modificadores aditivos de Ataque, Defesa e Controle da formação."""
    counts = formation_distribution(formation)

    defender_delta = counts["DEF"] - config.baseline_defenders
    midfielder_delta = counts["MID"] - config.baseline_midfielders
    forward_delta = counts["FW"] - config.baseline_forwards

    return {
        "attack": (
            defender_delta * config.defender_attack
            + midfielder_delta * config.midfielder_attack
            + forward_delta * config.forward_attack
        ),
        "defense": (
            defender_delta * config.defender_defense
            + midfielder_delta * config.midfielder_defense
            + forward_delta * config.forward_defense
        ),
        "control": (
            defender_delta * config.defender_control
            + midfielder_delta * config.midfielder_control
            + forward_delta * config.forward_control
        ),
    }


def apply_formation_modifiers(
    attributes: TeamAttributes,
    formation: Sequence[str],
    config: FormationBonusConfig = DEFAULT_FORMATION_BONUS,
) -> TeamAttributes:
    """
    Aplica bônus e penalidades relativos à formação de referência (4-3-3).

    `formation` é a lista de slots (ou posições) dos 11 titulares.
    Os modificadores são aditivos e o resultado é limitado a [0, 100].
    """
    deltas = _formation_deltas(formation, config)

    return TeamAttributes(
        attack=clamp(attributes.attack + deltas["attack"]),
        defense=clamp(attributes.defense + deltas["defense"]),
        control=clamp(attributes.control + deltas["control"]),
    )


# ============================================================
# API principal
# ============================================================

def calculate_team_attributes(
    players: Sequence[Player],
    formation: Sequence[str] | None = None,
    *,
    formation_config: FormationBonusConfig | None = DEFAULT_FORMATION_BONUS,
) -> TeamAttributes:
    """
    Calcula os atributos coletivos de um time titular.

    - `formation`: slots táticos dos 11 titulares. Se omitida, é derivada
      das posições dos próprios jogadores.
    - `formation_config`: bônus de formação. Com `None`, devolve apenas
      os atributos-base (sem modificadores).

    Levanta ValueError se não houver 11 jogadores, se a formação não tiver
    11 slots, se houver jogadores duplicados ou se a escalação não for
    coerente com a formação (ver `validate_lineup_matches_formation`).
    """
    if len(players) != 11:
        raise ValueError(
            f"A escalação deve conter exatamente 11 titulares; recebido: {len(players)}"
        )

    slots = [player.pos for player in players] if formation is None else list(formation)

    if len(slots) != 11:
        raise ValueError(
            f"A formação deve conter exatamente 11 slots; recebido: {len(slots)}"
        )
    if len({player.name for player in players}) != len(players):
        raise ValueError("A escalação não pode conter jogadores duplicados.")

    validate_lineup_matches_formation(players, slots)

    base = aggregate_player_scores(players)

    if formation_config is None:
        return base

    return apply_formation_modifiers(base, slots, formation_config)




