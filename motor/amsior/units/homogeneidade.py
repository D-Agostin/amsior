# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Análise dimensional de uma AmsiorExpr (camada V5 da verificação)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import sympy as sp

from amsior.erros import ErroDimensional
from amsior.expr.latex import para_latex
from amsior.expr.nos import (
    Abs, Add, Cos, Deriv, Div, Eq, Exp, Expr, Func, Ge, Gt, Integral, Le, Ln, Log, Lt,
    Mul, Ne, Neg, Num, PDeriv, Pow, Root, Sin, Sqrt, Sub, Sym, Tan,
)
from amsior.expr.ponte_sympy import para_sympy
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.units.dimensao import UM, Dim
from amsior.units.glossario import Glossario

EstadoDim = Literal["aprovado", "reprovado", "indeterminado", "dispensado"]
_ADIMENSIONAIS = frozenset({"\\pi", "\\infty"})


@dataclass
class ResultadoDimensional:
    estado: EstadoDim
    dimensao: Dim | None = None
    erro: ErroDimensional | None = None
    sem_grandeza: set[str] = field(default_factory=set)


class AnalisadorDimensional:
    def __init__(self, tabela: TabelaDeSimbolos, glossario: Glossario) -> None:
        self.tabela = tabela
        self.glossario = glossario
        self.sem_grandeza: set[str] = set()

    def _txt(self, e: Expr) -> str:
        return para_latex(e)

    def dim_simbolo(self, id_: str) -> Dim | None:
        if id_ in _ADIMENSIONAIS:
            return UM
        s = self.tabela.obter(id_)
        if s is None or s.grandeza is None or s.grandeza not in self.glossario:
            self.sem_grandeza.add(id_)
            return None
        return self.glossario[s.grandeza].dimensao

    def _exigir_adimensional(self, arg: Expr, funcao: str) -> None:
        d = self.dim(arg)
        if d is not None and not d.adimensional():
            raise ErroDimensional(
                "erro.dim.argumento_nao_adimensional", funcao=funcao,
                argumento=self._txt(arg), dimensao=d.texto(),
            )

    def _iguais(self, partes: list[Expr], chave: str) -> Dim | None:
        conhecida: Dim | None = None
        ref: Expr | None = None
        for p in partes:
            d = self.dim(p)
            if d is None:
                continue
            if conhecida is None:
                conhecida, ref = d, p
            elif not conhecida.igual(d):
                assert ref is not None
                raise ErroDimensional(
                    chave, a=self._txt(ref), dim_a=conhecida.texto(),
                    b=self._txt(p), dim_b=d.texto(),
                )
        return conhecida

    def dim(self, e: Expr) -> Dim | None:  # noqa: C901 - um ramo por tipo de nó
        if isinstance(e, Num):
            # zero tem qualquer dimensão: "P V - n R T = 0" e "\int_0^T" são homogêneos
            return None if e.fracao() == 0 else UM
        if isinstance(e, Sym):
            return self.dim_simbolo(e.id)
        if isinstance(e, Add):
            return self._iguais(list(e.termos), "erro.dim.soma_inconsistente")
        if isinstance(e, Sub):
            return self._iguais([e.a, e.b], "erro.dim.soma_inconsistente")
        if isinstance(e, Neg | Abs):
            return self.dim(e.a)
        if isinstance(e, Mul):
            dims = [self.dim(f) for f in e.fatores]
            if any(d is None for d in dims):
                return None
            total = UM
            for d in dims:
                assert d is not None
                total = total * d
            return total
        if isinstance(e, Div):
            dn, dd = self.dim(e.num), self.dim(e.den)
            return None if dn is None or dd is None else dn / dd
        if isinstance(e, Pow):
            db = self.dim(e.base)
            self._exigir_adimensional(e.exp, "expoente")
            if db is None:
                return None
            if db.adimensional():
                return UM
            return db ** para_sympy(e.exp, self.tabela)
        if isinstance(e, Sqrt):
            db = self.dim(e.a)
            return None if db is None else db ** sp.Rational(1, 2)
        if isinstance(e, Root):
            db = self.dim(e.a)
            self._exigir_adimensional(e.n, "índice da raiz")
            return None if db is None else db ** (1 / para_sympy(e.n, self.tabela))
        if isinstance(e, Exp | Ln | Sin | Cos | Tan):
            nome = {Exp: "exp", Ln: "ln", Sin: "sen", Cos: "cos", Tan: "tg"}[type(e)]
            self._exigir_adimensional(e.a, nome)
            return UM
        if isinstance(e, Log):
            self._exigir_adimensional(e.a, "log")
            self._exigir_adimensional(e.base, "base do log")
            return UM
        if isinstance(e, Func):
            for a in e.args:
                self.dim(a)
            return self.dim_simbolo(e.nome)
        if isinstance(e, Deriv | PDeriv):
            df, dv = self.dim(e.f), self.dim(e.var)
            return None if df is None or dv is None else df / dv ** e.ordem
        if isinstance(e, Integral):
            df, dv = self.dim(e.f), self.dim(e.var)
            for lim in (e.inferior, e.superior):
                if lim is not None:
                    self._iguais([e.var, lim], "erro.dim.limite_inconsistente")
            return None if df is None or dv is None else df * dv
        if isinstance(e, Eq | Ne | Gt | Ge | Lt | Le):
            self._iguais([e.esq, e.dir], "erro.dim.lados_diferentes")
            return None
        raise TypeError(f"nó sem regra dimensional: {type(e).__name__}")


def verificar_homogeneidade(
    e: Expr,
    tabela: TabelaDeSimbolos,
    glossario: Glossario,
    empirica_dimensional: bool = False,
) -> ResultadoDimensional:
    """V5: homogeneidade e argumentos adimensionais.

    ``indeterminado`` quando algum símbolo não tem grandeza: a análise roda
    com o que se sabe, mas não pode aprovar. Equações empíricas dimensionais
    (Antoine) são ``dispensado``: os coeficientes valem para unidades fixas.
    """
    if empirica_dimensional:
        return ResultadoDimensional("dispensado")
    a = AnalisadorDimensional(tabela, glossario)
    try:
        d = a.dim(e)
    except ErroDimensional as erro:
        return ResultadoDimensional("reprovado", erro=erro, sem_grandeza=a.sem_grandeza)
    if a.sem_grandeza:
        return ResultadoDimensional("indeterminado", d, sem_grandeza=a.sem_grandeza)
    return ResultadoDimensional("aprovado", d)
