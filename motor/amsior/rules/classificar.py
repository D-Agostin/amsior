# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Tipo da equação em relação a uma variável (D-12).

Segue a classificação usual do ensino: expressões algébricas **racionais
inteiras** (polinômios, com grau), **racionais fracionárias** (a variável no
denominador) e **irracionais** (a variável sob radical ou com expoente
fracionário); além delas, as **transcendentes**: exponencial, logarítmica,
trigonométrica. Quando a variável aparece ao mesmo tempo de forma algébrica e
dentro de uma função transcendente (``x + ln x``, o LMTD em ΔT₂), a equação é
**mista** e em geral não tem forma fechada elementar.

A classificação é só informativa: cada tipo aponta para a ficha da seção de
Matemática que o explica. Ela não muda nenhum passo nem nenhuma verificação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import sympy as sp

from amsior.expr.nos import (
    Abs, Cos, Div, Eq, Exp, Expr, Ln, Log, Pow, Root, Sin, Sqrt, Sym, Tan,
)
from amsior.expr.ponte_sympy import ParaSympy
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.verify.arvore import fracao_exata, livres

Classe = Literal["polinomial", "racional", "irracional", "transcendente", "mista"]
Familia = Literal["exponencial", "logaritmica", "trigonometrica", "modulo"]
_TRANSCENDENTES = frozenset({"exponencial", "logaritmica", "trigonometrica", "modulo"})


# todas as chaves possíveis (são também os ids das fichas de Matemática que explicam cada tipo)
CHAVES: tuple[str, ...] = (
    "tipo.polinomial_1", "tipo.polinomial_2", "tipo.polinomial_3", "tipo.polinomial",
    "tipo.racional", "tipo.irracional", "tipo.exponencial", "tipo.logaritmica",
    "tipo.trigonometrica", "tipo.modulo", "tipo.transcendente", "tipo.mista",
)


@dataclass(frozen=True)
class Classificacao:
    alvo: str
    classe: Classe
    grau: int | None = None  # polinomial: grau; racional: grau depois de tirar os denominadores
    familias: tuple[Familia, ...] = field(default_factory=tuple)

    @property
    def chave(self) -> str:
        """Chave do catálogo de textos e id da ficha de Matemática que explica o tipo."""
        if self.classe == "polinomial" and self.grau in (1, 2, 3):
            return f"tipo.polinomial_{self.grau}"
        if self.classe == "transcendente" and len(self.familias) == 1:
            return f"tipo.{self.familias[0]}"
        return f"tipo.{self.classe}"

    def args(self) -> dict[str, str]:
        return {"alvo": self.alvo, "grau": "" if self.grau is None else str(self.grau)}


def _contexto(e: Expr, alvo: str, achados: dict[str, bool], dentro: tuple[str, ...] = ()) -> None:
    """Percorre a árvore anotando em que tipo de lugar o alvo aparece."""
    if isinstance(e, Sym):
        if e.id == alvo:
            transc = [d for d in dentro if d in _TRANSCENDENTES]
            if transc:  # dentro de exp, ln ou trigonométrica só conta a família
                for d in transc:
                    achados[d] = True
            elif not dentro:
                achados["algebrico"] = True
            else:
                for d in dentro:
                    achados[d] = True
        return
    if alvo not in livres(e):
        return
    if isinstance(e, Exp):
        _contexto(e.a, alvo, achados, (*dentro, "exponencial"))
        return
    if isinstance(e, Ln | Log):
        for c in e.filhos():
            _contexto(c, alvo, achados, (*dentro, "logaritmica"))
        return
    if isinstance(e, Sin | Cos | Tan):
        _contexto(e.a, alvo, achados, (*dentro, "trigonometrica"))
        return
    if isinstance(e, Abs):
        _contexto(e.a, alvo, achados, (*dentro, "modulo"))
        return
    if isinstance(e, Pow):
        if alvo in livres(e.exp):
            _contexto(e.exp, alvo, achados, (*dentro, "exponencial"))
        k = fracao_exata(e.exp)
        marca = () if k is not None and k.denominator == 1 and k >= 0 else \
            ("denominador",) if k is not None and k.denominator == 1 else ("radical",)
        _contexto(e.base, alvo, achados, (*dentro, *marca))
        return
    if isinstance(e, Sqrt | Root):
        _contexto(e.filhos()[0], alvo, achados, (*dentro, "radical"))
        return
    if isinstance(e, Div):
        _contexto(e.num, alvo, achados, dentro)
        _contexto(e.den, alvo, achados, (*dentro, "denominador"))
        return
    for c in e.filhos():
        _contexto(c, alvo, achados, dentro)


def classificar(eq: Expr, alvo: str, tabela: TabelaDeSimbolos) -> Classificacao | None:
    """Tipo de ``eq`` como equação em ``alvo``; None se o alvo não aparece."""
    if not isinstance(eq, Eq) or alvo not in livres(eq):
        return None
    achados: dict[str, bool] = {}
    _contexto(eq.esq, alvo, achados)
    _contexto(eq.dir, alvo, achados)
    familias: tuple[Familia, ...] = tuple(
        f for f in ("exponencial", "logaritmica", "trigonometrica", "modulo") if achados.get(f))
    algebrico = achados.get("algebrico") or achados.get("denominador") or achados.get("radical")
    if familias:
        transc = [f for f in familias if f != "modulo"]
        if transc and algebrico:
            return Classificacao(alvo, "mista", None, familias)
        return Classificacao(alvo, "transcendente", None, familias)
    if achados.get("radical"):
        return Classificacao(alvo, "irracional")
    conv = ParaSympy(tabela)
    u = conv.valor_simbolo(alvo)
    try:
        num, den = sp.fraction(sp.together(conv(eq.esq) - conv(eq.dir)))
        grau = int(sp.Poly(sp.expand(num, log=False), u).degree())
    except Exception:
        grau = None
    if achados.get("denominador") and grau is not None:
        try:
            if sp.Poly(den, u).degree() > 0:
                return Classificacao(alvo, "racional", grau)
        except Exception:
            pass
    return Classificacao(alvo, "polinomial", grau)
