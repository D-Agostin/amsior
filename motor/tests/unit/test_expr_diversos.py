# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Léxico, impressão, JSON e ponte com SymPy."""

from __future__ import annotations

import pytest
import sympy as sp

from amsior.expr import (
    Add, Div, Eq, Func, Integral, Mul, Neg, Num, Pow, Simbolo, Sqrt, Sub, Sym,
    TabelaDeSimbolos, analisar, de_json, de_sympy, para_json, para_latex, para_sympy,
)
from amsior.expr.lexico import tokenizar
from tests.conftest import tabela_corpus

x, y, t = Sym("x"), Sym("y"), Sym("t")


def test_lexico_registra_espacos_e_decimais() -> None:
    toks = tokenizar(r"P V = 2{,}5\,x")
    assert [(k.tipo, k.texto, k.espaco_antes) for k in toks[:-1]] == [
        ("LETRA", "P", False), ("LETRA", "V", True), ("OP", "=", True),
        ("NUM", "2.5", True), ("LETRA", "x", True),
    ]


def test_lexico_normaliza_unicode_e_delimitadores() -> None:
    tipos = [(k.tipo, k.texto) for k in tokenizar(r"\left| x − 1 \right|")[:-1]]
    assert tipos == [("ABRE", "|"), ("LETRA", "x"), ("OP", "-"), ("NUM", "1"), ("FECHA", "|")]


@pytest.mark.parametrize(("arvore", "esperado"), [
    (Mul((Num("2"), x)), "2 x"),
    (Mul((x, Num("2"))), "x \\cdot 2"),
    (Mul((Num("2"), Pow(Num("10"), Num("3")))), "2 \\cdot 10^{3}"),
    (Sub(x, Add((y, t))), "x - \\left(y + t\\right)"),
    (Mul((Neg(x), y)), "\\left(-x\\right) y"),
    (Pow(Sym("e"), Num("2")), "\\left(e\\right)^{2}"),
    (Num("0.5"), "0{,}5"),
    (Div(x, y), "\\frac{x}{y}"),
    (Sqrt(x), "\\sqrt{x}"),
    (Integral(Num("1"), x), "\\int \\mathrm{d}x"),
    (Eq(Func("y", (t,)), x), "y\\left(t\\right) = x"),
])
def test_impressao_canonica(arvore: object, esperado: str) -> None:
    assert para_latex(arvore) == esperado  # type: ignore[arg-type]


def test_impressao_em_ingles_usa_ponto() -> None:
    assert para_latex(Num("0.5"), "en") == "0.5"


def test_num_rejeita_formato_invalido() -> None:
    with pytest.raises(ValueError):
        Num("-1")
    with pytest.raises(ValueError):
        Num("1,5")


def test_json_formato_documentado() -> None:
    e = analisar("PV = nRT", tabela_corpus())
    assert para_json(e) == {"Eq": [
        {"Mul": [{"Sym": "P"}, {"Sym": "V"}]},
        {"Mul": [{"Sym": "n"}, {"Sym": "R"}, {"Sym": "T"}]},
    ]}
    assert de_json(para_json(e)) == e
    with pytest.raises(ValueError):
        de_json({"Xyz": []})


def test_para_sympy_usa_suposicoes_e_dependencias() -> None:
    tab = TabelaDeSimbolos.de([
        Simbolo("T", suposicoes=frozenset({"positivo"})),
        Simbolo("C_{A}", depende_de=("t",)),
    ])
    T = para_sympy(Sym("T"), tab)
    assert T.is_positive
    ca = para_sympy(Sym("C_{A}"), tab)
    assert isinstance(ca, sp.core.function.AppliedUndef)
    assert para_sympy(Num("0.1"), tab) == sp.Rational(1, 10)
    assert para_sympy(Sym("\\pi"), tab) is sp.pi


def test_de_sympy_forma_de_apresentacao() -> None:
    a, b = sp.symbols("a b", positive=True)
    assert de_sympy(a - b) == Sub(Sym("a"), Sym("b")) or de_sympy(a - b) == Add(
        (Neg(Sym("b")), Sym("a")))
    assert de_sympy(a / b) == Div(Sym("a"), Sym("b"))
    assert de_sympy(sp.sqrt(a)) == Sqrt(Sym("a"))
    assert de_sympy(sp.Rational(-3, 4)) == Neg(Div(Num("3"), Num("4")))
    assert de_sympy(sp.Float("0.25")) == Num("0.25")


@pytest.mark.parametrize("latex", [
    r"\frac{a + b}{c} - \sqrt{x} e^{-t}", r"\ln\frac{P_2}{P_1}", r"x^{3} - 2x + 1",
    r"\frac{1}{1 + e^{-x}}", r"a \sin x + b\cos x",
])
def test_de_sympy_preserva_o_valor(latex: str) -> None:
    tab = tabela_corpus()
    e = para_sympy(analisar(latex, tab), tab)
    assert sp.simplify(para_sympy(de_sympy(e), tab) - e) == 0
