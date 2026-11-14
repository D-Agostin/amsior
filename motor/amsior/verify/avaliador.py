# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Avaliador numérico próprio da árvore AmsiorExpr (contraprova da via simbólica).

Avalia a árvore direto em mpmath, nos reais, sem passar pelo SymPy: um erro
na conversão para o SymPy não engana as duas vias ao mesmo tempo.

Semântica (a mesma que ``dominio.py`` descreve com obrigações):

* fora do domínio real o valor é ``None`` (ln de não positivo, divisão por
  zero, raiz par de negativo, base não positiva com expoente não inteiro);
* raiz de índice ímpar é a raiz real (``∛(−8) = −2``);
* símbolo que declara dependências e função incógnita ``y(t)`` viram funções
  suaves sorteadas (fixas pela semente), com o sinal das suposições: uma
  identidade que vale para toda função vale para elas, e uma que não vale
  falha com probabilidade 1;
* derivadas por diferenciação numérica (``mpmath.diff``); integrais definidas
  por quadratura (``mpmath.quad``), depois de conferir que o integrando existe
  no intervalo inteiro.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable
from typing import Any

import mpmath as mp
import sympy as sp

from amsior.expr.nos import (
    Abs, Add, Cos, Deriv, Div, Eq, Exp, Expr, Func, Ge, Gt, Integral, Le, Ln, Log, Lt, Mul,
    Ne, Neg, Num, PDeriv, Pow, Root, Sin, Sqrt, Sub, Sym, Tan,
)
from amsior.expr.ponte_sympy import ParaSympy
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.verify.arvore import chave, fracao_exata
from amsior.verify.dominio import Obrigacao, obrigacoes
from amsior.verify.logica import normalizar

Valor = Any  # mpmath.mpf | bool | None


class ForaDoDominio(Exception):
    pass


class Estouro(Exception):
    """Valor grande demais para calcular com precisão em tempo útil (ex.: exp(exp(10⁹)))."""


LIMITE_ARGUMENTO = mp.mpf(10) ** 7  # |argumento| de exp e de potência real
LIMITE_TRIG = mp.mpf(10) ** 20


def _semente(*partes: str) -> int:
    return int(hashlib.sha256("|".join(partes).encode()).hexdigest()[:16], 16)


class _FuncaoSorteada:
    """f(x₁…xₖ) suave, genérica e com o sinal das suposições."""

    def __init__(self, nome: str, aridade: int, suposicoes: frozenset[str], semente: int) -> None:
        rng = random.Random(_semente(nome, str(semente)))

        def u(a: float, b: float) -> Any:
            return mp.mpf(rng.uniform(a, b))

        self.c0 = u(-1, 1)
        self.termos = [(u(0.3, 1.2), u(0.5, 2), u(0, 3), u(0.2, 0.8), u(0.1, 1))
                       for _ in range(aridade)]
        self.cruzado = u(0.1, 0.5) if aridade > 1 else mp.mpf(0)
        self.escala = mp.mpf(10) ** u(-2, 2)
        self.positiva = bool(suposicoes & {"positivo", "nao_negativo", "nao_nulo"})

    def __call__(self, *xs: Any) -> Any:
        g = self.c0
        for (a, b, p, d, e), x in zip(self.termos, xs, strict=True):
            g += a * mp.sin(b * x + p) + d * mp.tanh(e * x)
        if len(xs) > 1:
            g += self.cruzado * mp.sin(xs[0] * xs[1] / 3)
        return self.escala * (mp.exp(g) if self.positiva else g)


class Avaliador:
    def __init__(self, tabela: TabelaDeSimbolos, semente: int = 0) -> None:
        self.tabela = tabela
        self.semente = semente
        self.conv = ParaSympy(tabela)
        self._funcoes: dict[tuple[str, int], _FuncaoSorteada] = {}
        self._obrig_integrais: dict[str, list[Obrigacao]] = {}
        self.estourou = False

    # ------------------------------------------------------------ API

    def valor(self, e: Expr, env: dict[str, Any]) -> Valor:
        """Valor real finito no contexto de precisão atual, ou None.

        ``estourou`` fica verdadeiro quando o None vem de um valor grande demais,
        e não de um ponto fora do domínio.
        """
        self.estourou = False
        try:
            v = self._v(e, env)
        except Estouro:
            self.estourou = True
            return None
        except (ForaDoDominio, ZeroDivisionError, ValueError, OverflowError, TypeError,
                KeyError, mp.libmp.libhyper.NoConvergence):
            return None
        if isinstance(v, bool):
            return v
        return _finito(v)

    def funcao(self, nome: str, aridade: int) -> _FuncaoSorteada:
        k = (nome, aridade)
        if k not in self._funcoes:
            self._funcoes[k] = _FuncaoSorteada(nome, aridade, self.tabela.suposicoes(nome),
                                               self.semente)
        return self._funcoes[k]

    # ------------------------------------------------------------ nós

    def _v(self, e: Expr, env: dict[str, Any]) -> Any:  # noqa: C901 - um ramo por nó
        v = self._v
        if isinstance(e, Num):
            q = e.fracao()
            return mp.mpf(q.numerator) / q.denominator
        if isinstance(e, Sym):
            if e.id == "\\pi":
                return +mp.pi
            if e.id == "\\infty":
                return mp.inf
            s = self.tabela.obter(e.id)
            if s is not None and s.depende_de and s.papel != "funcao" and e.id not in env:
                args = [env[d] for d in s.depende_de]
                return self.funcao(e.id, len(args))(*args)
            return env[e.id]
        if isinstance(e, Add):
            return mp.fsum(_num(v(t, env)) for t in e.termos)
        if isinstance(e, Sub):
            return _num(v(e.a, env)) - _num(v(e.b, env))
        if isinstance(e, Neg):
            return -_num(v(e.a, env))
        if isinstance(e, Mul):
            total = mp.mpf(1)
            for f in e.fatores:
                total *= _num(v(f, env))
            return total
        if isinstance(e, Div):
            d = _num(v(e.den, env))
            if d == 0:
                raise ForaDoDominio
            return _num(v(e.num, env)) / d
        if isinstance(e, Pow):
            return self._pow(e, env)
        if isinstance(e, Sqrt):
            a = _num(v(e.a, env))
            if a < 0:
                raise ForaDoDominio
            return mp.sqrt(a)
        if isinstance(e, Root):
            return self._raiz(e, env)
        if isinstance(e, Exp):
            a = _num(v(e.a, env))
            if abs(a) > LIMITE_ARGUMENTO:
                raise Estouro
            return mp.exp(a)
        if isinstance(e, Ln):
            a = _num(v(e.a, env))
            if a <= 0:
                raise ForaDoDominio
            return mp.log(a)
        if isinstance(e, Log):
            a, b = _num(v(e.a, env)), _num(v(e.base, env))
            if a <= 0 or b <= 0 or b == 1:
                raise ForaDoDominio
            return mp.log(a) / mp.log(b)
        if isinstance(e, Sin):
            return mp.sin(_trig(_num(v(e.a, env))))
        if isinstance(e, Cos):
            return mp.cos(_trig(_num(v(e.a, env))))
        if isinstance(e, Tan):
            a = _trig(_num(v(e.a, env)))
            if mp.cos(a) == 0:
                raise ForaDoDominio
            return mp.tan(a)
        if isinstance(e, Abs):
            return abs(_num(v(e.a, env)))
        if isinstance(e, Func):
            args = [_num(v(a, env)) for a in e.args]
            return self.funcao(e.nome, len(args))(*args)
        if isinstance(e, Deriv | PDeriv):
            if isinstance(e, PDeriv) and e.mantidas:
                raise ForaDoDominio  # opaco: tratado antes de chegar aqui
            var = e.var.id
            x0 = env[var]
            g = self._funcao_de(e.f, env, var)
            return mp.diff(g, x0, e.ordem)
        if isinstance(e, Integral):
            return self._integral(e, env)
        if isinstance(e, Eq | Ne | Gt | Ge | Lt | Le):
            a, b = _num(v(e.esq, env)), _num(v(e.dir, env))
            return {Eq: a == b, Ne: a != b, Gt: a > b, Ge: a >= b, Lt: a < b,
                    Le: a <= b}[type(e)]
        raise TypeError(f"nó sem avaliação: {type(e).__name__}")

    def _funcao_de(self, f: Expr, env: dict[str, Any], var: str) -> Callable[[Any], Any]:
        def g(s: Any) -> Any:
            r = self.valor(f, {**env, var: s})
            if r is None or isinstance(r, bool):
                raise ForaDoDominio
            return r
        return g

    def _pow(self, e: Pow, env: dict[str, Any]) -> Any:
        b = _num(self._v(e.base, env))
        k = fracao_exata(e.exp)
        if k is not None and k.denominator == 1:
            if b == 0 and k <= 0:
                raise ForaDoDominio
            if b != 0 and abs(k * mp.log(abs(b))) > LIMITE_ARGUMENTO:
                raise Estouro
            return b ** int(k)
        x = _num(self._v(e.exp, env))
        if b > 0:
            if abs(x * mp.log(b)) > LIMITE_ARGUMENTO:
                raise Estouro
            return b ** x
        if b == 0 and x > 0:
            return mp.mpf(0)
        raise ForaDoDominio

    def _raiz(self, e: Root, env: dict[str, Any]) -> Any:
        a = _num(self._v(e.a, env))
        k = fracao_exata(e.n)
        if k is not None and k.denominator == 1 and k != 0:
            n = int(k)
            if n % 2 == 1:
                r = mp.root(abs(a), abs(n))
                r = -r if a < 0 else r
                return r if n > 0 else 1 / r
            if a < 0:
                raise ForaDoDominio
            return mp.root(a, n) if n > 0 else 1 / mp.root(a, -n)
        n_val = _num(self._v(e.n, env))
        if a <= 0 or n_val == 0:
            raise ForaDoDominio
        return a ** (1 / n_val)

    # ------------------------------------------------------------ integrais

    def _integral(self, e: Integral, env: dict[str, Any]) -> Any:
        if e.inferior is None or e.superior is None:
            raise ForaDoDominio  # indefinida: opaca, tratada antes
        lo, hi = _num(self._v(e.inferior, env)), _num(self._v(e.superior, env))
        if lo == hi:
            return mp.mpf(0)
        if not self._intervalo_ok(e, env, lo, hi):
            raise ForaDoDominio
        g = self._funcao_de(e.f, env, e.var.id)
        sinal = 1
        if lo > hi:
            lo, hi, sinal = hi, lo, -1
        return sinal * mp.quad(g, _pontos(lo, hi))

    def _intervalo_ok(self, e: Integral, env: dict[str, Any], lo: Any, hi: Any) -> bool:
        """O integrando existe em todo o intervalo [lo, hi]?"""
        k = chave(e)
        if k not in self._obrig_integrais:
            self._obrig_integrais[k] = [o for o in obrigacoes(e.f) if isinstance(o, Obrigacao)]
        w = self.conv.simbolo(e.var.id)
        for o in self._obrig_integrais[k]:
            try:
                q = self.conv(o.expr)
                fixos = {s: sp.Rational(mp.nstr(env[str(s)], 40)) for s in q.free_symbols
                         if s != w and str(s) in env}
                comps = normalizar(q.xreplace(fixos), o.predicado)
            except Exception:
                return False
            if comps is None:
                return False
            for g, pred in comps:
                if not _vale_no_intervalo(g, w, lo, hi, pred):
                    return False
        return True


def _vale_no_intervalo(g: Any, w: Any, lo: Any, hi: Any, pred: str) -> bool:
    a, b = (sp.Rational(mp.nstr(x, 40)) if mp.isfinite(x) else (sp.oo if x > 0 else -sp.oo)
            for x in (lo, hi))
    if a > b:
        a, b = b, a
    intervalo = sp.Interval(a, b)
    ruim = {"nao_nulo": sp.Eq(g, 0), "positivo": g <= 0, "nao_negativo": g < 0}[pred]
    try:
        conj = sp.solveset(ruim, w, intervalo)
        if conj is sp.S.EmptySet:
            return True
        if isinstance(conj, sp.FiniteSet | sp.Interval | sp.Union):
            return False
    except Exception:
        pass
    # sem resposta exata: varredura densa com detecção de troca de sinal
    f = sp.lambdify(w, g, modules="mpmath")
    pts = _pontos(lo if mp.isfinite(lo) else -mp.mpf(10) ** 9,
                  hi if mp.isfinite(hi) else mp.mpf(10) ** 9, 400)
    anterior = None
    for p in pts:
        try:
            y = _finito(f(p))
        except Exception:
            return False
        if y is None:
            return False
        if pred == "positivo" and y <= 0 or pred == "nao_negativo" and y < 0:
            return False
        if pred == "nao_nulo" and (y == 0 or anterior is not None and anterior * y < 0):
            return False
        anterior = y
    return True


def _pontos(lo: Any, hi: Any, n: int = 0) -> list[Any]:
    """Pontos de subdivisão: espaçados em escala log quando o intervalo cobre décadas."""
    if lo > 0 and hi / lo > 10 or hi < 0 and lo / hi > 10:
        sinal = 1 if lo > 0 else -1
        a, b = abs(lo), abs(hi)
        m = max(n, int(mp.ceil(mp.log10(max(a, b) / min(a, b)))) + 1)
        pts = [sinal * min(a, b) * (max(a, b) / min(a, b)) ** (mp.mpf(i) / m) for i in range(m + 1)]
        return sorted(pts)
    m = max(n, 2)
    return [lo + (hi - lo) * mp.mpf(i) / m for i in range(m + 1)]


def _trig(x: Any) -> Any:
    if abs(x) > LIMITE_TRIG:
        raise Estouro
    return x


def _num(x: Any) -> Any:
    if x is None or isinstance(x, bool):
        raise ForaDoDominio
    return x


def _finito(v: Any) -> Any:
    try:
        if isinstance(v, mp.mpc):
            return None
        v = mp.mpf(v)
        if mp.isnan(v) or mp.isinf(v):
            return None
        return v
    except Exception:
        return None
