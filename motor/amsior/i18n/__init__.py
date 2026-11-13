# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Catálogo de textos por idioma.

Nenhum texto de interface, de erro ou de justificativa fica no código: o código
usa chaves (``erro.analise.fim_inesperado``) e este módulo devolve o texto no
idioma pedido, com os argumentos substituídos.
"""

from __future__ import annotations

import json
import string
from functools import cache
from pathlib import Path

IDIOMA_PADRAO = "pt-BR"
IDIOMAS = ("pt-BR", "en")
_PASTA = Path(__file__).parent


class ChaveAusente(KeyError):
    pass


@cache
def catalogo(idioma: str = IDIOMA_PADRAO) -> dict[str, str]:
    caminho = _PASTA / f"{idioma}.json"
    if not caminho.exists():
        raise ValueError(f"idioma sem catálogo: {idioma}")
    dados: dict[str, str] = json.loads(caminho.read_text(encoding="utf-8"))
    return dados


def campos(modelo: str) -> set[str]:
    """Nomes dos argumentos ``{x}`` usados num modelo de texto."""
    return {nome for _, nome, _, _ in string.Formatter().parse(modelo) if nome}


def t(chave: str, idioma: str = IDIOMA_PADRAO, **args: object) -> str:
    """Texto da ``chave`` no ``idioma``; cai para pt-BR se faltar no outro idioma."""
    cat = catalogo(idioma)
    modelo = cat.get(chave)
    if modelo is None and idioma != IDIOMA_PADRAO:
        modelo = catalogo(IDIOMA_PADRAO).get(chave)
    if modelo is None:
        raise ChaveAusente(chave)
    return modelo.format(**args)
