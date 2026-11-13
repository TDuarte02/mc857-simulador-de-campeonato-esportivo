"""OpenAPI 3.1 description of the HTTP API, served at /openapi.json and shown at /docs.

Hand-written, but enums come from the domain models and the tests check every
response the API sends against these schemas (tests/openapi_check.py), so the
document cannot silently drift from the code.
"""

from functools import cache

from api.domain.models import (
    GROUP_NAMES,
    CardType,
    Federation,
    NextStep,
    Phase,
    Placement,
    Position,
    Stage,
    UnavailableReason,
)

INT = {"type": "integer"}
STR = {"type": "string"}
BOOL = {"type": "boolean"}

# Valid ids in the mock data: Brazil's "current" preset and an XI picked from it.
EXAMPLE_CALL_UP = [301, 302, 303, *range(306, 314), *range(318, 326), *range(330, 337)]
EXAMPLE_LINEUP = [301, 306, 307, 308, 309, 318, 319, 320, 321, 330, 331]


def _ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def _enum(values) -> dict:
    return {"type": "string", "enum": [str(value) for value in values]}


def _array(items: dict, **extra) -> dict:
    return {"type": "array", "items": items, **extra}


def _nullable(schema: dict) -> dict:
    if "$ref" in schema:
        return {"anyOf": [schema, {"type": "null"}]}
    nullable = {**schema, "type": [schema["type"], "null"]}
    if "enum" in schema:
        nullable["enum"] = [*schema["enum"], None]
    return nullable


def _obj(properties: dict, required: list[str] | None = None, **extra) -> dict:
    """An object with exactly these fields; all of them required unless stated."""
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
        **extra,
    }


_SQUAD = {
    "id": {**STR, "example": "brazil"},
    "name": {**STR, "example": "Brasil"},
    "flag": {**STR, "format": "uri", "example": "https://flagcdn.com/w320/br.png"},
    "federation": _enum(Federation),
}
_PLAYER = {
    "id": {**INT, "example": 301},
    "name": STR,
    "age": INT,
    "position": _enum(Position),
    "overall": {**INT, "description": "Força geral do jogador (0–99)."},
}
_EVENT = {
    "minute": INT,
    "squad": {**STR, "description": "Id da seleção do jogador."},
    "player": _ref("EventPlayer"),
}

SCHEMAS = {
    "Squad": _obj(_SQUAD),
    "Player": _obj(_PLAYER),
    "Preset": _obj(
        {
            "id": _enum(["current", "legends", "random"]),
            "name": STR,
            "description": STR,
            "players": _array(_ref("Player")),
        }
    ),
    "SessionCreated": _obj({"sessionId": {**STR, "format": "uuid"}}),
    "PlayerStatus": _obj(
        {
            "yellowCards": {**INT, "description": "Amarelos acumulados."},
            "suspendedMatches": INT,
            "suspensionReason": _nullable(_enum([UnavailableReason.SUSPENDED_RED, UnavailableReason.SUSPENDED_YELLOWS])),
            "injuredMatches": INT,
            "available": BOOL,
            "matchesRemaining": {**INT, "description": "Partidas que ainda vai perder (0 se disponível)."},
        }
    ),
    "SessionState": _obj(
        {
            "id": {**STR, "format": "uuid"},
            "createdAt": {**STR, "format": "date-time"},
            "phase": _enum(Phase),
            "squadId": _nullable({**STR, "description": "null até a convocação."}),
            "callUp": _array(INT, description="Ids dos 26 convocados; vazio até a convocação."),
            "playerStatus": {
                "type": "object",
                "description": "Situação de cada convocado, indexada pelo id do jogador (como string).",
                "additionalProperties": _ref("PlayerStatus"),
            },
            "round": {**INT, "description": "Rodadas já jogadas (0–6)."},
            "userEliminated": BOOL,
        }
    ),
    "CallUpRequest": _obj(
        {
            "squad": {**STR, "description": "Id da seleção do usuário.", "example": "brazil"},
            "players": _array(
                INT,
                minItems=26,
                maxItems=26,
                description="Ids dos 26 convocados: 3 GK, 8 DEF, 8 MID e 7 FW.",
                example=EXAMPLE_CALL_UP,
            ),
        }
    ),
    "CallUp": _obj({"sessionId": STR, "squad": _ref("Squad"), "players": _array(_ref("Player"))}),
    "DrawSquad": _obj({**_SQUAD, "players": _array(_ref("Player"), description="Os 26 jogadores que a seleção leva à copa.")}),
    "DrawGroup": _obj({"name": _enum(GROUP_NAMES), "squads": _array(_ref("DrawSquad"))}),
    "Draw": _obj(
        {
            "userSquad": _ref("Squad"),
            "groups": _array(_ref("DrawGroup")),
            "matches": _array(_ref("Match"), description="Tabela da fase de grupos, ainda sem resultados."),
        }
    ),
    "AvailablePlayer": _obj({**_PLAYER, "yellowCards": {**INT, "description": "Amarelos acumulados."}}),
    "UnavailablePlayer": _obj(
        {**_PLAYER, "reason": _enum(UnavailableReason), "matchesRemaining": {**INT, "description": "Partidas que ainda vai perder."}}
    ),
    "Availability": _obj(
        {"available": _array(_ref("AvailablePlayer")), "unavailable": _array(_ref("UnavailablePlayer"))}
    ),
    "SimulateRequest": _obj(
        {
            "players": _array(
                INT,
                minItems=11,
                maxItems=11,
                description="Os 11 titulares, todos convocados e disponíveis, com exatamente 1 goleiro.",
                example=EXAMPLE_LINEUP,
            ),
            "formation": {**STR, "description": "Repassada ao modelo.", "example": "4-4-2"},
        },
        required=["players"],
    ),
    "EventPlayer": _obj({"id": INT, "name": STR}),
    "Goal": _obj(_EVENT),
    "Card": _obj({**_EVENT, "type": _enum(CardType)}),
    "Injury": _obj({**_EVENT, "matchesOut": {**INT, "description": "Partidas que o jogador vai perder."}}),
    "Penalties": _obj({"home": INT, "away": INT}),
    "MatchResult": _obj(
        {
            "homeGoals": INT,
            "awayGoals": INT,
            "penalties": _nullable(_ref("Penalties")),
            "winner": _nullable({**STR, "description": "Id da seleção vencedora; null em empate na fase de grupos."}),
            "goals": _array(_ref("Goal")),
            "cards": _array(_ref("Card")),
            "injuries": _array(_ref("Injury")),
        }
    ),
    "Match": _obj(
        {
            "id": {**STR, "example": "G-A-R1-1"},
            "stage": _enum(Stage),
            "round": {**INT, "description": "1–3: grupos, 4: quartas, 5: semifinal, 6: final e 3º lugar."},
            "group": _nullable(_enum(GROUP_NAMES)),
            "home": _ref("Squad"),
            "away": _ref("Squad"),
            "played": BOOL,
            "result": _nullable(_ref("MatchResult")),
        },
        description="`result` só aparece depois que a rodada da partida foi jogada.",
    ),
    "NextStep": _obj(
        {
            "step": _enum(NextStep),
            "stage": _nullable(_enum(Stage)),
            "round": _nullable(INT),
            "opponent": _nullable(_ref("Squad")),
        },
        description="O que fazer depois da partida. `stage`, `round` e `opponent` só vêm com NEXT_ROUND e THIRD_PLACE_MATCH.",
    ),
    "SimulationOutcome": _obj({"match": _ref("Match"), "next": _ref("NextStep")}),
    "Standing": _obj(
        {
            "squad": _ref("Squad"),
            "played": INT,
            "won": INT,
            "drawn": INT,
            "lost": INT,
            "goalsFor": INT,
            "goalsAgainst": INT,
            "goalDifference": INT,
            "points": INT,
            "yellowCards": INT,
            "redCards": INT,
        }
    ),
    "GroupTable": _obj({"name": _enum(GROUP_NAMES), "standings": _array(_ref("Standing"))}),
    "Podium": _obj(
        {"champion": _ref("Squad"), "runnerUp": _ref("Squad"), "third": _ref("Squad"), "fourth": _ref("Squad")}
    ),
    "RoundResults": _obj(
        {
            "round": INT,
            "stage": _enum(Stage),
            "matches": _array(_ref("Match")),
            "groups": _nullable(_array(_ref("GroupTable"), description="Só na fase de grupos.")),
            "qualified": _nullable(_array(_ref("Squad"), description="Só depois da 3ª rodada de grupos.")),
            "advanced": _nullable(_array(_ref("Squad"), description="Só em quartas e semifinal.")),
            "podium": _nullable(_ref("Podium")),
        }
    ),
    "PlayoffsDraw": _obj({"qualified": _array(_ref("Squad")), "quarterFinals": _array(_ref("Match"))}),
    "Bracket": _obj(
        {
            "quarterFinals": _array(_ref("Match")),
            "semiFinals": _array(_ref("Match")),
            "thirdPlace": _nullable(_ref("Match")),
            "final": _nullable(_ref("Match")),
        }
    ),
    "History": _obj(
        {
            "sessionId": STR,
            "phase": _enum(Phase),
            "userSquad": _nullable(_ref("Squad")),
            "placement": _nullable({**_enum(Placement), "description": "null enquanto o usuário está na copa."}),
            "podium": _nullable(_ref("Podium")),
            "groups": _array(_ref("GroupTable")),
            "bracket": _ref("Bracket"),
            "userPath": _array(_ref("Match"), description="Partidas jogadas pela seleção do usuário."),
            "matches": _array(_ref("Match"), description="Todas as partidas já jogadas."),
        }
    ),
}

_SESSION_ID = {
    "name": "sessionId",
    "in": "path",
    "required": True,
    "description": "Id devolvido por `POST /session`.",
    "schema": {**STR, "format": "uuid"},
}
_SQUAD_ID = {
    "name": "squadId",
    "in": "path",
    "required": True,
    "description": "Id da seleção (veja `GET /squads`).",
    "schema": {**STR, "example": "brazil"},
}
_POSITION = {
    "name": "position",
    "in": "query",
    "required": False,
    "description": "Filtra por posição (maiúsculas ou minúsculas).",
    "schema": _enum(Position),
}


def _json(schema: dict) -> dict:
    return {"application/json": {"schema": schema}}


def _ok(description: str, schema: dict, status: int = 200) -> tuple[str, dict]:
    return str(status), {"description": description, "content": _json(schema)}


def _error(status: int, codes: list[str]) -> tuple[str, dict]:
    """An error response; `error.code` is one of `codes`."""
    titles = {400: "Corpo ou parâmetro inválido", 404: "Não encontrado", 409: "Etapa errada da sessão"}
    schema = _obj({"error": _obj({"code": _enum(codes), "message": STR})})
    listed = ", ".join(f"`{code}`" for code in codes)
    return str(status), {"description": f"{titles[status]}: {listed}.", "content": _json(schema)}


def _operation(operation_id: str, tag: str, summary: str, description: str, responses: list, **extra) -> dict:
    return {
        "operationId": operation_id,
        "tags": [tag],
        "summary": summary,
        "description": description,
        "responses": dict(responses),
        **extra,
    }


def _body(schema_name: str) -> dict:
    return {"required": True, "content": _json(_ref(schema_name))}


_SESSION = "Sessão"
_CATALOGUE = "Catálogo"
_SETUP = "Preparação"
_LOOP = "Loop de partidas"
_ENDGAME = "Mata-mata e encerramento"

PATHS = {
    "/session": {
        "post": _operation(
            "createSession",
            _SESSION,
            "Cria uma sessão",
            "Não há autenticação: o `sessionId` devolvido identifica o usuário nas outras chamadas.",
            [_ok("Sessão criada.", _ref("SessionCreated"), status=201)],
        )
    },
    "/session/{sessionId}": {
        "get": _operation(
            "getSession",
            _SESSION,
            "Estado da sessão",
            "Fase atual, seleção e convocação do usuário, rodadas jogadas e a situação de cada convocado.",
            [_ok("Sessão.", _obj({"session": _ref("SessionState")})), _error(404, ["SESSION_NOT_FOUND"])],
            parameters=[_SESSION_ID],
        )
    },
    "/squads": {
        "get": _operation(
            "listSquads",
            _CATALOGUE,
            "Lista as seleções",
            "As 16 seleções disponíveis.",
            [_ok("Seleções.", _obj({"squads": _array(_ref("Squad"))}))],
        )
    },
    "/{squadId}/players": {
        "get": _operation(
            "listPlayers",
            _CATALOGUE,
            "Lista os jogadores de uma seleção",
            "Todos os jogadores da seleção, opcionalmente filtrados por posição.",
            [
                _ok("Jogadores.", _obj({"players": _array(_ref("Player"))})),
                _error(400, ["INVALID_POSITION"]),
                _error(404, ["SQUAD_NOT_FOUND"]),
            ],
            parameters=[_SQUAD_ID, _POSITION],
        )
    },
    "/{squadId}/presets": {
        "get": _operation(
            "listPresets",
            _CATALOGUE,
            "Convocações prontas",
            "Três convocações válidas de 26 jogadores: elenco atual, lendas e aleatória.",
            [_ok("Presets.", _obj({"presets": _array(_ref("Preset"))})), _error(404, ["SQUAD_NOT_FOUND"])],
            parameters=[_SQUAD_ID],
        )
    },
    "/{sessionId}/call-up": {
        "post": _operation(
            "callUp",
            _SETUP,
            "Envia a convocação",
            "Define a seleção do usuário e seus 26 jogadores. Pode ser reenviada até o sorteio.",
            [
                _ok("Convocação aceita.", _ref("CallUp")),
                _error(400, ["INVALID_BODY", "INVALID_CALL_UP"]),
                _error(404, ["SESSION_NOT_FOUND", "SQUAD_NOT_FOUND"]),
                _error(409, ["DRAW_ALREADY_DONE"]),
            ],
            parameters=[_SESSION_ID],
            requestBody=_body("CallUpRequest"),
        )
    },
    "/{sessionId}/draw": {
        "get": _operation(
            "drawGroups",
            _SETUP,
            "Sorteia os grupos",
            "Na primeira chamada sorteia 4 grupos de 4, escolhe o elenco das outras 15 seleções e monta a "
            "tabela; as partidas sem o usuário já são simuladas, mas ficam ocultas até a rodada delas. "
            "Chamadas seguintes devolvem o mesmo sorteio.",
            [
                _ok("Sorteio.", _ref("Draw")),
                _error(404, ["SESSION_NOT_FOUND"]),
                _error(409, ["CALL_UP_REQUIRED"]),
            ],
            parameters=[_SESSION_ID],
        )
    },
    "/{sessionId}/available-players": {
        "get": _operation(
            "availablePlayers",
            _LOOP,
            "Jogadores disponíveis",
            "Os convocados que podem jogar a próxima partida e os suspensos ou lesionados.",
            [
                _ok("Disponibilidade.", _ref("Availability")),
                _error(404, ["SESSION_NOT_FOUND"]),
                _error(409, ["CALL_UP_REQUIRED"]),
            ],
            parameters=[_SESSION_ID],
        )
    },
    "/{sessionId}/simulate": {
        "post": _operation(
            "simulateMatch",
            _LOOP,
            "Simula a partida da rodada",
            "Joga a partida do usuário na rodada atual e fecha a rodada. `next.step` diz o que fazer depois.",
            [
                _ok("Resultado da partida.", _ref("SimulationOutcome")),
                _error(400, ["INVALID_BODY", "INVALID_LINEUP", "PLAYER_UNAVAILABLE"]),
                _error(404, ["SESSION_NOT_FOUND"]),
                _error(409, ["DRAW_REQUIRED", "PLAYOFFS_DRAW_REQUIRED", "USER_ELIMINATED", "TOURNAMENT_FINISHED"]),
            ],
            parameters=[_SESSION_ID],
            requestBody=_body("SimulateRequest"),
        )
    },
    "/{sessionId}/round-results": {
        "get": _operation(
            "roundResults",
            _LOOP,
            "Resultados da rodada",
            "Todos os jogos da rodada que acabou de ser jogada, com a classificação dos grupos ou quem avançou.",
            [
                _ok("Resultados.", _ref("RoundResults")),
                _error(404, ["SESSION_NOT_FOUND"]),
                _error(409, ["NO_ROUND_PLAYED"]),
            ],
            parameters=[_SESSION_ID],
        )
    },
    "/{sessionId}/playoffs-draw": {
        "get": _operation(
            "drawPlayoffs",
            _ENDGAME,
            "Sorteia o mata-mata",
            "Sorteia as quartas entre os 8 classificados. QF1 × QF2 e QF3 × QF4 se encontram nas semifinais. "
            "Chamadas seguintes devolvem o mesmo chaveamento.",
            [
                _ok("Quartas de final.", _ref("PlayoffsDraw")),
                _error(404, ["SESSION_NOT_FOUND"]),
                _error(409, ["GROUP_STAGE_NOT_FINISHED"]),
            ],
            parameters=[_SESSION_ID],
        )
    },
    "/{sessionId}/simulate-all": {
        "post": _operation(
            "simulateAll",
            _ENDGAME,
            "Simula o resto da copa",
            "Só depois que o usuário foi eliminado. Devolve o mesmo que `GET /{sessionId}/history`.",
            [
                _ok("Histórico da copa encerrada.", _ref("History")),
                _error(404, ["SESSION_NOT_FOUND"]),
                _error(409, ["DRAW_REQUIRED", "USER_STILL_PLAYING"]),
            ],
            parameters=[_SESSION_ID],
        )
    },
    "/{sessionId}/history": {
        "get": _operation(
            "history",
            _ENDGAME,
            "Histórico da sessão",
            "Classificação dos grupos, chaveamento, todas as partidas jogadas, o caminho do usuário e a colocação final.",
            [_ok("Histórico.", _ref("History")), _error(404, ["SESSION_NOT_FOUND"])],
            parameters=[_SESSION_ID],
        )
    },
}


@cache
def openapi_spec() -> dict:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Simulador de Campeonato",
            "version": "0.1.0",
            "description": (
                "API do simulador de copa (MC857).\n\n"
                "Fluxo: `POST /session` → catálogo → `POST /{sessionId}/call-up` → `GET /{sessionId}/draw` → "
                "loop de partidas (`available-players` → `simulate` → `round-results`) → `playoffs-draw` quando "
                "a fase de grupos acaba → `history`. Se o usuário for eliminado, `simulate-all` encerra a copa.\n\n"
                "Erros têm sempre o formato `{\"error\": {\"code\", \"message\"}}`."
            ),
        },
        "servers": [{"url": "/", "description": "Este servidor"}],
        "tags": [
            {"name": _SESSION},
            {"name": _CATALOGUE},
            {"name": _SETUP, "description": "Convocação e sorteio dos grupos."},
            {"name": _LOOP, "description": "Repetido a cada rodada."},
            {"name": _ENDGAME},
        ],
        "paths": PATHS,
        "components": {"schemas": SCHEMAS},
    }
