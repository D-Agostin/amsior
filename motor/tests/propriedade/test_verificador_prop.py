# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Propriedades do verificador com equações aleatórias de lados estritamente positivos.

* Um passo construído aplicando de fato a operação é aprovado.
* O mesmo passo com um lado adulterado é reprovado.

Os lados só usam soma, produto, divisão, potência inteira, raiz e exponencial
de símbolos positivos, para que nenhum lado seja identicamente nulo (o que
tornaria uma adulteração indistinguível).
"""

from __future__ import annotations

from typing import Any

import sympy as sp
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from amsior.expr import Eq, Num, TabelaDeSimbolos, de_sympy, para_sympy
from amsior.units import carregar_glossario
from amsior.verify import Operacao, Passo, certificar

G = carregar_glossario()
NOMES = ("u", "v", "p", "s")
TAB = TabelaDeSimbolos.de([G.simbolo(n, "numero_adimensional") for n in NOMES])
SIMB = [para_sympy(de_sympy(sp.Symbol(n)), TAB) for n in NOMES]

folhas = st.one_of(st.sampled_from(SIMB), st.integers(1, 5).map(sp.Integer))


def _compor(f: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
    return st.one_of(
        st.builds(lambda a, b: a + b, f, f), st.builds(lambda a, b: a * b, f, f),
        st.builds(lambda a, b: a / b, f, f), st.builds(lambda a: a**2, f),
        st.builds(sp.sqrt, f), st.builds(lambda a: sp.exp(a / 7), f),
    )


lados = st.recursive(folhas, _compor, max_leaves=5)
OPS = ["somar_ambos", "subtrair_ambos", "multiplicar_ambos", "dividir_ambos", "elevar_ambos",
       "ln_ambos", "exp_ambos", "reciproco_ambos", "trocar_lados", "raiz_ambos"]


def _efeito(op: str, L: Any, R: Any, a: Any) -> tuple[Any, Any, Any]:
    if op == "somar_ambos":
        return L + a, R + a, a
    if op == "subtrair_ambos":
        return L - a, R - a, a
    if op == "multiplicar_ambos":
        return L * a, R * a, a
    if op == "dividir_ambos":
        return L / a, R / a, a
    if op == "elevar_ambos":
        return L**3, R**3, sp.Integer(3)
    if op == "raiz_ambos":
        return sp.sqrt(L), sp.sqrt(R), sp.Integer(2)
    if op == "ln_ambos":
        return sp.log(L), sp.log(R), None
    if op == "exp_ambos":
        return sp.exp(L / 9), sp.exp(R / 9), None
    if op == "reciproco_ambos":
        return 1 / L, 1 / R, None
    return R, L, None


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(lados, lados, st.sampled_from(OPS), lados, st.integers(0, 2))
def test_passo_verdadeiro_aprova_e_adulterado_reprova(
        L: Any, R: Any, op: str, a: Any, adulteracao: int) -> None:
    if op == "exp_ambos":
        L, R = L / 9, R / 9  # mantém os números pequenos
        novo_l, novo_r = sp.exp(L), sp.exp(R)
        arg = None
    else:
        novo_l, novo_r, arg = _efeito(op, L, R, a)
    antes = Eq(de_sympy(L), de_sympy(R))
    depois = Eq(de_sympy(novo_l), de_sympy(novo_r))
    operacao = Operacao(op, None if arg is None else de_sympy(arg))
    cert = certificar(Passo(antes, depois, operacao), TAB, G)
    assert cert.estado == "aprovado", [m.texto() for m in cert.motivos]

    if adulteracao == 0 and sp.simplify(novo_l) != 0:
        ruim = Eq(de_sympy(novo_l * 2), depois.dir)
    elif adulteracao == 0:  # lado identicamente nulo: o dobro seria igual
        ruim = Eq(de_sympy(novo_l + 1), depois.dir)
    elif adulteracao == 1:
        ruim = Eq(depois.esq, de_sympy(novo_r + 1))
    elif sp.simplify(novo_r) != 0:
        ruim = Eq(depois.esq, de_sympy(-novo_r))
    else:
        ruim = Eq(depois.esq, de_sympy(novo_r + 1))
    cert_ruim = certificar(Passo(antes, ruim, operacao), TAB, G)
    assert cert_ruim.estado == "reprovado"


def test_numero_um_nao_quebra_a_estrategia() -> None:
    assert de_sympy(sp.Integer(1)) == Num("1")


# ---------------------------------------------------------------- revisão 0001
# Geradores das classes de erro que a suíte original não cobria: ramos longe
# da origem, polos cancelados e escalas extremas.

TAB_REV = TabelaDeSimbolos.de([G.simbolo("u", "numero_adimensional"),
                               G.simbolo("x", "adimensional"),
                               G.simbolo("z", "adimensional")])
constantes = st.builds(lambda m, e: f"{m}" + "0" * e, st.integers(11, 99), st.integers(0, 7))


def _passo(antes: str, depois: str, op: str = "reescrever", relacao: str = "equivalente",
           condicoes: tuple[str, ...] = ()) -> Passo:
    from amsior.expr import analisar
    from amsior.verify import Condicao
    A = lambda s: analisar(s, TAB_REV)  # noqa: E731
    return Passo(A(antes), A(depois), Operacao(op), relacao,  # type: ignore[arg-type]
                 condicoes=tuple(Condicao(A(c)) for c in condicoes))


@settings(max_examples=25, deadline=None)
@given(constantes, st.sampled_from(["u", "x"]))
def test_ramo_de_modulo_longe_da_origem(c: str, v: str) -> None:
    errado = certificar(_passo(rf"|{v} - {c}| = z", rf"{c} - {v} = z"), TAB_REV, G)
    assert errado.estado == "reprovado"
    certo = certificar(_passo(rf"|{v} - {c}| = z", rf"{c} - {v} = z",
                              condicoes=(rf"{v} \leq {c}",)), TAB_REV, G)
    assert certo.estado == "aprovado" and certo.sob_hipotese


@settings(max_examples=25, deadline=None)
@given(constantes)
def test_polo_cancelado_so_implica(c: str) -> None:
    antes, depois = rf"\frac{{(x - {c}) z}}{{x - {c}}} = u", "z = u"
    assert certificar(_passo(antes, depois), TAB_REV, G).estado == "reprovado"
    assert certificar(_passo(antes, depois, relacao="implica"), TAB_REV, G).estado == "aprovado"
    assert certificar(_passo(depois, antes, relacao="implica"), TAB_REV, G).estado == "reprovado"


@settings(max_examples=25, deadline=None)
@given(st.integers(2, 9), st.integers(20, 80))
def test_escalas_extremas(m: int, e: int) -> None:
    antes = rf"{m} \cdot 10^{{-{e}}} u = z"
    certo = certificar(_passo(antes, rf"u \cdot {m} \cdot 10^{{-{e}}} = z"), TAB_REV, G)
    assert certo.estado == "aprovado"
    errado = certificar(_passo(antes, rf"{m + 1} \cdot 10^{{-{e}}} u = z"), TAB_REV, G)
    assert errado.estado == "reprovado"
