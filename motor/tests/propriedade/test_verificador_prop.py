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
