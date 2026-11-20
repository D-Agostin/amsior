# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Utilitários do verificador sobre a árvore AmsiorExpr.

O verificador trabalha na árvore do Amsior, e não no SymPy: o domínio de
definição, as derivadas que não podem ser calculadas e a avaliação numérica
própria dependem da forma escrita, que o SymPy altera ao construir (``x/x``
vira 1, ``exp(ln x)`` vira ``x``).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import fields
from fractions import Fraction

from amsior.expr.latex import para_latex
from amsior.expr.nos import (
    Add, Deriv, Div, Expr, Func, Integral, Mul, Neg, Num, PDeriv, Pow, Sub, Sym,
)
from amsior.expr.simbolos import TabelaDeSimbolos

ESPECIAIS = frozenset({"\\pi", "\\infty"})


def mapear(e: Expr, f: Callable[[Expr], Expr]) -> Expr:
    """Reconstrói ``e`` aplicando ``f`` a cada filho direto."""
    if isinstance(e, Num | Sym):
        return e
    args = {}
    for campo in fields(e):  # type: ignore[arg-type]
        v = getattr(e, campo.name)
        if isinstance(v, Expr):
            v = f(v)
        elif isinstance(v, tuple):
            v = tuple(f(x) if isinstance(x, Expr) else x for x in v)
        args[campo.name] = v
    return type(e)(**args)


def percorrer(e: Expr) -> Iterator[Expr]:
    yield e
    for c in e.filhos():
        yield from percorrer(c)


def substituir(e: Expr, id_: str, novo: Expr) -> Expr:
    if isinstance(e, Sym):
        return novo if e.id == id_ else e
    return mapear(e, lambda c: substituir(c, id_, novo))


def trocar_subarvore(e: Expr, velha: Expr, nova: Expr) -> Expr:
    """Troca cada ocorrência estrutural de ``velha`` por ``nova``."""
    if e == velha:
        return nova
    return mapear(e, lambda c: trocar_subarvore(c, velha, nova))


def chave(e: Expr) -> str:
    """Identificador estável de uma subárvore (sua forma LaTeX canônica)."""
    return para_latex(e)


def livres(e: Expr) -> set[str]:
    """Símbolos livres: a variável de uma integral definida é ligada."""
    if isinstance(e, Sym):
        return set() if e.id in ESPECIAIS else {e.id}
    if isinstance(e, Num):
        return set()
    if isinstance(e, Integral) and e.inferior is not None and e.superior is not None:
        return (livres(e.f) - {e.var.id}) | livres(e.inferior) | livres(e.superior)
    if isinstance(e, PDeriv):
        return livres(e.f) | {e.var.id} | {m.id for m in e.mantidas}
    if isinstance(e, Deriv | Integral):
        return livres(e.f) | {e.var.id}
    out: set[str] = set()
    for c in e.filhos():
        out |= livres(c)
    return out


def variaveis_de_amostragem(exprs: list[Expr], tabela: TabelaDeSimbolos) -> list[str]:
    """Símbolos que recebem valor no sorteio.

    Um símbolo que declara dependências é uma função: não é sorteado, mas as
    variáveis de que ele depende são.
    """
    nomes: set[str] = set()
    for e in exprs:
        nomes |= livres(e)
    fila = list(nomes)
    out: set[str] = set()
    while fila:
        n = fila.pop()
        s = tabela.obter(n)
        if s is not None and s.depende_de:
            for d in s.depende_de:
                if d not in out and d not in fila:
                    fila.append(d)
            continue
        out.add(n)
    return sorted(out)


def numeros(e: Expr) -> list[Fraction]:
    return [n.fracao() for n in percorrer(e) if isinstance(n, Num)]


def fracao_exata(e: Expr) -> Fraction | None:
    """Valor exato de uma subárvore sem símbolos, ou None."""
    if isinstance(e, Num):
        return e.fracao()
    if isinstance(e, Neg):
        v = fracao_exata(e.a)
        return None if v is None else -v
    if isinstance(e, Add):
        soma = Fraction(0)
        for t in e.termos:
            v = fracao_exata(t)
            if v is None:
                return None
            soma += v
        return soma
    if isinstance(e, Sub):
        a, b = fracao_exata(e.a), fracao_exata(e.b)
        return None if a is None or b is None else a - b
    if isinstance(e, Mul):
        total = Fraction(1)
        for f in e.fatores:
            v = fracao_exata(f)
            if v is None:
                return None
            total *= v
        return total
    if isinstance(e, Div):
        a, b = fracao_exata(e.num), fracao_exata(e.den)
        return None if a is None or b is None or b == 0 else a / b
    if isinstance(e, Pow):
        b, k = fracao_exata(e.base), fracao_exata(e.exp)
        if b is None or k is None or k.denominator != 1 or abs(k) > 64:
            return None
        if b == 0 and k <= 0:
            return None
        return b ** int(k)
    return None


def depende(s_id: str, var: str, tabela: TabelaDeSimbolos) -> bool:
    """O símbolo ``s_id`` pode variar com ``var``?"""
    if s_id == var:
        return True
    s = tabela.obter(s_id)
    if s is None:
        return False
    return var in s.depende_de


def eh_variavel(s_id: str, tabela: TabelaDeSimbolos) -> bool:
    """Símbolos sem papel declarado contam como variáveis (lado seguro)."""
    s = tabela.obter(s_id)
    return s is None or s.papel == "variavel"


def sem_dependencia(f: Expr, var: str, tabela: TabelaDeSimbolos) -> list[str]:
    """Variáveis de ``f`` que não declaram depender de ``var``."""
    return sorted(s for s in livres(f) if s != var and eh_variavel(s, tabela)
                  and not depende(s, var, tabela))


def tem_funcao_de(e: Expr, var: str, tabela: TabelaDeSimbolos) -> bool:
    """A expressão contém uma função de ``var`` (símbolo que depende dela ou f(var))?"""
    for n in percorrer(e):
        if isinstance(n, Sym) and n.id != var and depende(n.id, var, tabela):
            return True
        if isinstance(n, Func) and any(var in livres(a) for a in n.args):
            return True
    return False


def variaveis_ligadas(e: Expr) -> set[str]:
    """Variáveis de derivação, de integração e mantidas constantes."""
    out: set[str] = set()
    for n in percorrer(e):
        if isinstance(n, Deriv | Integral):
            out.add(n.var.id)
        if isinstance(n, PDeriv):
            out.add(n.var.id)
            out |= {m.id for m in n.mantidas}
    return out
