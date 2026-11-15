# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Árvore de expressões do Amsior (AmsiorExpr).

A árvore preserva a forma escrita pelo autor: ``a - b`` é ``Sub(a, b)``, e não
``Add(a, Neg(b))``; a ordem dos termos e dos fatores é a digitada. Os nós são
imutáveis e comparáveis por valor, o que permite usá-los como chaves e testar
ida e volta (LaTeX → árvore → LaTeX) por igualdade estrutural.

Convenções de estrutura (as mesmas que o analisador produz):

* Cadeias de ``+`` e ``-`` são associativas à esquerda: ``a - b + c`` é
  ``Add(Sub(a, b), c)`` e ``a + b - c`` é ``Sub(Add(a, b), c)``.
* ``Add`` e ``Mul`` são n-ários e só agrupam operandos da mesma cadeia;
  parênteses explícitos geram um nó aninhado.
* Números são sempre não negativos; o sinal é um ``Neg``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, fields
from fractions import Fraction
from typing import TypeAlias

_NUM_RE = re.compile(r"^\d+(\.\d+)?$")


class Expr:
    """Base de todos os nós."""

    __slots__ = ()

    def filhos(self) -> tuple[Expr, ...]:
        resultado: list[Expr] = []
        for campo in fields(self):  # type: ignore[arg-type]
            valor = getattr(self, campo.name)
            if isinstance(valor, Expr):
                resultado.append(valor)
            elif isinstance(valor, tuple):
                resultado.extend(v for v in valor if isinstance(v, Expr))
        return tuple(resultado)


# ---------------------------------------------------------------- folhas


@dataclass(frozen=True, slots=True)
class Num(Expr):
    """Número não negativo, guardado como texto decimal exato com ponto."""

    valor: str

    def __post_init__(self) -> None:
        if not _NUM_RE.match(self.valor):
            raise ValueError(f"Num inválido: {self.valor!r}")

    def fracao(self) -> Fraction:
        return Fraction(self.valor)


@dataclass(frozen=True, slots=True)
class Sym(Expr):
    """Símbolo. O ``id`` é a forma LaTeX canônica (ex.: ``T_{1}``, ``\\Delta H``)."""

    id: str


# ---------------------------------------------------------------- aritmética


@dataclass(frozen=True, slots=True)
class Add(Expr):
    termos: tuple[Expr, ...]

    def __post_init__(self) -> None:
        if len(self.termos) < 2:
            raise ValueError("Add precisa de ao menos dois termos")


@dataclass(frozen=True, slots=True)
class Sub(Expr):
    a: Expr
    b: Expr


@dataclass(frozen=True, slots=True)
class Neg(Expr):
    a: Expr


@dataclass(frozen=True, slots=True)
class Mul(Expr):
    fatores: tuple[Expr, ...]

    def __post_init__(self) -> None:
        if len(self.fatores) < 2:
            raise ValueError("Mul precisa de ao menos dois fatores")


@dataclass(frozen=True, slots=True)
class Div(Expr):
    num: Expr
    den: Expr


@dataclass(frozen=True, slots=True)
class Pow(Expr):
    base: Expr
    exp: Expr


@dataclass(frozen=True, slots=True)
class Sqrt(Expr):
    a: Expr


@dataclass(frozen=True, slots=True)
class Root(Expr):
    a: Expr
    n: Expr


# ---------------------------------------------------------------- funções


@dataclass(frozen=True, slots=True)
class Exp(Expr):
    a: Expr


@dataclass(frozen=True, slots=True)
class Ln(Expr):
    a: Expr


@dataclass(frozen=True, slots=True)
class Log(Expr):
    """Logaritmo com base explícita; ``\\log x`` sem base é base 10."""

    a: Expr
    base: Expr


@dataclass(frozen=True, slots=True)
class Sin(Expr):
    a: Expr


@dataclass(frozen=True, slots=True)
class Cos(Expr):
    a: Expr


@dataclass(frozen=True, slots=True)
class Tan(Expr):
    a: Expr


@dataclass(frozen=True, slots=True)
class Abs(Expr):
    a: Expr


@dataclass(frozen=True, slots=True)
class Func(Expr):
    """Função incógnita aplicada, como ``y(t)``."""

    nome: str
    args: tuple[Expr, ...]


# ---------------------------------------------------------------- cálculo


@dataclass(frozen=True, slots=True)
class Deriv(Expr):
    f: Expr
    var: Sym
    ordem: int = 1


@dataclass(frozen=True, slots=True)
class PDeriv(Expr):
    f: Expr
    var: Sym
    mantidas: tuple[Sym, ...] = ()
    ordem: int = 1


@dataclass(frozen=True, slots=True)
class Integral(Expr):
    f: Expr
    var: Sym
    inferior: Expr | None = None
    superior: Expr | None = None


# ---------------------------------------------------------------- relações


@dataclass(frozen=True, slots=True)
class Eq(Expr):
    esq: Expr
    dir: Expr


@dataclass(frozen=True, slots=True)
class Ne(Expr):
    esq: Expr
    dir: Expr


@dataclass(frozen=True, slots=True)
class Gt(Expr):
    esq: Expr
    dir: Expr


@dataclass(frozen=True, slots=True)
class Ge(Expr):
    esq: Expr
    dir: Expr


@dataclass(frozen=True, slots=True)
class Lt(Expr):
    esq: Expr
    dir: Expr


@dataclass(frozen=True, slots=True)
class Le(Expr):
    esq: Expr
    dir: Expr


Relacao: TypeAlias = Eq | Ne | Gt | Ge | Lt | Le
RELACOES: tuple[type[Expr], ...] = (Eq, Ne, Gt, Ge, Lt, Le)
FUNCOES_UNARIAS: tuple[type[Expr], ...] = (Exp, Ln, Sin, Cos, Tan, Abs, Sqrt)

TODOS_OS_NOS: dict[str, type[Expr]] = {
    c.__name__: c
    for c in (
        Num, Sym, Add, Sub, Neg, Mul, Div, Pow, Sqrt, Root, Exp, Ln, Log, Sin, Cos, Tan,
        Abs, Func, Deriv, PDeriv, Integral, Eq, Ne, Gt, Ge, Lt, Le,
    )
}


def eh_relacao(e: Expr) -> bool:
    return isinstance(e, RELACOES)


def percorrer(e: Expr) -> Iterator[Expr]:
    """Percorre a árvore em pré-ordem."""
    yield e
    for f in e.filhos():
        yield from percorrer(f)


def simbolos(e: Expr) -> set[str]:
    """Ids de todos os símbolos (incluindo variáveis de derivada e integral)."""
    ids: set[str] = set()
    for no in percorrer(e):
        if isinstance(no, Sym):
            ids.add(no.id)
        elif isinstance(no, Func):
            ids.add(no.nome)
    return ids
