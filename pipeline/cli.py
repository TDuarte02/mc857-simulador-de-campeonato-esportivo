"""CLI do pipeline de convocados."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .identity import carregar_aliases, descobrir_lacunas
from .io import carregar_convocacoes, carregar_dataset, escrever_csv
from .materialize import materializar
from .report import consolidar_resumo, mesclar_publicados
from .research import gerar_pacote, escrever_pacote
from .runner import (
    iniciar_manifesto,
    preparar_pais,
    proximo_passo,
    publicar_pais,
    validar_resposta_pais,
)
from .state import carregar_manifesto, salvar_manifesto, resumo_manifesto
from .validation import carregar_propostas, validar_propostas

REGISTRY_PADRAO = Path("dados/autoresearch/registry/player_ids.csv")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    discover = sub.add_parser("discover", help="compara convocados com a base")
    discover.add_argument("--dataset", type=Path, required=True)
    discover.add_argument("--convocations", type=Path, required=True)
    discover.add_argument("--aliases", type=Path)
    discover.add_argument("--output", type=Path, required=True)

    package = sub.add_parser("package", help="gera pacote de pesquisa e calibração")
    package.add_argument("--dataset", type=Path, required=True)
    package.add_argument("--gaps", type=Path, required=True)
    package.add_argument("--pais", required=True)
    package.add_argument("--data-referencia", required=True)
    package.add_argument("--output", type=Path, required=True)

    validate = sub.add_parser("validate", help="valida resposta JSON do LLM")
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--pais", required=True)
    validate.add_argument("--output", type=Path, required=True)

    material = sub.add_parser("materialize", help="materializa propostas aprovadas")
    material.add_argument("--dataset", type=Path, required=True)
    material.add_argument("--input", type=Path, required=True)
    material.add_argument("--pais", required=True)
    material.add_argument("--data-referencia", required=True)
    material.add_argument("--registry", type=Path, default=REGISTRY_PADRAO)
    material.add_argument("--output", type=Path, required=True)

    init = sub.add_parser("init-run", help="cria ou carrega manifesto global")
    init.add_argument("--manifest", type=Path, required=True)
    init.add_argument("--competicao", default="Copa América")
    init.add_argument("--edicao", type=int, required=True)
    init.add_argument("--data-referencia", required=True)
    init.add_argument("--paises", nargs="+", required=True)

    prepare = sub.add_parser("prepare-country", help="prepara uma iteração isolada")
    prepare.add_argument("--manifest", type=Path, required=True)
    prepare.add_argument("--pais", required=True)
    prepare.add_argument("--dataset", type=Path, required=True)
    prepare.add_argument("--convocations", type=Path, required=True)
    prepare.add_argument("--aliases", type=Path)
    prepare.add_argument("--escalacoes", type=Path, help="escalação da última partida do país")
    prepare.add_argument("--state-dir", type=Path, required=True)

    resume = sub.add_parser("validate-country", help="valida a resposta bruta do país")
    resume.add_argument("--manifest", type=Path, required=True)
    resume.add_argument("--pais", required=True)
    resume.add_argument("--state-dir", type=Path, required=True)

    publish = sub.add_parser("publish-country", help="materializa e publica o snapshot do país")
    publish.add_argument("--manifest", type=Path, required=True)
    publish.add_argument("--pais", required=True)
    publish.add_argument("--dataset", type=Path, required=True)
    publish.add_argument("--registry", type=Path, default=REGISTRY_PADRAO)
    publish.add_argument("--allow-partial", action="store_true", help="publica mesmo com jogadores em revisão manual (requer allow_partial_publish no manifesto)")
    publish.add_argument("--state-dir", type=Path, required=True)

    nxt = sub.add_parser("next-country", help="mostra o próximo país pendente")
    nxt.add_argument("--manifest", type=Path, required=True)
    nxt.add_argument("--state-dir", type=Path, required=True)

    report = sub.add_parser("report", help="gera o resumo consolidado da execução")
    report.add_argument("--manifest", type=Path, required=True)
    report.add_argument("--state-dir", type=Path, help="diretório com execucoes/ para contar convocados/presentes/ausentes")
    report.add_argument("--output", type=Path, required=True)

    merge = sub.add_parser("merge-final", help="concatena os snapshots publicados")
    merge.add_argument("--manifest", type=Path, required=True)
    merge.add_argument("--state-dir", type=Path, required=True)
    merge.add_argument("--output", type=Path, required=True)
    return parser


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _run_orchestration(args: argparse.Namespace) -> int | None:
    if args.comando == "init-run":
        manifesto = iniciar_manifesto(args.manifest, args.competicao, args.edicao, args.data_referencia, args.paises)
        _print_json({"manifest": str(args.manifest), "summary": resumo_manifesto(manifesto)})
        return 0
    if args.comando == "prepare-country":
        manifesto = carregar_manifesto(args.manifest)
        pacote = preparar_pais(
            manifesto, args.pais, args.dataset, args.convocations, args.aliases,
            args.state_dir, escalacoes=args.escalacoes,
        )
        salvar_manifesto(manifesto, args.manifest)
        _print_json({"pais": args.pais, "package_path": str(pacote), "response_path": str(pacote.parent / "resposta_bruta.json")})
        return 0
    if args.comando == "validate-country":
        manifesto = carregar_manifesto(args.manifest)
        resultado = validar_resposta_pais(manifesto, args.pais, args.state_dir)
        salvar_manifesto(manifesto, args.manifest)
        _print_json({"pais": args.pais, "approved": int((resultado["status"] == "approved").sum()), "total": len(resultado), "manifest_status": manifesto["paises"][args.pais]["status"]})
        return 0 if (resultado["status"] == "approved").all() else 2
    if args.comando == "publish-country":
        manifesto = carregar_manifesto(args.manifest)
        saida = publicar_pais(
            manifesto, args.pais, args.dataset, args.state_dir, args.registry,
            allow_partial=args.allow_partial,
        )
        salvar_manifesto(manifesto, args.manifest)
        _print_json({"pais": args.pais, "output_path": str(saida), "manifest_status": manifesto["paises"][args.pais]["status"]})
        return 0
    if args.comando == "next-country":
        manifesto = carregar_manifesto(args.manifest)
        _print_json(proximo_passo(manifesto, args.state_dir))
        return 0
    if args.comando == "report":
        manifesto = carregar_manifesto(args.manifest)
        escrever_csv(consolidar_resumo(manifesto, args.state_dir), args.output)
        return 0
    if args.comando == "merge-final":
        manifesto = carregar_manifesto(args.manifest)
        escrever_csv(mesclar_publicados(manifesto, args.state_dir), args.output)
        return 0
    return None


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.comando == "discover":
        resultado = descobrir_lacunas(carregar_convocacoes(args.convocations), carregar_dataset(args.dataset), carregar_aliases(args.aliases))
        escrever_csv(resultado, args.output)
        return 0
    if args.comando == "package":
        dataset = carregar_dataset(args.dataset)
        lacunas = carregar_convocacoes(args.gaps)
        escrever_pacote(gerar_pacote(dataset, lacunas, args.pais, args.data_referencia), args.output)
        return 0
    if args.comando == "validate":
        propostas = carregar_propostas(args.input)
        resultado = validar_propostas(propostas, args.pais)
        escrever_csv(pd.DataFrame(resultado), args.output)
        return 0 if all(item["status"] == "approved" for item in resultado) else 2
    orchestration_result = _run_orchestration(args)
    if orchestration_result is not None:
        return orchestration_result
    if args.comando == "materialize":
        propostas = carregar_propostas(args.input)
        validacao = validar_propostas(propostas, args.pais)
        if any(item["status"] != "approved" for item in validacao):
            raise ValueError("há propostas inválidas; execute validate e corrija antes de materializar")
        resultado = materializar(propostas, carregar_dataset(args.dataset), args.data_referencia, args.registry)
        escrever_csv(resultado, args.output)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
