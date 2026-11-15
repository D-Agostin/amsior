# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Leituras do analisador: cada regra da gramática com a árvore esperada."""

from __future__ import annotations

import pytest

from amsior.erros import AmbiguidadeDeSimbolo, ErroDeAnalise
from amsior.expr import (
    Abs, Add, Deriv, Div, Eq, Exp, Func, Ge, Integral, Ln, Log, Mul, Ne, Neg, Num, PDeriv,
    Pow, Root, Simbolo, Sin, Sqrt, Sub, Sym, TabelaDeSimbolos, analisar,
)
from tests.conftest import tabela_corpus

x, y, a, b, c, d, t, T, P, V, n, R = (Sym(s) for s in "xyabcdtTPVnR")
TAB = tabela_corpus()


def A(s: str, tab: TabelaDeSimbolos | None = TAB) -> object:
    return analisar(s, tab)


# ------------------------------------------------------------ aritmética e forma


def test_cadeia_de_soma_e_subtracao_associa_a_esquerda() -> None:
    assert A("a - b + c") == Add((Sub(a, b), c))
    assert A("a + b - c") == Sub(Add((a, b)), c)
    assert A("a - b - c") == Sub(Sub(a, b), c)


def test_parenteses_explicitos_geram_no_aninhado() -> None:
    assert A("a + (b + c)") == Add((a, Add((b, c))))
    assert A("(ab)c") == Mul((Mul((a, b)), c))


def test_menos_unario_engloba_o_produto() -> None:
    assert A("-ab") == Neg(Mul((a, b)))
    assert A("-x^2") == Neg(Pow(x, Num("2")))


def test_divisao_com_barra_associa_a_esquerda() -> None:
    assert A("a/b/c") == Div(Div(a, b), c)
    assert A("a/bc") == Div(a, Mul((b, c)))


def test_numeros_com_virgula_ponto_e_chave() -> None:
    assert A("2,5") == A("2.5") == A("2{,}5") == Num("2.5")


def test_expoente_sem_chaves_pega_um_caractere() -> None:
    assert A("x^23") == Mul((Pow(x, Num("2")), Num("3")))


# ------------------------------------------------------------ símbolos e palavras


def test_palavra_resolvida_pela_tabela() -> None:
    assert A("PV") == Mul((P, V))
    assert A("nRT^2") == Mul((n, R, Pow(T, Num("2"))))


def test_palavra_conhecida_vira_simbolo_de_varias_letras() -> None:
    assert A("Re") == Sym("\\mathrm{Re}")


def test_palavra_desconhecida_nao_e_adivinhada() -> None:
    with pytest.raises(AmbiguidadeDeSimbolo) as info:
        analisar("PV", TabelaDeSimbolos())
    assert info.value.palavra == "PV"
    assert "P V" in info.value.opcoes


def test_modo_produto_aceita_letras_soltas() -> None:
    assert analisar("PV", TabelaDeSimbolos(), "produto") == Mul((P, V))


def test_indices_canonicos() -> None:
    assert A("T_1") == A("T_{1}") == Sym("T_{1}")
    assert A("\\Delta H_{vap}") == A("\\Delta H_{\\mathrm{vap}}") == A(
        "\\Delta H_{\\text{vap}}") == Sym("\\Delta H_{\\mathrm{vap}}")
    assert A("x_{\\mathrm{A}}") == Sym("x_{A}")


def test_rotulos_sobrescritos_versus_potencia() -> None:
    assert A("P^{\\mathrm{sat}}") == A("P^{sat}") == Sym("P^{\\mathrm{sat}}")
    assert A("H^{\\circ}") == Sym("H^{\\circ}")
    assert A("y^{*}") == Sym("y^{*}")
    assert A("B^{(0)}") == Sym("B^{(0)}")
    assert A("x^{n}") == Pow(x, Sym("n"))


def test_decoracoes_e_gregas() -> None:
    assert A("\\dot{m}") == A("\\dot m") == Sym("\\dot{m}")
    assert A("\\overline{V}") == Sym("\\bar{V}")
    assert A("\\rho v") == Mul((Sym("\\rho"), Sym("v")))
    assert A("ρ") == Sym("\\rho")


def test_delta_precisa_de_simbolo() -> None:
    with pytest.raises(ErroDeAnalise):
        A("\\Delta(PV)")


def test_funcao_incognita_so_com_papel_funcao() -> None:
    tab = tabela_corpus(("y",))
    assert analisar("y(t)", tab) == Func("y", (t,))
    assert analisar("y (t)", tab) == Mul((y, t))
    assert A("y(t)") == Mul((y, t))


# ------------------------------------------------------------ funções


def test_argumento_de_funcao_sem_parenteses() -> None:
    assert A("\\ln x y") == Mul((Ln(x), y))
    assert A("\\ln xy") == Ln(Mul((x, y)))
    assert A("\\ln\\frac{a}{b}") == Ln(Div(a, b))
    assert A("\\sin^2 x") == Pow(Sin(x), Num("2"))


def test_log_sem_base_e_base_10() -> None:
    assert A("\\log x") == A("\\log_{10} x") == Log(x, Num("10"))


def test_exponencial() -> None:
    assert A("e^{x}") == A("\\exp(x)") == A("\\mathrm{e}^{x}") == Exp(x)


def test_exponencial_colada_numa_palavra() -> None:
    # "Ae^{x}" é A·exp(x) (Arrhenius): o e colado antes de ^ não vira símbolo.
    assert A("ae^{x}", None) == Mul((a, Exp(x)))
    assert analisar("ae^{x}", None, modo_palavras="produto") == Mul((a, Exp(x)))
    assert A("b e^{x}") == Mul((b, Exp(x)))


def test_raizes_e_modulo() -> None:
    assert A("\\sqrt{x}") == Sqrt(x)
    assert A("\\sqrt[3]{x}") == Root(x, Num("3"))
    assert A("|x|") == A("\\left|x\\right|") == Abs(x)


# ------------------------------------------------------------ cálculo


def test_derivadas() -> None:
    assert A("\\frac{dy}{dt}") == A("\\frac{\\mathrm{d}y}{\\mathrm{d}t}") == Deriv(y, t)
    assert A("\\frac{d^2y}{dt^2}") == Deriv(y, t, 2)
    assert A("\\frac{d}{dt}(xy)") == Deriv(Mul((x, y)), t)
    assert A("\\frac{d\\ln x}{dt}") == Deriv(Ln(x), t)


def test_fracao_com_d_que_nao_e_derivada() -> None:
    assert A("\\frac{d}{t}") == Div(d, t)
    assert A("\\frac{d y}{d t}") == Div(Mul((d, y)), Mul((d, t)))


def test_derivada_parcial_com_variaveis_mantidas() -> None:
    assert A("\\left(\\frac{\\partial H}{\\partial T}\\right)_P") == PDeriv(
        Sym("H"), T, (P,))


def test_integrais() -> None:
    assert A("\\int x\\,dx") == Integral(x, x)
    assert A("\\int_0^1 x\\,dx") == Integral(x, x, Num("0"), Num("1"))
    assert A("\\int a + b T\\,dT") == Integral(Add((a, Mul((b, T)))), T)
    assert A("\\int \\frac{dP}{P}") == Integral(Div(Num("1"), P), P)
    assert A("\\int dT") == Integral(Num("1"), T)
    assert A("2\\int_0^1 x\\,dx + 1") == Add(
        (Mul((Num("2"), Integral(x, x, Num("0"), Num("1")))), Num("1")))


def test_d_dentro_de_parenteses_na_integral_nao_e_diferencial() -> None:
    assert A("\\int (a + dT^2)\\,dT") == Integral(
        Add((a, Mul((d, Pow(T, Num("2")))))), T)


def test_integral_sem_diferencial() -> None:
    with pytest.raises(ErroDeAnalise):
        A("\\int x^2")


# ------------------------------------------------------------ relações e erros


def test_relacoes() -> None:
    assert A("x = y") == Eq(x, y)
    assert A("x \\neq 0") == A("x ≠ 0") == Ne(x, Num("0"))
    assert A("x \\geq 0") == Ge(x, Num("0"))


@pytest.mark.parametrize("latex", [
    "x +", "\\frac{a}", "(a + b", "\\sum x", "x \\\\ y", "a & b", "\\int x\\,dx\\,dy = ",
    "x = = y", "\\sqrt", "#",
])
def test_erros_tem_mensagem_e_posicao(latex: str) -> None:
    with pytest.raises(ErroDeAnalise) as info:
        A(latex)
    assert info.value.mensagem()
    assert info.value.posicao >= 0


def test_simbolo_com_suposicao_nao_altera_leitura() -> None:
    tab = TabelaDeSimbolos.de([Simbolo("T", suposicoes=frozenset({"positivo"}))])
    assert analisar("T", tab) == T
