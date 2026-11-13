# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Propriedade: para toda árvore válida, analisar(para_latex(e)) == e."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from amsior.expr import (
    Abs, Add, Cos, Deriv, Div, Eq, Exp, Expr, Func, Ge, Integral, Le, Ln, Log, Lt, Mul, Ne,
    Neg, Num, PDeriv, Pow, Root, Sin, Sqrt, Sub, Sym, Tan, analisar, de_json, para_json,
    para_latex,
)
from tests.conftest import tabela_corpus

TAB = tabela_corpus(("f",))
SIMBOLOS = [
    "x", "y", "a", "b", "d", "e", "T_{1}", "T'", "P^{\\mathrm{sat}}", "\\Delta H_{\\mathrm{vap}}",
    "\\mathrm{Re}", "\\rho", "\\dot{m}", "C_{p}", "y_{A}^{*}", "B^{(0)}", "\\pi", "x_{\\mathrm{in}}",
]
VARIAVEIS = [Sym(s) for s in ("x", "t", "T", "z")]
NUMEROS = ["0", "1", "2", "3", "10", "0.5", "2.75", "101325"]

folhas = st.one_of(st.sampled_from(NUMEROS).map(Num), st.sampled_from(SIMBOLOS).map(Sym))
variaveis = st.sampled_from(VARIAVEIS)


def _compostas(filhos: st.SearchStrategy[Expr]) -> st.SearchStrategy[Expr]:
    lista = st.lists(filhos, min_size=2, max_size=3).map(tuple)
    return st.one_of(
        lista.map(Add), lista.map(Mul),
        st.builds(Sub, filhos, filhos), st.builds(Neg, filhos),
        st.builds(Div, filhos, filhos), st.builds(Pow, filhos, filhos),
        st.builds(Sqrt, filhos), st.builds(Root, filhos, filhos),
        st.builds(Exp, filhos), st.builds(Ln, filhos), st.builds(Log, filhos, filhos),
        st.builds(Sin, filhos), st.builds(Cos, filhos), st.builds(Tan, filhos),
        st.builds(Abs, filhos),
        st.builds(lambda a: Func("f", (a,)), filhos),
        st.builds(Deriv, filhos, variaveis, st.integers(1, 3)),
        st.builds(PDeriv, filhos, variaveis,
                  st.lists(variaveis, max_size=2, unique=True).map(tuple), st.integers(1, 2)),
        st.builds(Integral, filhos, variaveis),
        st.builds(lambda f, v, a, b: Integral(f, v, a, b), filhos, variaveis, filhos, filhos),
    )


expressoes = st.recursive(folhas, _compostas, max_leaves=12)
relacoes = st.one_of(
    expressoes,
    st.builds(Eq, expressoes, expressoes), st.builds(Ne, expressoes, expressoes),
    st.builds(Ge, expressoes, expressoes), st.builds(Le, expressoes, expressoes),
    st.builds(Lt, expressoes, expressoes),
)


@settings(max_examples=6000, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(relacoes)
def test_ida_e_volta_de_arvores_aleatorias(e: Expr) -> None:
    latex = para_latex(e)
    assert analisar(latex, TAB) == e, latex
    assert analisar(para_latex(e, "en"), TAB) == e


@settings(max_examples=500, deadline=None)
@given(relacoes)
def test_json_ida_e_volta(e: Expr) -> None:
    assert de_json(para_json(e)) == e
