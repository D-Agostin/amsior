# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Tabela própria do verificador: o que cada operação faz e quando preserva a equivalência.

Esta tabela é independente do catálogo de regras do motor de passos. Um passo
cuja relação ou cujas condições sejam mais otimistas do que esta tabela
permite é reprovado, mesmo que a conta esteja certa.

Dois tipos de exigência:

* ``dominio``: sem ela a operação nem está definida (dividir por zero, ln de
  não positivo). Se não for garantida pelas suposições nem declarada, o passo
  é reprovado.
* ``equivalencia``: sem ela a operação vale, mas só num sentido (multiplicar
  por algo que pode ser zero, elevar ao quadrado). Se não for garantida, a
  relação máxima é ``implica``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import sympy as sp

Predicado = Literal["nao_nulo", "positivo", "nao_negativo"]


@dataclass(frozen=True)
class Exigencia:
    expr: Any
    predicado: Predicado
    tipo: Literal["dominio", "equivalencia"]


@dataclass
class EfeitoOperacao:
    esquerdo: Any
    direito: Any
    relacao_base: Literal["equivalente", "implica"] = "equivalente"
    exigencias: list[Exigencia] = field(default_factory=list)


def _inteiro_impar(k: Any) -> bool:
    return bool(k.is_integer and k.is_odd)


def _inteiro_par(k: Any) -> bool:
    return bool(k.is_integer and k.is_even)


def _somar(L: Any, R: Any, a: Any) -> EfeitoOperacao:
    return EfeitoOperacao(L + a, R + a)


def _subtrair(L: Any, R: Any, a: Any) -> EfeitoOperacao:
    return EfeitoOperacao(L - a, R - a)


def _multiplicar(L: Any, R: Any, a: Any) -> EfeitoOperacao:
    return EfeitoOperacao(L * a, R * a, exigencias=[Exigencia(a, "nao_nulo", "equivalencia")])


def _dividir(L: Any, R: Any, a: Any) -> EfeitoOperacao:
    return EfeitoOperacao(L / a, R / a, exigencias=[Exigencia(a, "nao_nulo", "dominio")])


def _elevar(L: Any, R: Any, k: Any) -> EfeitoOperacao:
    ef = EfeitoOperacao(sp.Pow(L, k), sp.Pow(R, k))
    if _inteiro_impar(k) and k.is_positive:
        return ef
    if _inteiro_par(k) and k.is_positive:
        ef.exigencias = [Exigencia(L, "nao_negativo", "equivalencia"),
                         Exigencia(R, "nao_negativo", "equivalencia")]
        return ef
    if k.is_integer and k.is_negative:
        ef.exigencias = [Exigencia(L, "nao_nulo", "dominio"), Exigencia(R, "nao_nulo", "dominio")]
        if _inteiro_par(k):
            ef.exigencias += [Exigencia(L, "nao_negativo", "equivalencia"),
                              Exigencia(R, "nao_negativo", "equivalencia")]
        return ef
    pred: Predicado = "positivo" if (k.is_negative or not k.is_number) else "nao_negativo"
    ef.exigencias = [Exigencia(L, pred, "dominio"), Exigencia(R, pred, "dominio")]
    return ef


def _raiz(L: Any, R: Any, n: Any) -> EfeitoOperacao:
    if _inteiro_impar(n):
        return EfeitoOperacao(sp.real_root(L, n), sp.real_root(R, n))
    return EfeitoOperacao(
        sp.root(L, n), sp.root(R, n),
        exigencias=[Exigencia(L, "nao_negativo", "dominio"), Exigencia(R, "nao_negativo", "dominio")],
    )


def _ln(L: Any, R: Any, _a: Any) -> EfeitoOperacao:
    return EfeitoOperacao(sp.log(L), sp.log(R), exigencias=[
        Exigencia(L, "positivo", "dominio"), Exigencia(R, "positivo", "dominio")])


def _log(L: Any, R: Any, base: Any) -> EfeitoOperacao:
    b = base if base is not None else sp.Integer(10)
    return EfeitoOperacao(sp.log(L, b), sp.log(R, b), exigencias=[
        Exigencia(L, "positivo", "dominio"), Exigencia(R, "positivo", "dominio"),
        Exigencia(b, "positivo", "dominio"), Exigencia(b - 1, "nao_nulo", "dominio")])


def _exp(L: Any, R: Any, _a: Any) -> EfeitoOperacao:
    return EfeitoOperacao(sp.exp(L), sp.exp(R))


def _reciproco(L: Any, R: Any, _a: Any) -> EfeitoOperacao:
    return EfeitoOperacao(1 / L, 1 / R, exigencias=[
        Exigencia(L, "nao_nulo", "dominio"), Exigencia(R, "nao_nulo", "dominio")])


def _trocar(L: Any, R: Any, _a: Any) -> EfeitoOperacao:
    return EfeitoOperacao(R, L)


def _reescrever(L: Any, R: Any, _a: Any) -> EfeitoOperacao:
    return EfeitoOperacao(L, R)


def _derivar(L: Any, R: Any, v: Any) -> EfeitoOperacao:
    return EfeitoOperacao(sp.Derivative(L, v), sp.Derivative(R, v), "implica")


def _integrar(L: Any, R: Any, v: Any) -> EfeitoOperacao:
    return EfeitoOperacao(sp.Integral(L, v), sp.Integral(R, v), "implica")


# nome → (função, exige argumento)
OPERACOES: dict[str, tuple[Callable[[Any, Any, Any], EfeitoOperacao], bool]] = {
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
    "substituir": (_reescrever, False),
    "derivar_ambos": (_derivar, True),
    "integrar_ambos": (_integrar, True),
}
