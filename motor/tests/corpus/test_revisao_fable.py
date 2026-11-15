# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Achados da revisão 0001 na camada V2 (docs/revisoes/0001-verificador-fase-1a.md).

Os achados de passo (A1 a A14) estão no corpus de ataque, em
``passos_ataque.ERRADOS_REVISAO``. Aqui ficam as soluções falsas que a camada
V2 aceitava por não conhecer o domínio da equação original.
"""

from __future__ import annotations

import pytest

from amsior.expr import Sym, TabelaDeSimbolos, analisar
from amsior.units import Glossario
from amsior.verify.certificador import Verificador
from tests.corpus.passos_ataque import tabelas

# (equação, solução falsa de x)
V2_FALSAS: list[tuple[str, str]] = [
    (r"\frac{(x-1)(x+1)}{x-1} = 2", "1"),
    (r"x \cdot \frac{1}{x} = 1", "0"),
    (r"e^{\ln x} = -3", "-3"),
    (r"(\sqrt{x})^2 = -4", "-4"),
]


@pytest.fixture(scope="module")
def tabs(glossario: Glossario) -> dict[str, TabelaDeSimbolos]:
    return tabelas(glossario)


@pytest.mark.parametrize(("equacao", "solucao"), V2_FALSAS, ids=[e for e, _ in V2_FALSAS])
def test_v2_recusa_solucao_fora_do_dominio(equacao: str, solucao: str,
                                           tabs: dict[str, TabelaDeSimbolos],
                                           glossario: Glossario) -> None:
    tab = tabs["geral"]
    x = analisar("x", tab)
    assert isinstance(x, Sym)
    r = Verificador(tab, glossario).verificar_solucao(
        analisar(equacao, tab), x, analisar(solucao, tab))
    assert not r.aprovado
    assert r.motivo == "verif.solucao_fora_do_dominio"


def test_v2_aceita_a_solucao_verdadeira(tabs: dict[str, TabelaDeSimbolos],
                                        glossario: Glossario) -> None:
    tab = tabs["geral"]
    r = Verificador(tab, glossario).verificar_solucao(
        analisar(r"\frac{(x-1)(x+1)}{x-1} = 3", tab), Sym("x"), analisar("2", tab))
    assert r.aprovado
