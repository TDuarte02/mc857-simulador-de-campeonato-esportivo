"""Validação leve de URLs de fontes, sem scraping obrigatório."""

from __future__ import annotations

from urllib.parse import urlparse


def validar_url(url: object) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return "URL ausente"
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "URL deve usar http ou https"
    return None


def validar_fontes(fontes: object) -> list[str]:
    if not isinstance(fontes, list) or not fontes:
        return ["ao menos uma fonte é obrigatória"]
    erros = []
    for indice, fonte in enumerate(fontes):
        if not isinstance(fonte, dict):
            erros.append(f"fonte {indice} deve ser objeto")
            continue
        erro = validar_url(fonte.get("url"))
        if erro:
            erros.append(f"fonte {indice}: {erro}")
        if not str(fonte.get("afirmacao", "")).strip():
            erros.append(f"fonte {indice}: afirmação ausente")
    return erros
