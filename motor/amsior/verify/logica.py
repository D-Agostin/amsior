# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Prova de obrigações de domínio a partir de fatos (suposições, condições, domínio).

Uma obrigação é provada quando decorre:

1. das suposições dos símbolos (sistema de suposições do SymPy);
2. de um fato normalizado igual (ou oposto, para ``≠ 0``).

``sympy.ask`` não é usado: na versão 1.14 ele responde ``True`` para
``−a > 0`` dado ``a ≠ 0`` (teste ``test_sympy_ask_nao_e_confiavel``).

A normalização reduz cada predicado a componentes comparáveis, sempre por
equivalências válidas onde a expressão existe:

* ``p/q ≠ 0`` ⇔ cada fator de ``p`` ≠ 0;
* ``p/q > 0`` ⇔ ``p·q > 0``, com fatores de expoente par trocados por ``≠ 0``
  e fatores de sinal conhecido retirados;
* ``ln x ≠ 0`` ⇔ ``x − 1 ≠ 0``; ``|g| > 0`` ⇔ ``g ≠ 0``; ``exp(·)`` é sempre positivo.

Se nada disso prova a obrigação, ela fica sem prova: o verificador reprova ou
rebaixa o passo. A falta de prova nunca aprova nada.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import sympy as sp

from amsior.verify.dominio import Predicado

_FORTES: dict[Predicado, set[Predicado]] = {  # quem prova quem
    "positivo": {"positivo", "nao_negativo", "nao_nulo"},
    "nao_negativo": {"nao_negativo"},
    "nao_nulo": {"nao_nulo"},
}


def _zero(e: Any) -> bool:
    try:
        if sp.expand(e) == 0:
            return True
        if sp.cancel(sp.together(e)) == 0:
            return True
        if sp.count_ops(e) <= 40:
            return bool(sp.simplify(e) == 0)
    except Exception:
        return False
    return False


def por_suposicao(q: Any, pred: Predicado) -> bool:
    """O predicado decorre só das suposições dos símbolos?"""
    for cand in (q, _simplificar(q)):
        if cand is None:
            continue
        if pred == "positivo" and cand.is_positive is True:
            return True
        if pred == "nao_negativo" and cand.is_nonnegative is True:
            return True
        if pred == "nao_nulo" and (cand.is_nonzero is True or cand.is_positive is True
                                   or cand.is_negative is True):
            return True
    return False


def refutado_por_suposicao(q: Any, pred: Predicado) -> bool:
    """O predicado é falso em todo ponto permitido pelas suposições?"""
    for cand in (q, _simplificar(q)):
        if cand is None:
            continue
        real = cand.is_extended_real is True
        if pred == "positivo" and real and cand.is_positive is False:
            return True
        if pred == "nao_negativo" and real and cand.is_negative is True:
            return True
        if pred == "nao_nulo" and cand.is_zero is True:
            return True
    return False


def _simplificar(q: Any) -> Any:
    try:
        return sp.simplify(q) if sp.count_ops(q) <= 60 else None
    except Exception:
        return None


# ---------------------------------------------------------------- normalização

Componente = tuple[Any, Predicado]


def _fatores(e: Any) -> list[tuple[Any, Any]]:
    """Fatores (base, expoente) de um produto, já fatorado quando barato."""
    try:
        if sp.count_ops(e) <= 60:
            e = sp.factor(e)
    except Exception:
        pass
    out: list[tuple[Any, Any]] = []
    for f in sp.Mul.make_args(e):
        b, k = f.as_base_exp()
        out.append((b, k))
    return out


def normalizar(q: Any, pred: Predicado) -> list[Componente] | None:
    """Componentes cuja conjunção equivale ao predicado (onde ``q`` existe).

    Devolve None se o predicado é falso com certeza (ex.: ``0 ≠ 0``).
    """
    try:
        num, den = sp.fraction(sp.together(q))
    except Exception:
        return [(q, pred)]
    comps: list[Componente] = []
    if pred == "nao_nulo":
        for b, k in _fatores(num):
            if b.is_number:
                if b == 0:
                    return None
                continue
            if isinstance(b, sp.exp):
                continue
            if isinstance(b, sp.Abs):  # |g| ≠ 0 ⇔ g ≠ 0
                comps.extend(normalizar(b.args[0], "nao_nulo") or [(b.args[0], "nao_nulo")])
                continue
            if isinstance(b, sp.log):
                sub = normalizar(b.args[0] - 1, "nao_nulo")
                if sub is None:
                    return None
                comps.extend(sub)
                continue
            if k.is_positive or not k.is_number:
                comps.append((b, "nao_nulo"))
        return comps
    sinal = 1
    impares: list[Any] = []
    for parte, eh_num in ((num, True), (den, False)):
        for b, k in _fatores(parte):
            if b.is_number:
                if b == 0:
                    if not eh_num:
                        return None
                    return None if pred == "positivo" else []
                if b.is_negative:
                    if k.is_integer and k.is_odd:
                        sinal = -sinal
                    elif not k.is_integer:
                        return [(q, pred)]
                continue
            if isinstance(b, sp.exp) or por_suposicao(b, "positivo"):
                continue
            if isinstance(b, sp.Abs) and k.is_integer:  # |g|ᵏ ≥ 0, e > 0 ⇔ g ≠ 0
                if pred == "positivo":
                    comps.append((b.args[0], "nao_nulo"))
                continue
            if k.is_integer and k.is_even:
                if pred == "positivo":
                    comps.append((b, "nao_nulo"))
                continue
            if k.is_integer and k.is_odd:
                if por_suposicao(-b, "positivo"):
                    sinal = -sinal
                    continue
                impares.append(b)
                continue
            if k.is_number and k.is_rational:  # potência fracionária: base ≥ 0 é obrigação à parte
                if pred == "positivo":
                    comps.append((b, "nao_nulo"))
                continue
            return [(q, pred)]
    produto = sp.Mul(*impares) * sinal
    if produto == 1:
        return comps
    if produto == -1:
        return None if pred == "positivo" else [(q, pred)]
    comps.append((produto, pred))
    return comps


# ---------------------------------------------------------------- base de fatos


@dataclass
class Fato:
    expr: Any
    predicado: Predicado
    rotulo: str


@dataclass
class BaseDeFatos:
    fatos: list[Fato] = field(default_factory=list)

    def adicionar(self, q: Any, pred: Predicado, rotulo: str) -> None:
        comps = normalizar(q, pred)
        if comps is None:
            return
        brutos: list[Componente] = [(q, pred), *comps]
        # fatores de algo não nulo ou positivo também são não nulos
        if pred in ("nao_nulo", "positivo"):
            try:
                num, den = sp.fraction(sp.together(q))
                for parte in (num, den):
                    for b, _k in _fatores(parte):
                        if not b.is_number:
                            brutos.append((b, "nao_nulo"))
            except Exception:
                pass
        for e, p in brutos:
            self.fatos.append(Fato(e, p, rotulo))
        # x ≥ 0 e x ≠ 0 dão x > 0
        for f in list(self.fatos):
            for g in list(self.fatos):
                if f.predicado == "nao_negativo" and g.predicado == "nao_nulo" \
                        and _zero(f.expr - g.expr):
                    novo = Fato(f.expr, "positivo", f.rotulo + "+" + g.rotulo)
                    if novo not in self.fatos:
                        self.fatos.append(novo)

    def estender(self, outra: BaseDeFatos) -> BaseDeFatos:
        return BaseDeFatos([*self.fatos, *outra.fatos])

    def provar(self, q: Any, pred: Predicado) -> set[str] | None:
        """Rótulos dos fatos usados, conjunto vazio se bastaram as suposições,
        ou None se não há prova."""
        if por_suposicao(q, pred):
            return set()
        comps = normalizar(q, pred)
        if comps is None:
            return None
        usados: set[str] = set()
        for c in comps:
            r = self._componente(*c)
            if r is None:
                return None
            usados |= r
        return usados

    def _componente(self, g: Any, pred: Predicado) -> set[str] | None:
        if por_suposicao(g, pred):
            return set()
        for f in self.fatos:
            if pred not in _FORTES[f.predicado]:
                continue
            if _zero(g - f.expr):
                return {f.rotulo}
            if pred == "nao_nulo" and _zero(g + f.expr):
                return {f.rotulo}
        return None


def base(fatos: Iterable[tuple[Any, Predicado, str]]) -> BaseDeFatos:
    b = BaseDeFatos()
    for q, p, r in fatos:
        b.adicionar(q, p, r)
    return b
