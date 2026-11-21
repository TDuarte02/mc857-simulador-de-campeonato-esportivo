"""Configurações compartilhadas pelo pipeline de convocados."""

from __future__ import annotations

import re
import unicodedata

SELECOES_COPA_AMERICA_2024 = (
    "Argentina", "Bolivia", "Brazil", "Canada", "Chile", "Colombia",
    "Costa Rica", "Ecuador", "Jamaica", "Mexico", "Panama", "Paraguay",
    "Peru", "United States", "Uruguay", "Venezuela",
)

POSICAO_FIFA_GRUPO = {
    "GK": "GK",
    "CB": "DEF", "LB": "DEF", "RB": "DEF", "LWB": "DEF", "RWB": "DEF",
    "DM": "MID", "CDM": "MID", "CM": "MID", "AM": "MID", "CAM": "MID",
    "LM": "MID", "RM": "MID",
    "LW": "ATT", "RW": "ATT", "ST": "ATT", "CF": "ATT",
    "LS": "ATT", "RS": "ATT", "LF": "ATT", "RF": "ATT",
}

ATRIBUTOS_LINHA = ("pace", "shooting", "passing", "dribbling", "defending", "physic")
ATRIBUTOS_GK = (
    "goalkeeping_diving", "goalkeeping_handling", "goalkeeping_kicking",
    "goalkeeping_positioning", "goalkeeping_reflexes", "goalkeeping_speed",
)
ATRIBUTOS_NUMERICOS = ("overall",) + ATRIBUTOS_LINHA + ATRIBUTOS_GK
COLUNAS_CONVOCACAO = ("pais", "nome", "posicao", "fonte_url")
COLUNAS_ESCALACAO = ("pais", "data", "fase", "adversario", "nome", "posicao", "ordem", "fonte_url")
FONTE_URLS = ("fonte_url", "url")
COLUNAS_RASTREIO = (
    "is_historico", "origem_registro", "fonte_atributos", "fonte_validacao",
    "observacao", "validacao_via", "data_referencia", "status_validacao", "confianca",
)


def normalizar_nome(nome: object) -> str:
    """Normaliza nome para matching, preservando apenas letras, números e espaços."""
    sem_acento = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", sem_acento.lower()).strip()


def slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalizar_nome(nome)).strip("_")


def grupo_posicao(posicao: object) -> str | None:
    """Retorna GK/DEF/MID/ATT para a posição principal ou primeira posição."""
    for token in str(posicao or "").upper().split(","):
        token = token.strip()
        if token in POSICAO_FIFA_GRUPO:
            return POSICAO_FIFA_GRUPO[token]
    return None
