# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Serialização JSON da AmsiorExpr: ``{"Nome": [argumentos]}``.

Exemplos: ``{"Num": "3.14"}``, ``{"Sym": "T_{1}"}``, ``{"Eq": [a, b]}``,
``{"Integral": [f, {"Sym": "T"}, inferior|null, superior|null]}``.
"""

from __future__ import annotations

from typing import Any

from amsior.expr.nos import (
    TODOS_OS_NOS, Add, Deriv, Expr, Func, Integral, Log, Mul, Num, PDeriv, Root, Sym,
)


def para_json(e: Expr) -> Any:
    nome = type(e).__name__
    if isinstance(e, Num):
        return {"Num": e.valor}
    if isinstance(e, Sym):
        return {"Sym": e.id}
    if isinstance(e, Add):
        return {"Add": [para_json(t) for t in e.termos]}
    if isinstance(e, Mul):
        return {"Mul": [para_json(f) for f in e.fatores]}
    if isinstance(e, Func):
        return {"Func": [e.nome, [para_json(a) for a in e.args]]}
    if isinstance(e, Deriv):
        return {"Deriv": [para_json(e.f), para_json(e.var), e.ordem]}
    if isinstance(e, PDeriv):
        return {"PDeriv": [para_json(e.f), para_json(e.var),
                           [para_json(s) for s in e.mantidas], e.ordem]}
    if isinstance(e, Integral):
        return {"Integral": [
            para_json(e.f), para_json(e.var),
            None if e.inferior is None else para_json(e.inferior),
            None if e.superior is None else para_json(e.superior),
        ]}
    return {nome: [para_json(f) for f in e.filhos()]}


def de_json(dado: Any) -> Expr:
    if not isinstance(dado, dict) or len(dado) != 1:
        raise ValueError(f"nó JSON inválido: {dado!r}")
    ((nome, args),) = dado.items()
    if nome not in TODOS_OS_NOS:
        raise ValueError(f"tipo de nó desconhecido: {nome}")
    if nome == "Num":
        return Num(str(args))
    if nome == "Sym":
        return Sym(str(args))
    if nome == "Add":
        return Add(tuple(de_json(a) for a in args))
    if nome == "Mul":
        return Mul(tuple(de_json(a) for a in args))
    if nome == "Func":
        return Func(str(args[0]), tuple(de_json(a) for a in args[1]))
    if nome == "Deriv":
        var = de_json(args[1])
        assert isinstance(var, Sym)
        return Deriv(de_json(args[0]), var, int(args[2]))
    if nome == "PDeriv":
        var = de_json(args[1])
        mantidas = tuple(de_json(s) for s in args[2])
        assert isinstance(var, Sym) and all(isinstance(s, Sym) for s in mantidas)
        return PDeriv(de_json(args[0]), var, mantidas, int(args[3]))  # type: ignore[arg-type]
    if nome == "Integral":
        var = de_json(args[1])
        assert isinstance(var, Sym)
        return Integral(
            de_json(args[0]), var,
            None if args[2] is None else de_json(args[2]),
            None if args[3] is None else de_json(args[3]),
        )
    if nome in ("Log", "Root"):
        cls = Log if nome == "Log" else Root
        return cls(de_json(args[0]), de_json(args[1]))
    cls_ = TODOS_OS_NOS[nome]
    return cls_(*[de_json(a) for a in args])
