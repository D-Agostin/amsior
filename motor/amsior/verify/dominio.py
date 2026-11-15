# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Domínio de definição e objetos opacos, calculados na árvore AmsiorExpr.

Obrigações de domínio
    Cada nó que só existe em parte dos reais gera uma obrigação: denominador
    diferente de zero, argumento de ln positivo, radicando de raiz par não
    negativo, base de potência não inteira positiva, cos ≠ 0 na tangente.
    Numa integral definida, as obrigações do integrando que dependem da
    variável de integração valem no intervalo inteiro (``ObrigacaoIntegral``).
    O cálculo é feito antes de converter para o SymPy, que cancela e avalia na
    construção e apagaria essas informações.

Objetos opacos
    O que o verificador não sabe calcular com segurança vira um símbolo
    opaco, o mesmo dos dois lados do passo:

    * derivada parcial com variáveis mantidas constantes, ``(∂H/∂T)_P``;
    * derivada de uma expressão com variável que não declara depender da
      variável de derivação (sem isso ``dU/dT`` valeria zero);
    * integral indefinida (a constante de integração é da fase 3A).

    Um passo que carrega o objeto sem mexer nele continua verificável; um
    passo que o "calcula" não confere, porque o objeto opaco não é igual a
    nenhuma expressão.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from amsior.expr.nos import (
    Cos, Deriv, Div, Expr, Integral, Ln, Log, Mul, Num, PDeriv, Pow, Root, Sqrt, Sub,
    Sym, Tan, Abs,
)
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.verify.arvore import chave, fracao_exata, livres, mapear, sem_dependencia

Predicado = Literal["nao_nulo", "positivo", "nao_negativo"]


@dataclass(frozen=True)
class Obrigacao:
    expr: Expr
    predicado: Predicado


@dataclass(frozen=True)
class ObrigacaoIntegral:
    """As obrigações ``internas`` valem para todo ``var`` entre os limites."""

    var: Sym
    inferior: Expr
    superior: Expr
    internas: tuple[Obrigacao, ...]
    origem: Integral


Exigido = Obrigacao | ObrigacaoIntegral


def _juntar(destino: list[Exigido], novas: list[Exigido]) -> None:
    for o in novas:
        if o not in destino:
            destino.append(o)


def obrigacoes(e: Expr) -> list[Exigido]:
    out: list[Exigido] = []
    _obrig(e, out)
    return out


def _obrig(e: Expr, out: list[Exigido]) -> None:  # noqa: C901 - um ramo por nó
    if isinstance(e, Integral) and e.inferior is not None and e.superior is not None:
        _obrig(e.inferior, out)
        _obrig(e.superior, out)
        internas = obrigacoes(e.f)
        presas: list[Obrigacao] = []
        for o in internas:
            if isinstance(o, ObrigacaoIntegral) or e.var.id in livres(o.expr):
                if isinstance(o, Obrigacao):
                    presas.append(o)
                else:  # integral dentro de integral: obrigação do intervalo interno
                    presas.extend(o.internas)
            else:
                _juntar(out, [o])
        if presas:
            _juntar(out, [ObrigacaoIntegral(e.var, e.inferior, e.superior, tuple(presas), e)])
        return
    for c in e.filhos():
        _obrig(c, out)
    novas: list[Exigido] = []
    if isinstance(e, Div):
        novas.append(Obrigacao(e.den, "nao_nulo"))
    elif isinstance(e, Ln):
        novas.append(Obrigacao(e.a, "positivo"))
    elif isinstance(e, Log):
        novas += [Obrigacao(e.a, "positivo"), Obrigacao(e.base, "positivo"),
                  Obrigacao(Sub(e.base, Num("1")), "nao_nulo")]
    elif isinstance(e, Sqrt):
        novas.append(Obrigacao(e.a, "nao_negativo"))
    elif isinstance(e, Root):
        k = fracao_exata(e.n)
        if k is not None and k.denominator == 1 and k != 0:
            if int(k) % 2 == 0:
                novas.append(Obrigacao(e.a, "nao_negativo"))
        else:
            novas += [Obrigacao(e.a, "positivo"), Obrigacao(e.n, "nao_nulo")]
    elif isinstance(e, Pow):
        k = fracao_exata(e.exp)
        if k is None:
            novas.append(Obrigacao(e.base, "positivo"))
        elif k.denominator == 1:
            if k <= 0:  # 0⁰ e 0⁻ⁿ não existem
                novas.append(Obrigacao(e.base, "nao_nulo"))
        elif k > 0:
            novas.append(Obrigacao(e.base, "nao_negativo"))
        else:
            novas.append(Obrigacao(e.base, "positivo"))
    elif isinstance(e, Tan):
        novas.append(Obrigacao(Cos(e.a), "nao_nulo"))
    _juntar(out, novas)


def sensiveis_a_sinal(e: Expr) -> list[Expr]:
    """Subexpressões cujo sinal escolhe o ramo: argumento de módulo e base de
    potência par dentro de raiz (``√(w²) = |w|``)."""
    out: list[Expr] = []

    def bases_pares(r: Expr) -> None:
        fatores = r.fatores if isinstance(r, Mul) else (r,)
        for f in fatores:
            if isinstance(f, Pow):
                k = fracao_exata(f.exp)
                if k is not None and k.denominator == 1 and int(k) % 2 == 0:
                    out.append(f.base)

    def visitar(n: Expr) -> None:
        if isinstance(n, Abs):
            out.append(n.a)
        elif isinstance(n, Sqrt):
            bases_pares(n.a)
        elif isinstance(n, Root | Pow):
            radicando = n.a if isinstance(n, Root) else n.base
            k = fracao_exata(n.n if isinstance(n, Root) else n.exp)
            if k is None or k.denominator != 1:
                bases_pares(radicando)
            elif isinstance(n, Root) and int(k) % 2 == 0:
                bases_pares(radicando)
        for c in n.filhos():
            visitar(c)

    visitar(e)
    return [s for i, s in enumerate(out) if s not in out[:i]]


# ---------------------------------------------------------------- opacos

TipoOpaco = Literal["parcial_mantida", "derivada_sem_dependencia", "primitiva"]


@dataclass(frozen=True)
class Opaco:
    chave: str
    tipo: TipoOpaco
    variavel: str
    simbolos: tuple[str, ...] = ()


@dataclass
class Opacificacao:
    expr: Expr
    opacos: dict[str, Opaco] = field(default_factory=dict)


def opacificar(e: Expr, tabela: TabelaDeSimbolos) -> Opacificacao:
    """Troca cada objeto que o verificador não calcula por um símbolo opaco.

    O símbolo opaco tem como id a forma LaTeX do objeto: é o mesmo nos dois
    lados do passo e aparece legível nas mensagens.
    """
    resultado = Opacificacao(e)
    resultado.expr = _opac(e, tabela, resultado.opacos)
    return resultado


def _opac(e: Expr, tabela: TabelaDeSimbolos, opacos: dict[str, Opaco]) -> Expr:
    if isinstance(e, PDeriv) and e.mantidas:
        k = chave(e)
        opacos[k] = Opaco(k, "parcial_mantida", e.var.id)
        return Sym(k)
    if isinstance(e, Integral) and e.inferior is None and e.superior is None:
        k = chave(e)
        opacos[k] = Opaco(k, "primitiva", e.var.id)
        return Sym(k)
    novo = mapear(e, lambda c: _opac(c, tabela, opacos))
    if isinstance(novo, Deriv | PDeriv):
        faltam = sem_dependencia(novo.f, novo.var.id, tabela)
        if faltam:
            k = chave(e)
            opacos[k] = Opaco(k, "derivada_sem_dependencia", novo.var.id, tuple(faltam))
            return Sym(k)
    return novo
