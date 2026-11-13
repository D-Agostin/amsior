# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Teste de identidade entre duas expressões (seção 5.1).

1. Simbólico: a diferença simplifica a zero sob as suposições dos símbolos.
   Usa só transformações que provam; ``sympy.equals`` não é usado porque decide
   por amostragem.
2. Numérico: se o simbólico não concluir, avalia a diferença com mpmath a 50
   dígitos em 20 pontos sorteados no domínio (suposições e condições). Resíduo
   relativo abaixo de 1e-30 em todos os pontos aprova; um ponto acima reprova.
   Um ponto em que só um dos lados existe nos reais também reprova: o passo
   mudou o domínio. É evidência forte, não prova, e recebe selo próprio.
3. Inconclusivo equivale a reprovado.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import mpmath
import sympy as sp
from sympy.core.function import AppliedUndef

DIGITOS = 50
PONTOS = 20
TENTATIVAS = 600
LIMITE_RESIDUO = mpmath.mpf("1e-30")


@dataclass
class ResultadoIdentidade:
    aprovado: bool
    metodo: Literal["simbolico", "numerico"] | None
    motivo: str = ""
    residuo: float | None = None


def _eh_zero(x: Any) -> bool:
    try:
        return bool(x == 0) or x.is_zero is True
    except Exception:
        return False


_TRANSFORMACOES: tuple[Callable[[Any], Any], ...] = (
    lambda d: d,
    lambda d: sp.cancel(sp.together(d)),
    sp.expand,
    lambda d: sp.expand(sp.expand_log(d, force=False)),
    lambda d: sp.logcombine(d, force=False),
    lambda d: sp.powsimp(sp.powdenest(d)),
    lambda d: sp.simplify(d),
    lambda d: sp.simplify(sp.expand_log(sp.expand_power_base(d), force=False)),
)


def identidade_simbolica(a: Any, b: Any) -> bool:
    try:
        dif = sp.sympify(a - b).doit()
    except Exception:
        return False
    for f in _TRANSFORMACOES:
        try:
            if _eh_zero(f(dif)):
                return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------------- numérico


def _semente(*partes: Any) -> int:
    h = hashlib.sha256("|".join(sp.srepr(p) for p in partes).encode()).hexdigest()
    return int(h[:16], 16)


def _atomizar(exprs: Sequence[Any]) -> tuple[list[Any], dict[Any, Any]]:
    """Troca funções incógnitas e derivadas por símbolos fictícios consistentes."""
    trocas: dict[Any, Any] = {}
    contador = 0
    for e in exprs:
        alvos = sorted(
            e.atoms(sp.Derivative) | e.atoms(AppliedUndef), key=sp.default_sort_key, reverse=True
        )
        for at in alvos:
            if at not in trocas:
                sup = {}
                if isinstance(at, AppliedUndef):
                    sup = {k: v for k, v in at._assumptions.items() if v is True and k in (
                        "positive", "nonnegative", "nonzero", "real", "integer")}
                trocas[at] = sp.Symbol(f"_amsior_{contador}", **(sup or {"real": True}))
                contador += 1
    return [e.xreplace(trocas) for e in exprs], trocas


def _sortear(s: Any, rng: random.Random) -> mpmath.mpf:
    mag = mpmath.mpf(10) ** mpmath.mpf(rng.uniform(-2, 2))
    if s.is_integer:
        n = rng.randint(1, 6)
        return mpmath.mpf(n if s.is_nonnegative or s.is_positive else rng.choice([-1, 1]) * n)
    if s.is_positive or s.is_nonnegative:
        return mag
    return mag * rng.choice([-1, 1])


def _real_finito(v: Any) -> mpmath.mpf | None:
    try:
        if isinstance(v, mpmath.mpc):
            if abs(v.imag) > mpmath.mpf(10) ** (-DIGITOS + 10) * max(1, abs(v.real)):
                return None
            v = v.real
        v = mpmath.mpf(v)
        if mpmath.isnan(v) or mpmath.isinf(v):
            return None
        return v
    except Exception:
        return None


def _avaliar(f: Callable[..., Any], valores: list[mpmath.mpf]) -> mpmath.mpf | None:
    try:
        return _real_finito(f(*valores))
    except (ZeroDivisionError, ValueError, OverflowError, TypeError):
        return None


def _condicao_ok(c: Callable[..., Any], valores: list[mpmath.mpf]) -> bool:
    try:
        return bool(c(*valores))
    except Exception:
        return False


def identidade_numerica(a: Any, b: Any, condicoes: Sequence[Any] = ()) -> ResultadoIdentidade:
    try:
        (a2, b2, *conds), _ = _atomizar([sp.sympify(a).doit(), sp.sympify(b).doit(),
                                         *[sp.sympify(c) for c in condicoes]])
    except Exception:
        return ResultadoIdentidade(False, None, "verif.identidade.nao_avaliavel")
    if a2.atoms(sp.Integral) or b2.atoms(sp.Integral):
        return ResultadoIdentidade(False, None, "verif.identidade.integral_nao_avaliada")
    livres = sorted(a2.free_symbols | b2.free_symbols | set().union(
        *[c.free_symbols for c in conds]), key=sp.default_sort_key)
    with mpmath.workdps(DIGITOS):
        try:
            fa = sp.lambdify(livres, a2, modules="mpmath")
            fb = sp.lambdify(livres, b2, modules="mpmath")
            fc = [sp.lambdify(livres, c, modules="mpmath") for c in conds]
        except Exception:
            return ResultadoIdentidade(False, None, "verif.identidade.nao_avaliavel")
        rng = random.Random(_semente(a2, b2, *conds))
        validos = 0
        pior = mpmath.mpf(0)
        for _ in range(TENTATIVAS):
            if validos >= PONTOS:
                break
            valores = [_sortear(s, rng) for s in livres]
            if not all(_condicao_ok(c, valores) for c in fc):
                continue
            va, vb = _avaliar(fa, valores), _avaliar(fb, valores)
            if va is None and vb is None:
                continue
            if va is None or vb is None:
                return ResultadoIdentidade(False, None, "verif.identidade.dominio_diferente")
            escala = max(abs(va), abs(vb), mpmath.mpf(1))
            residuo = abs(va - vb) / escala
            if residuo > LIMITE_RESIDUO:
                return ResultadoIdentidade(
                    False, None, "verif.identidade.residuo", float(residuo))
            pior = max(pior, residuo)
            validos += 1
        if validos < PONTOS:
            return ResultadoIdentidade(False, None, "verif.identidade.amostras_insuficientes")
        return ResultadoIdentidade(True, "numerico", residuo=float(pior))


def identicas(a: Any, b: Any, condicoes: Sequence[Any] = ()) -> ResultadoIdentidade:
    """Identidade entre expressões SymPy: simbólica, senão numérica.

    Com condições, a prova simbólica (que só usa as suposições dos símbolos) é
    pulada: a identidade depende das condições e só a amostragem as respeita.
    """
    if not condicoes and identidade_simbolica(a, b):
        return ResultadoIdentidade(True, "simbolico")
    return identidade_numerica(a, b, condicoes)
