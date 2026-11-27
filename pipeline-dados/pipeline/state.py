"""Estado persistente do autoresearch por país."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_PENDING = "pending"
STATUS_RESEARCHING = "researching"
STATUS_PROPOSED = "proposed"
STATUS_VALIDATION_FAILED = "validation_failed"
STATUS_REVIEW_REQUIRED = "review_required"
STATUS_APPROVED = "approved"
STATUS_PUBLISHED = "published"
STATUS_BLOCKED = "blocked"
ESTADOS_FINAIS = {STATUS_PUBLISHED, STATUS_BLOCKED}


def agora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def novo_manifesto(
    competicao: str,
    edicao: int,
    data_referencia: str,
    paises: list[str],
    pipeline_version: str,
    prompt_version: str,
    *,
    allow_partial_publish: bool = False,
    max_attempts: int = 3,
) -> dict[str, Any]:
    if max_attempts < 1:
        raise ValueError("max_attempts deve ser pelo menos 1")
    return {
        "schema_version": 1,
        "created_at": agora(),
        "updated_at": agora(),
        "competicao": competicao,
        "edicao": edicao,
        "data_referencia": data_referencia,
        "pipeline_version": pipeline_version,
        "prompt_version": prompt_version,
        "allow_partial_publish": allow_partial_publish,
        "max_attempts": max_attempts,
        "paises": {
            pais: {"status": STATUS_PENDING, "attempts": 0, "updated_at": agora(), "message": ""}
            for pais in paises
        },
    }


def carregar_manifesto(caminho: Path) -> dict[str, Any]:
    if not caminho.exists():
        raise FileNotFoundError(f"manifesto não encontrado: {caminho}")
    try:
        manifesto = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifesto inválido: {caminho}") from exc
    if not isinstance(manifesto.get("paises"), dict):
        raise ValueError("manifesto deve conter um objeto 'paises'")
    manifesto.setdefault("allow_partial_publish", False)
    manifesto.setdefault("max_attempts", 3)
    if not isinstance(manifesto["max_attempts"], int) or manifesto["max_attempts"] < 1:
        raise ValueError("manifesto.max_attempts deve ser inteiro positivo")
    return manifesto


def salvar_manifesto(manifesto: dict[str, Any], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    manifesto["updated_at"] = agora()
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(caminho)


def atualizar_pais(manifesto: dict[str, Any], pais: str, status: str, message: str = "", **campos: Any) -> dict[str, Any]:
    if pais not in manifesto["paises"]:
        raise KeyError(f"país não está no manifesto: {pais}")
    entrada = manifesto["paises"][pais]
    entrada.update({"status": status, "updated_at": agora(), "message": message, **campos})
    return entrada


def contar_status_pais(entrada: dict[str, Any]) -> dict[str, int]:
    return {key: int(entrada.get(key, 0)) for key in ("approved", "review_required", "rejected")}


def proxima_tarefa(manifesto: dict[str, Any]) -> tuple[str, str] | None:
    """Retoma trabalho incompleto antes de iniciar um país pendente."""
    prioridades = (
        (STATUS_RESEARCHING, "resume_research"),
        (STATUS_VALIDATION_FAILED, "retry_validation"),
        (STATUS_REVIEW_REQUIRED, "review"),
        (STATUS_PENDING, "start"),
    )
    for status, acao in prioridades:
        for pais, entrada in manifesto["paises"].items():
            if entrada.get("status") == status:
                return acao, pais
    return None


def proximo_pais(manifesto: dict[str, Any]) -> str | None:
    tarefa = proxima_tarefa(manifesto)
    return tarefa[1] if tarefa else None


def pode_tentar_novamente(manifesto: dict[str, Any], pais: str) -> bool:
    return manifesto["paises"][pais].get("attempts", 0) < manifesto.get("max_attempts", 3)


def registrar_versao(entrada: dict[str, Any], campo: str, caminho: str) -> int:
    versoes = entrada.setdefault(campo, [])
    versoes.append(caminho)
    return len(versoes)


def resumo_manifesto(manifesto: dict[str, Any]) -> dict[str, int]:
    resumo: dict[str, int] = {}
    for entrada in manifesto["paises"].values():
        status = entrada.get("status", STATUS_PENDING)
        resumo[status] = resumo.get(status, 0) + 1
    return dict(sorted(resumo.items()))


def resumo_manifesto_detalhado(manifesto: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"pais": pais, "status": entrada.get("status", STATUS_PENDING), **contar_status_pais(entrada), "attempts": entrada.get("attempts", 0)}
        for pais, entrada in manifesto["paises"].items()
    ]
