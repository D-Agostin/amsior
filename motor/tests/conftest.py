# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
from __future__ import annotations

import string

import pytest

from amsior.expr import Simbolo, TabelaDeSimbolos
from amsior.units import Glossario, carregar_glossario

MULTILETRAS = ("Re", "Nu", "Pr", "Bi", "Sh", "Sc", "Gr", "Da", "Pe", "NTU", "Fo", "Ra")


def tabela_corpus(funcoes: tuple[str, ...] = ()) -> TabelaDeSimbolos:
    """Todas as letras isoladas, os números adimensionais usuais e as funções pedidas."""
    t = TabelaDeSimbolos()
    for c in string.ascii_letters:
        t.adicionar(Simbolo(c))
    for p in MULTILETRAS:
        t.adicionar(Simbolo(f"\\mathrm{{{p}}}"))
    for f in funcoes:
        t.adicionar(Simbolo(f, papel="funcao"))
    return t


@pytest.fixture(scope="session")
def glossario() -> Glossario:
    return carregar_glossario()
