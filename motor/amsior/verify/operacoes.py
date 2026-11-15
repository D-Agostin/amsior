# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Tabela própria do verificador: o que cada operação faz e quando preserva a equivalência.

Esta tabela é independente do catálogo de regras do motor de passos. Cada
operação monta, na árvore AmsiorExpr, o resultado esperado de aplicá-la aos
dois lados; o domínio desse resultado (divisor ≠ 0, argumento de ln > 0...)
sai das obrigações de domínio da própria árvore (``dominio.py``).

A tabela declara só o que o domínio não mostra: as exigências de
**equivalência**. Sem elas a operação vale, mas num sentido só
(multiplicar por algo que pode ser zero, elevar ao quadrado, elevar a zero),
e a relação máxima é ``implica``.

Argumentos inválidos (índice de raiz que não é inteiro ≥ 2, variável de
derivação que não é símbolo) reprovam o passo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from amsior.expr.nos import (
    Add, Deriv, Div, Exp, Expr, Integral, Ln, Log, Mul, Num, Pow, Root, Sqrt, Sub, Sym,
)
from amsior.verify.arvore import fracao_exata
from amsior.verify.dominio import Predicado


@dataclass(frozen=True)
class Exigencia:
    expr: Expr
    predicado: Predicado


@dataclass
class EfeitoOperacao:
    esquerdo: Expr
    direito: Expr
    relacao_base: Literal["equivalente", "implica"] = "equivalente"
    exigencias: list[Exigencia] = field(default_factory=list)
    erro: str | None = None  # chave do motivo, se o argumento é inválido


def _somar(L: Expr, R: Expr, a: Expr | None) -> EfeitoOperacao:
    assert a is not None
    return EfeitoOperacao(Add((L, a)), Add((R, a)))


def _subtrair(L: Expr, R: Expr, a: Expr | None) -> EfeitoOperacao:
    assert a is not None
    return EfeitoOperacao(Sub(L, a), Sub(R, a))


def _multiplicar(L: Expr, R: Expr, a: Expr | None) -> EfeitoOperacao:
    assert a is not None
    return EfeitoOperacao(Mul((L, a)), Mul((R, a)), exigencias=[Exigencia(a, "nao_nulo")])


def _dividir(L: Expr, R: Expr, a: Expr | None) -> EfeitoOperacao:
    assert a is not None
    return EfeitoOperacao(Div(L, a), Div(R, a))


def _elevar(L: Expr, R: Expr, k: Expr | None) -> EfeitoOperacao:
    assert k is not None
    ef = EfeitoOperacao(Pow(L, k), Pow(R, k))
    q = fracao_exata(k)
    if q is None:  # expoente simbólico: t ↦ tᵏ só é injetora se k ≠ 0
        ef.exigencias = [Exigencia(k, "nao_nulo")]
    elif q == 0:
        ef.exigencias = [Exigencia(Num("0"), "nao_nulo")]  # falsa: só implica
    elif q.denominator == 1 and int(q) % 2 == 0:
        ef.exigencias = [Exigencia(L, "nao_negativo"), Exigencia(R, "nao_negativo")]
    return ef


def _raiz(L: Expr, R: Expr, n: Expr | None) -> EfeitoOperacao:
    assert n is not None
    q = fracao_exata(n)
    if q is None or q.denominator != 1 or q < 2:
        return EfeitoOperacao(L, R, erro="verif.indice_invalido")
    if q == 2:
        return EfeitoOperacao(Sqrt(L), Sqrt(R))
    return EfeitoOperacao(Root(L, n), Root(R, n))


def _ln(L: Expr, R: Expr, _a: Expr | None) -> EfeitoOperacao:
    return EfeitoOperacao(Ln(L), Ln(R))


def _log(L: Expr, R: Expr, base: Expr | None) -> EfeitoOperacao:
    b = base if base is not None else Num("10")
    return EfeitoOperacao(Log(L, b), Log(R, b))


def _exp(L: Expr, R: Expr, _a: Expr | None) -> EfeitoOperacao:
    return EfeitoOperacao(Exp(L), Exp(R))


def _reciproco(L: Expr, R: Expr, _a: Expr | None) -> EfeitoOperacao:
    return EfeitoOperacao(Div(Num("1"), L), Div(Num("1"), R))


def _trocar(L: Expr, R: Expr, _a: Expr | None) -> EfeitoOperacao:
    return EfeitoOperacao(R, L)


def _reescrever(L: Expr, R: Expr, _a: Expr | None) -> EfeitoOperacao:
    return EfeitoOperacao(L, R)


def _derivar(L: Expr, R: Expr, v: Expr | None) -> EfeitoOperacao:
    if not isinstance(v, Sym) or v.id in ("\\pi", "\\infty"):
        return EfeitoOperacao(L, R, erro="verif.argumento_invalido")
    return EfeitoOperacao(Deriv(L, v), Deriv(R, v), "implica")


def _integrar(L: Expr, R: Expr, v: Expr | None) -> EfeitoOperacao:
    if not isinstance(v, Sym) or v.id in ("\\pi", "\\infty"):
        return EfeitoOperacao(L, R, erro="verif.argumento_invalido")
    return EfeitoOperacao(Integral(L, v), Integral(R, v), "implica")


Funcao = Callable[[Expr, Expr, Expr | None], EfeitoOperacao]

# nome → (função, exige argumento)
OPERACOES: dict[str, tuple[Funcao, bool]] = {
    "somar_ambos": (_somar, True),
    "subtrair_ambos": (_subtrair, True),
    "multiplicar_ambos": (_multiplicar, True),
    "dividir_ambos": (_dividir, True),
    "elevar_ambos": (_elevar, True),
    "raiz_ambos": (_raiz, True),
    "ln_ambos": (_ln, False),
    "log_ambos": (_log, False),
    "exp_ambos": (_exp, False),
    "reciproco_ambos": (_reciproco, False),
    "trocar_lados": (_trocar, False),
    "reescrever": (_reescrever, False),
    "substituir": (_reescrever, True),
    "derivar_ambos": (_derivar, True),
    "integrar_ambos": (_integrar, True),
}

OPERACOES_DE_CALCULO = frozenset({"derivar_ambos", "integrar_ambos"})
