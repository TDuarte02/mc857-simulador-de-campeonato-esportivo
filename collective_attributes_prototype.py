from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass


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

    @classmethod
    def from_csv_row(cls, name: str, pos: str, row: dict[str, str]) -> "Player":
        values = {key: row[key] for key in (
            "potential",
            "pace",
            "shooting",
            "passing",
            "dribbling",
            "defending",
            "physic",
            "attacking_heading_accuracy",
            "movement_agility",
            "movement_reactions",
            "movement_balance",
            "power_jumping",
            "power_stamina",
            "mentality_aggression",
            "mentality_penalties",
            "mentality_composure",
            "goalkeeping_reflexes",
        )}
        overall_value = row.get("overall", row.get("potential", values["potential"]))
        return cls(
            name=name,
            pos=pos,
            overall=int(overall_value),
            potential=int(values["potential"]),
            pace=float(values["pace"]),
            shooting=float(values["shooting"]),
            passing=float(values["passing"]),
            dribbling=float(values["dribbling"]),
            defending=float(values["defending"]),
            physic=float(values["physic"]),
            attacking_heading_accuracy=int(values["attacking_heading_accuracy"]),
            movement_agility=int(values["movement_agility"]),
            movement_reactions=int(values["movement_reactions"]),
            movement_balance=int(values["movement_balance"]),
            power_jumping=int(values["power_jumping"]),
            power_stamina=int(values["power_stamina"]),
            mentality_aggression=int(values["mentality_aggression"]),
            mentality_penalties=int(values["mentality_penalties"]),
            mentality_composure=int(values["mentality_composure"]),
            goalkeeping_reflexes=int(values["goalkeeping_reflexes"]),
        )

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


POSITION_SECTORS = {
    "GK": "goalkeeper",
    "CB": "defense",
    "FB": "defense",
    "DM": "midfield",
    "CM": "midfield",
    "AM": "midfield",
    "W": "attack",
    "ST": "attack",
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
# Cálculo das pontuações individuais
# ============================================================

def weighted_score(player, weights: dict[str, float]) -> float:
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


def calculate_player_scores(player) -> PlayerScores:
    """
    Calcula as pontuações individuais de Ataque, Defesa e Controle.

    Potential, overall, power_stamina e mentality_penalties
    não entram diretamente nos atributos coletivos.
    """
    position = canonical_position(player.pos)

    attack = weighted_score(player, ATTACK_WEIGHTS)
    control = weighted_score(player, CONTROL_WEIGHTS)

    if position == "GK":
        # O dataset disponível possui apenas um atributo específico
        # de goleiro: goalkeeping_reflexes.
        defense = float(player.goalkeeping_reflexes)
    else:
        defense = weighted_score(player, DEFENSE_WEIGHTS)

    scores = PlayerScores(
        attack=attack,
        defense=defense,
        control=control,
    )

    for attribute, value in (
        ("attack", scores.attack),
        ("defense", scores.defense),
        ("control", scores.control),
    ):
        if not 0 <= value <= 100:
            raise ValueError(
                f"Pontuação {attribute} inválida para {player.name}: {value}"
            )

    return scores


# ============================================================
# Agregação dos 11 jogadores
# ============================================================

def aggregate_player_scores(
    players: Sequence,
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
# Bônus e penalidades da formação
# ============================================================

def count_formation_sectors(players: Sequence) -> dict[str, int]:
    """Conta os jogadores por setor, excluindo o goleiro."""
    counts = {
        "goalkeeper": 0,
        "defense": 0,
        "midfield": 0,
        "attack": 0,
    }

    for player in players:
        position = canonical_position(player.pos)
        sector = POSITION_SECTORS[position]
        counts[sector] += 1

    return counts


def apply_formation_modifiers(
    attributes: TeamAttributes,
    players: Sequence,
    config: FormationBonusConfig = DEFAULT_FORMATION_BONUS,
) -> TeamAttributes:
    """
    Aplica bônus e penalidades relativos à formação de referência.

    Os modificadores são aditivos e limitados à escala [0, 100].
    """
    counts = count_formation_sectors(players)

    defender_delta = counts["defense"] - config.baseline_defenders
    midfielder_delta = counts["midfield"] - config.baseline_midfielders
    forward_delta = counts["attack"] - config.baseline_forwards

    attack_modifier = (
        defender_delta * config.defender_attack
        + midfielder_delta * config.midfielder_attack
        + forward_delta * config.forward_attack
    )

    defense_modifier = (
        defender_delta * config.defender_defense
        + midfielder_delta * config.midfielder_defense
        + forward_delta * config.forward_defense
    )

    control_modifier = (
        defender_delta * config.defender_control
        + midfielder_delta * config.midfielder_control
        + forward_delta * config.forward_control
    )

    return TeamAttributes(
        attack=max(0.0, min(100.0, attributes.attack + attack_modifier)),
        defense=max(0.0, min(100.0, attributes.defense + defense_modifier)),
        control=max(0.0, min(100.0, attributes.control + control_modifier)),
    )


# ============================================================
# ============================================================
# Agregação por formação (compatível com testes e protótipo)
# ============================================================

def formation_distribution(formation: Sequence[str]) -> dict[str, int]:
    """Conta jogadores por setor do campo conforme a formação."""
    counts = {"GK": 0, "DEF": 0, "MID": 0, "FW": 0}

    for slot in formation:
        normalized = canonical_position(slot)
        if normalized == "GK":
            counts["GK"] += 1
        elif normalized in {"CB", "FB"}:
            counts["DEF"] += 1
        elif normalized in {"DM", "CM", "AM"}:
            counts["MID"] += 1
        else:
            counts["FW"] += 1

    return counts


def collective_attributes(
    players: Sequence[Player],
    formation: Sequence[str],
) -> dict[str, float]:
    """Calcula o perfil coletivo do time para uma formação específica."""
    if len(players) != 11:
        raise ValueError(f"Collective attributes require exactly 11 starters.")
    if len(formation) != 11:
        raise ValueError("A valid tactical shape must contain 11 slots.")
    if len({player.name for player in players}) != len(players):
        raise ValueError("A lineup cannot contain duplicate players.")

    base = aggregate_player_scores(players)
    counts = formation_distribution(formation)

    defender_delta = counts["DEF"] - DEFAULT_FORMATION_BONUS.baseline_defenders
    midfielder_delta = counts["MID"] - DEFAULT_FORMATION_BONUS.baseline_midfielders
    forward_delta = counts["FW"] - DEFAULT_FORMATION_BONUS.baseline_forwards

    attack_modifier = (
        defender_delta * DEFAULT_FORMATION_BONUS.defender_attack
        + midfielder_delta * DEFAULT_FORMATION_BONUS.midfielder_attack
        + forward_delta * DEFAULT_FORMATION_BONUS.forward_attack
    )
    defense_modifier = (
        defender_delta * DEFAULT_FORMATION_BONUS.defender_defense
        + midfielder_delta * DEFAULT_FORMATION_BONUS.midfielder_defense
        + forward_delta * DEFAULT_FORMATION_BONUS.forward_defense
    )
    control_modifier = (
        defender_delta * DEFAULT_FORMATION_BONUS.defender_control
        + midfielder_delta * DEFAULT_FORMATION_BONUS.midfielder_control
        + forward_delta * DEFAULT_FORMATION_BONUS.forward_control
    )

    return {
        "attack": max(0.0, min(100.0, base.attack + attack_modifier)),
        "defense": max(0.0, min(100.0, base.defense + defense_modifier)),
        "control": max(0.0, min(100.0, base.control + control_modifier)),
    }


# API principal
# ============================================================

def calculate_team_attributes(
    players: Sequence,
    formation_config: FormationBonusConfig | None = DEFAULT_FORMATION_BONUS,
) -> TeamAttributes:
    """
    Calcula os atributos coletivos de um time titular.

    Por padrão, aplica os bônus e penalidades da formação.
    Passe formation_config=None para obter apenas os atributos-base.
    """
    if len(players) != 11:
        raise ValueError(
            f"O time deve conter exatamente 11 jogadores; recebido: {len(players)}"
        )

    goalkeeper_count = sum(
        canonical_position(player.pos) == "GK"
        for player in players
    )

    if goalkeeper_count != 1:
        raise ValueError(
            f"O time deve conter exatamente um goleiro; encontrado: "
            f"{goalkeeper_count}"
        )

    base_attributes = aggregate_player_scores(players)

    if formation_config is None:
        return base_attributes

    return apply_formation_modifiers(
        base_attributes,
        players,
        formation_config,
    )

