"""Orquestração determinística do autoresearch por país."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from . import __version__
from .identity import carregar_aliases, descobrir_lacunas
from .io import carregar_convocacoes, carregar_dataset, carregar_escalacao, escrever_csv
from .ancoragem import deslocamentos_por_pais
from .materialize import materializar
from .posicoes import treinar_modelo
from .research import PROMPT_VERSION, gerar_pacote, escrever_pacote
from .state import (
    STATUS_APPROVED,
    STATUS_BLOCKED,
    STATUS_PROPOSED,
    STATUS_PUBLISHED,
    STATUS_RESEARCHING,
    STATUS_REVIEW_REQUIRED,
    STATUS_VALIDATION_FAILED,
    STATUS_PENDING,
    atualizar_pais,
    carregar_manifesto,
    contar_status_pais,
    novo_manifesto,
    pode_tentar_novamente,
    proxima_tarefa,
    registrar_versao,
    salvar_manifesto,
    resumo_manifesto,
)
from .validation import carregar_propostas, validar_propostas


def iniciar_manifesto(
    caminho: Path,
    competicao: str,
    edicao: int,
    data_referencia: str,
    paises: list[str],
    *,
    allow_partial_publish: bool = False,
    max_attempts: int = 3,
) -> dict[str, Any]:
    if caminho.exists():
        return carregar_manifesto(caminho)
    (caminho.parent / "registry").mkdir(parents=True, exist_ok=True)
    manifesto = novo_manifesto(
        competicao, edicao, data_referencia, paises, __version__, PROMPT_VERSION,
        allow_partial_publish=allow_partial_publish, max_attempts=max_attempts,
    )
    salvar_manifesto(manifesto, caminho)
    return manifesto


def diretorio_pais(raiz: Path, pais: str) -> Path:
    return raiz / "execucoes" / pais.lower().replace(" ", "_")


def nome_snapshot(pais: str, edicao: int) -> str:
    return f"{pais.lower().replace(' ', '_')}_{edicao}.csv"


def _proxima_versao(destino: Path, prefixo: str, extensao: str) -> Path:
    existentes = list(destino.glob(f"{prefixo}_v*{extensao}"))
    numero = len(existentes) + 1
    return destino / f"{prefixo}_v{numero:03d}{extensao}"


def preparar_pais(
    manifesto: dict[str, Any], pais: str, dataset: Path, convocacoes: Path,
    aliases: Path | None, raiz: Path, escalacoes: Path | None = None,
) -> Path:
    if pais not in manifesto["paises"]:
        raise KeyError(f"país não está no manifesto: {pais}")
    destino = diretorio_pais(raiz, pais)
    destino.mkdir(parents=True, exist_ok=True)
    if not pode_tentar_novamente(manifesto, pais):
        raise ValueError(f"limite de tentativas atingido para {pais}")
    df = carregar_dataset(dataset)
    lista = carregar_convocacoes(convocacoes)
    lacunas = descobrir_lacunas(lista, df, carregar_aliases(aliases))
    lacunas_path = destino / "lacunas.csv"
    escrever_csv(lacunas, lacunas_path)
    escala = carregar_escalacao(escalacoes)
    pacote = gerar_pacote(df, lacunas, pais, manifesto["data_referencia"], escala)
    pacote_path = destino / "pacote.json"
    escrever_pacote(pacote, pacote_path)
    entrada = manifesto["paises"][pais]
    atualizar_pais(
        manifesto, pais, STATUS_RESEARCHING,
        message="pacote pronto; aguardando resposta externa do LLM",
        attempts=entrada.get("attempts", 0) + 1,
        input_path=str(lacunas_path), package_path=str(pacote_path),
        escalacao_path=str(escalacoes) if escalacoes else None,
    )
    return pacote_path


def _salvar_status(destino: Path, dados: dict[str, Any]) -> None:
    (destino / "status.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def validar_resposta_pais(manifesto: dict[str, Any], pais: str, raiz: Path) -> pd.DataFrame:
    destino = diretorio_pais(raiz, pais)
    resposta = destino / "resposta_bruta.json"
    if not resposta.exists():
        raise FileNotFoundError(f"resposta externa não encontrada: {resposta}")
    versao_resposta = _proxima_versao(destino, "resposta_bruta", ".json")
    shutil.copyfile(resposta, versao_resposta)
    propostas = carregar_propostas(resposta)
    validacao = pd.DataFrame(validar_propostas(propostas, pais))
    validacao_path = _proxima_versao(destino, "validacao", ".csv")
    escrever_csv(validacao, validacao_path)
    entrada = manifesto["paises"][pais]
    registrar_versao(entrada, "response_versions", str(versao_resposta))
    registrar_versao(entrada, "validation_versions", str(validacao_path))
    aprovados = int((validacao["status"] == "approved").sum()) if not validacao.empty else 0
    revisao = int((validacao["status"] != "approved").sum()) if not validacao.empty else 0
    if revisao == 0:
        status, mensagem = STATUS_PROPOSED, "proposta validada"
    elif pode_tentar_novamente(manifesto, pais):
        status, mensagem = STATUS_VALIDATION_FAILED, "há propostas inválidas; nova tentativa disponível"
    else:
        status, mensagem = STATUS_REVIEW_REQUIRED, "limite de tentativas esgotado; revisão manual necessária"
    atualizar_pais(
        manifesto, pais, status, mensagem,
        validation_path=str(validacao_path), approved=aprovados, review_required=revisao,
    )
    _salvar_status(destino, {"pais": pais, "status": status, "approved": aprovados, "review_required": revisao, "response_version": str(versao_resposta), "validation_version": str(validacao_path)})
    return validacao


def publicar_pais(
    manifesto: dict[str, Any], pais: str, dataset: Path, raiz: Path, registry: Path,
    *, allow_partial: bool = False,
) -> Path:
    destino = diretorio_pais(raiz, pais)
    entrada = manifesto["paises"].get(pais)
    if entrada is None:
        raise KeyError(f"país não está no manifesto: {pais}")
    if entrada.get("status") != STATUS_PROPOSED:
        raise ValueError(f"país não está aprovado para publicação: {entrada.get('status')}")
    if entrada.get("review_required", 0) and not (allow_partial and manifesto.get("allow_partial_publish")):
        raise ValueError("há propostas pendentes; publicação parcial precisa ser autorizada no manifesto e no comando")
    propostas = carregar_propostas(destino / "resposta_bruta.json")
    if not propostas:
        raise ValueError("nenhuma proposta para publicar")
    aprovadas = [p for p in propostas if p.get("status") == "approved"]
    if not aprovadas:
        raise ValueError("nenhuma proposta aprovada para publicar")
    saida = destino / nome_snapshot(pais, manifesto["edicao"])
    base = carregar_dataset(dataset)
    resultado = materializar(
        aprovadas, base, manifesto["data_referencia"], registry, treinar_modelo(base),
        deslocamentos_por_pais(base),
    )
    escrever_csv(resultado, saida)
    if len(resultado.columns) < 110:
        raise ValueError("snapshot publicado não preserva o schema do dataset")
    proposta_aprovada = destino / "proposta_aprovada.json"
    proposta_aprovada.write_text(json.dumps(aprovadas, ensure_ascii=False, indent=2), encoding="utf-8")
    atualizar_pais(manifesto, pais, STATUS_PUBLISHED, "snapshot publicado", output_path=str(saida), published_count=len(resultado))
    _salvar_status(destino, {"pais": pais, "status": STATUS_PUBLISHED, "published_count": len(resultado), "output_path": str(saida)})
    return saida


def proximo_passo(manifesto: dict[str, Any], raiz: Path) -> dict[str, Any]:
    tarefa = proxima_tarefa(manifesto)
    if tarefa is None:
        return {"status": "complete", "summary": resumo_manifesto(manifesto)}
    acao, pais = tarefa
    entrada = manifesto["paises"][pais]
    return {"status": "ready", "action": acao, "pais": pais, "status_pais": entrada.get("status"), "package_path": str(diretorio_pais(raiz, pais) / "pacote.json"), "response_path": str(diretorio_pais(raiz, pais) / "resposta_bruta.json")}
