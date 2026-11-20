# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Conversões entre AmsiorExpr e SymPy.

AmsiorExpr → SymPy alimenta o oráculo e o verificador. SymPy → AmsiorExpr só
existe para resultados do oráculo: nunca se converte texto em SymPy (T-05).
"""

from __future__ import annotations

from typing import Any

import sympy as sp
from sympy.core.function import AppliedUndef

from amsior.expr.nos import (
    Abs, Add, Cos, Deriv, Div, Eq, Exp, Expr, Func, Ge, Gt, Integral, Le, Ln, Log, Lt,
    Mul, Ne, Neg, Num, PDeriv, Pow, Root, Sin, Sqrt, Sub, Sym, Tan,
)
from amsior.expr.simbolos import TabelaDeSimbolos

_MAPA_SUPOSICOES = {
    "real": "real", "positivo": "positive", "nao_negativo": "nonnegative",
    "nao_nulo": "nonzero", "inteiro": "integer",
}
_ESPECIAIS: dict[str, Any] = {"\\pi": sp.pi, "\\infty": sp.oo}


def suposicoes_sympy(sup: frozenset[str]) -> dict[str, bool]:
    return {_MAPA_SUPOSICOES[s]: True for s in sup if s in _MAPA_SUPOSICOES}


class ParaSympy:
    def __init__(self, tabela: TabelaDeSimbolos | None = None) -> None:
        self.tabela = tabela if tabela is not None else TabelaDeSimbolos()
        self._cache: dict[str, Any] = {}

    def simbolo(self, id_: str) -> Any:
        if id_ in _ESPECIAIS:
            return _ESPECIAIS[id_]
        if id_ not in self._cache:
            self._cache[id_] = sp.Symbol(id_, **suposicoes_sympy(self.tabela.suposicoes(id_)))
        return self._cache[id_]

    def valor_simbolo(self, id_: str) -> Any:
        """Símbolo, ou função aplicada se o símbolo declara dependências (``P`` vira ``P(T)``;
        com papel de função, ``P(T_2)`` vira ``Func`` e as duas formas usam o mesmo nome)."""
        s = self.tabela.obter(id_)
        if s is not None and s.depende_de:
            f = sp.Function(id_, **suposicoes_sympy(s.suposicoes))
            return f(*[self.simbolo(d) for d in s.depende_de])
        return self.simbolo(id_)

    def __call__(self, e: Expr) -> Any:  # noqa: C901 - um ramo por tipo de nó
        c = self
        if isinstance(e, Num):
            return sp.Rational(e.valor)
        if isinstance(e, Sym):
            return c.valor_simbolo(e.id)
        if isinstance(e, Add):
            return sp.Add(*[c(t) for t in e.termos])
        if isinstance(e, Sub):
            return c(e.a) - c(e.b)
        if isinstance(e, Neg):
            return -c(e.a)
        if isinstance(e, Mul):
            return sp.Mul(*[c(f) for f in e.fatores])
        if isinstance(e, Div):
            return c(e.num) / c(e.den)
        if isinstance(e, Pow):
            return sp.Pow(c(e.base), c(e.exp))
        if isinstance(e, Sqrt):
            return sp.sqrt(c(e.a))
        if isinstance(e, Root):
            n = c(e.n)
            if n.is_integer and n.is_odd:  # raiz de índice ímpar é a real: ∛(−8) = −2
                return sp.real_root(c(e.a), n)
            return sp.Pow(c(e.a), 1 / n)
        if isinstance(e, Exp):
            return sp.exp(c(e.a))
        if isinstance(e, Ln):
            return sp.log(c(e.a))
        if isinstance(e, Log):
            return sp.log(c(e.a), c(e.base))
        if isinstance(e, Sin):
            return sp.sin(c(e.a))
        if isinstance(e, Cos):
            return sp.cos(c(e.a))
        if isinstance(e, Tan):
            return sp.tan(c(e.a))
        if isinstance(e, Abs):
            return sp.Abs(c(e.a))
        if isinstance(e, Func):
            s = self.tabela.obter(e.nome)
            sup = suposicoes_sympy(s.suposicoes) if s else {"real": True}
            return sp.Function(e.nome, **sup)(*[c(a) for a in e.args])
        if isinstance(e, PDeriv) and e.mantidas:
            # (∂H/∂T)_P não é Derivative(H, T): sem modelo da função de estado,
            # vira um objeto opaco identificado pela própria notação
            from amsior.expr.latex import para_latex
            return sp.Symbol(para_latex(e), real=True)
        if isinstance(e, Deriv | PDeriv):
            return sp.Derivative(c(e.f), (self.simbolo(e.var.id), e.ordem))
        if isinstance(e, Integral):
            v = self.simbolo(e.var.id)
            if e.inferior is None and e.superior is None:
                return sp.Integral(c(e.f), v)
            if e.inferior is None or e.superior is None:
                raise ValueError("integral com só um limite")
            return sp.Integral(c(e.f), (v, c(e.inferior), c(e.superior)))
        rel = {Eq: sp.Eq, Ne: sp.Ne, Gt: sp.Gt, Ge: sp.Ge, Lt: sp.Lt, Le: sp.Le}
        for cls, f in rel.items():
            if isinstance(e, cls):
                return f(c(e.esq), c(e.dir), evaluate=False)  # type: ignore[attr-defined]
        raise TypeError(f"nó sem conversão para SymPy: {type(e).__name__}")


def para_sympy(e: Expr, tabela: TabelaDeSimbolos | None = None) -> Any:
    return ParaSympy(tabela)(e)


# ---------------------------------------------------------------- SymPy → AmsiorExpr


def _numero(x: Any) -> Expr:
    if x.is_Integer:
        n = int(x)
        return Num(str(n)) if n >= 0 else Neg(Num(str(-n)))
    if x.is_Rational:
        p, q = int(x.p), int(x.q)
        frac: Expr = Div(Num(str(abs(p))), Num(str(q)))
        return frac if p >= 0 else Neg(frac)
    if x.is_Float:
        txt = format(float(abs(x)), ".15g")
        if "e" in txt or "E" in txt:
            txt = format(float(abs(x)), "f").rstrip("0").rstrip(".") or "0"
        return Num(txt) if x >= 0 else Neg(Num(txt))
    raise TypeError(f"número não suportado: {x!r}")


def de_sympy(x: Any, tabela: TabelaDeSimbolos | None = None) -> Expr:  # noqa: C901
    """Converte um resultado do oráculo em AmsiorExpr, em forma de apresentação."""
    tab = tabela if tabela is not None else TabelaDeSimbolos()

    def d(y: Any) -> Expr:
        return de_sympy(y, tab)

    if isinstance(x, sp.Equality):
        return Eq(d(x.lhs), d(x.rhs))
    for cls_sp, cls in ((sp.Unequality, Ne), (sp.StrictGreaterThan, Gt),
                        (sp.GreaterThan, Ge), (sp.StrictLessThan, Lt), (sp.LessThan, Le)):
        if isinstance(x, cls_sp):
            return cls(d(x.lhs), d(x.rhs))
    if x is sp.pi:
        return Sym("\\pi")
    if x is sp.oo:
        return Sym("\\infty")
    if x is sp.E:
        return Exp(Num("1"))
    if x.is_Number:
        return _numero(x)
    if x.is_Symbol:
        return Sym(x.name)
    if isinstance(x, AppliedUndef):
        nome = type(x).__name__
        s = tab.obter(nome)
        if s is not None and s.depende_de:
            return Sym(nome)
        return Func(nome, tuple(d(a) for a in x.args))
    if x.is_Add:
        termos = x.as_ordered_terms()
        primeiro = termos[0]
        pendente: list[Expr] = [
            Neg(d(-primeiro)) if primeiro.could_extract_minus_sign() else d(primeiro)
        ]
        for termo in termos[1:]:
            if termo.could_extract_minus_sign():
                acc = pendente[0] if len(pendente) == 1 else Add(tuple(pendente))
                pendente = [Sub(acc, d(-termo))]
            else:
                pendente.append(d(termo))
        return pendente[0] if len(pendente) == 1 else Add(tuple(pendente))
    if x.is_Mul:
        if x.could_extract_minus_sign():
            return Neg(d(-x))
        num, den = sp.fraction(x)
        if den != 1:
            return Div(d(num), d(den))
        fatores = [d(f) for f in x.as_ordered_factors()]
        return fatores[0] if len(fatores) == 1 else Mul(tuple(fatores))
    if x.is_Pow:
        b, e = x.as_base_exp()
        if b is sp.E:
            return Exp(d(e))
        if e == sp.Rational(1, 2):
            return Sqrt(d(b))
        if e.is_Rational and e.p == 1 and e.q > 1:
            return Root(d(b), Num(str(e.q)))
        if e.is_number and e.is_negative:
            return Div(Num("1"), d(sp.Pow(b, -e)))
        return Pow(d(b), d(e))
    if isinstance(x, sp.exp):
        return Exp(d(x.args[0]))
    if isinstance(x, sp.log):
        return Ln(d(x.args[0]))
    for cls_sp, cls1 in ((sp.sin, Sin), (sp.cos, Cos), (sp.tan, Tan), (sp.Abs, Abs)):
        if isinstance(x, cls_sp):
            return cls1(d(x.args[0]))
    if isinstance(x, sp.Derivative):
        (var, ordem), = x.variable_count
        return Deriv(d(x.expr), Sym(var.name), int(ordem))
    if isinstance(x, sp.Integral):
        (lim,) = x.limits
        var = Sym(lim[0].name)
        if len(lim) == 3:
            return Integral(d(x.function), var, d(lim[1]), d(lim[2]))
        return Integral(d(x.function), var)
    raise TypeError(f"expressão SymPy sem conversão: {type(x).__name__}")
