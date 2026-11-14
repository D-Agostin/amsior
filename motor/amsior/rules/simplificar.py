# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Simplificações de apresentação, sempre visíveis como passo próprio.

Depois de uma operação nos dois lados (dividir por ``P``), o lado mostra a
operação literal (``PV/P``); o passo seguinte cancela o que se anula. Este
módulo faz só o cancelamento estrutural de fatores e de parcelas iguais, sem
reordenar o que o autor escreveu e sem expandir nada. Cada resultado volta ao
verificador como passo ``reescrever``: um cancelamento errado é reprovado.
"""

from __future__ import annotations

from amsior.expr.nos import Add, Div, Expr, Mul, Neg, Num, Pow, Sub, Sym

_UM = Num("1")


# ---------------------------------------------------------------- produtos


def _fatores(e: Expr) -> tuple[int, list[Expr], list[Expr]]:
    """(sinal, numerador, denominador) de um produto ou quociente."""
    if isinstance(e, Neg):
        s, n, d = _fatores(e.a)
        return -s, n, d
    if isinstance(e, Mul):
        sinal, num, den = 1, [], []
        for f in e.fatores:
            s, n, d = _fatores(f)
            sinal *= s
            num += n
            den += d
        return sinal, num, den
    if isinstance(e, Div):
        s1, n1, d1 = _fatores(e.num)
        s2, n2, d2 = _fatores(e.den)
        return s1 * s2, n1 + d2, d1 + n2
    if e == _UM:
        return 1, [], []
    return 1, [e], []


def produto(sinal: int, num: list[Expr], den: list[Expr]) -> Expr:
    n: Expr = _UM if not num else num[0] if len(num) == 1 else Mul(tuple(num))
    r: Expr = n
    if den:
        d = den[0] if len(den) == 1 else Mul(tuple(den))
        r = Div(n, d)
    return Neg(r) if sinal < 0 else r


def _cancelar_fatores(e: Expr) -> Expr:
    sinal, num, den = _fatores(e)
    num, den = list(num), list(den)
    antes = len(num) + len(den)
    for f in list(num):
        if f in den:
            num.remove(f)
            den.remove(f)
    if len(num) + len(den) == antes:
        return e
    return produto(sinal, num, den)


# ---------------------------------------------------------------- somas


def _termos(e: Expr) -> list[tuple[int, Expr]]:
    if isinstance(e, Add):
        return [t for x in e.termos for t in _termos(x)]
    if isinstance(e, Sub):
        return _termos(e.a) + [(-s, t) for s, t in _termos(e.b)]
    if isinstance(e, Neg) and isinstance(e.a, Add | Sub | Neg):
        return [(-s, t) for s, t in _termos(e.a)]
    if isinstance(e, Neg):
        return [(-1, e.a)]
    return [(1, e)]


def soma(termos: list[tuple[int, Expr]]) -> Expr:
    """Reconstrói a soma; se a primeira parcela é negativa e há positiva, ela vai na frente."""
    if not termos:
        return Num("0")
    if termos[0][0] < 0:
        pos = [i for i, (s, _) in enumerate(termos) if s > 0]
        if pos:
            i = pos[0]
            termos = [termos[i], *termos[:i], *termos[i + 1:]]
    s0, t0 = termos[0]
    r: Expr = t0 if s0 > 0 else Neg(t0)
    for s, t in termos[1:]:
        if s > 0:
            r = Add((*r.termos, t)) if isinstance(r, Add) else Add((r, t))
        else:
            r = Sub(r, t)
    return r


def _cancelar_termos(e: Expr) -> Expr:
    termos = _termos(e)
    restantes = [(s, t) for s, t in termos if t != Num("0")]
    for s, t in termos:
        if (s, t) in restantes and (-s, t) in restantes:
            restantes.remove((s, t))
            restantes.remove((-s, t))
    if len(restantes) == len(termos):
        return e  # nada se cancelou: a forma do autor fica
    return soma(restantes)


# ---------------------------------------------------------------- API


def cancelar(e: Expr) -> Expr:
    """Cancela fatores e parcelas estruturalmente iguais no nível de cima de ``e``."""
    if isinstance(e, Add | Sub) or isinstance(e, Neg) and isinstance(e.a, Add | Sub):
        r = _cancelar_termos(e)
        return r if r != e else e
    if isinstance(e, Mul | Div | Neg):
        r = _cancelar_fatores(e)
        return r if r != e else e
    return e


def sem_sinal_duplo(e: Expr) -> Expr:
    """−(−x) → x e −(b − a) → a − b, só no nível de cima."""
    if isinstance(e, Neg) and isinstance(e.a, Neg):
        return e.a.a
    if isinstance(e, Neg) and isinstance(e.a, Sub | Add):
        return soma([(-s, t) for s, t in _termos(e.a)])
    return e


# ---------------------------------------------------------------- acabamento


def _classe(f: Expr) -> int:
    """Ordem dos fatores na apresentação: números, símbolos, potências de símbolo, o resto."""
    if isinstance(f, Num) or isinstance(f, Sym) and f.id == "\\pi":
        return 0
    if isinstance(f, Sym):
        return 1
    if isinstance(f, Pow) and isinstance(f.base, Sym):
        return 2
    return 3


def apresentar(e: Expr) -> Expr:
    """Forma de leitura: fração de frações achatada, produtos sem parênteses
    aninhados, sinal na frente, números e símbolos antes de funções e somas.
    Só reorganiza; quem confere a igualdade é o verificador."""
    from amsior.verify.arvore import mapear
    if isinstance(e, Mul | Div | Neg) and not (isinstance(e, Neg) and isinstance(e.a, Add | Sub)):
        sinal, num, den = _fatores(e)
        num = sorted((apresentar(f) for f in num), key=_classe)
        den = sorted((apresentar(f) for f in den), key=_classe)
        return produto(sinal, num, den)
    if isinstance(e, Add | Sub) or isinstance(e, Neg):
        return soma([(s, apresentar(t)) for s, t in _termos(e)])
    return mapear(e, apresentar)
