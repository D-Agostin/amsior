# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Teste de identidade entre duas expressões (seção 5.1).

Duas vias independentes, que rodam sempre:

1. **Simbólica** (SymPy): a diferença simplifica a zero sob as suposições,
   só com transformações que provam (``sympy.equals`` decide por amostragem e
   não é usado). Uma diferença que simplifica a uma constante não nula é
   refutação imediata.
2. **Numérica** (avaliador próprio, ``amostragem.py``): não passa pelo SymPy.

Decisão:

* simbólica prova e a numérica não acha divergência → ``simbolico``;
* simbólica prova e a numérica acha divergência → reprova
  (``contraprova_divergente``: indica erro de conversão, como a variável
  mantida constante perdida no SymPy);
* simbólica não conclui → vale a numérica, com selo ``numerico``.

Com condições declaradas, a via simbólica é pulada: ela só conhece as
suposições dos símbolos, e a identidade depende das condições.

Antes de tudo, os objetos que o verificador não calcula (``dominio.opacificar``)
viram símbolos opacos dos dois lados.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import sympy as sp

from amsior.expr.nos import Expr
from amsior.expr.ponte_sympy import ParaSympy
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.verify.amostragem import ResultadoNumerico, comparar_numerico
from amsior.verify.avaliador import Avaliador
from amsior.verify.dominio import Opaco, opacificar


@dataclass
class ResultadoIdentidade:
    aprovado: bool
    metodo: Literal["simbolico", "numerico", "estrutural"] | None
    motivo: str = ""
    residuo: float | None = None
    numerico: ResultadoNumerico | None = None
    opacos: dict[str, Opaco] = field(default_factory=dict)
    faltam: list[Any] = field(default_factory=list)  # V2: condições que a solução precisaria


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


def identidade_simbolica(a: Any, b: Any) -> Literal["prova", "refuta"] | None:
    """'prova' se a − b ≡ 0; 'refuta' se a − b é uma constante não nula."""
    try:
        dif = sp.sympify(a - b).doit()
    except Exception:
        return None
    for f in _TRANSFORMACOES:
        try:
            d = f(dif)
        except Exception:
            continue
        if _eh_zero(d):
            return "prova"
        try:
            if d.is_number and not d.free_symbols and abs(sp.N(d, 80)) > sp.Float("1e-60", 80):
                return "refuta"
        except Exception:
            continue
    return None


@dataclass
class Comparador:
    """Compara expressões AmsiorExpr de um passo com uma tabela e um avaliador fixos."""

    tabela: TabelaDeSimbolos
    semente: int = 0
    avaliador: Avaliador = field(init=False)
    conv: ParaSympy = field(init=False)

    def __post_init__(self) -> None:
        self.avaliador = Avaliador(self.tabela, self.semente)
        self.conv = ParaSympy(self.tabela)

    def comparar(self, esperado: Expr, obtido: Expr,
                 condicoes: Sequence[Expr] = ()) -> ResultadoIdentidade:
        if esperado == obtido:
            return ResultadoIdentidade(True, "estrutural")
        oe, oo = opacificar(esperado, self.tabela), opacificar(obtido, self.tabela)
        opacos = {**oe.opacos, **oo.opacos}
        simb = None
        if not condicoes:
            try:
                simb = identidade_simbolica(self.conv(oe.expr), self.conv(oo.expr))
            except Exception:
                simb = None
        if simb == "refuta":
            return ResultadoIdentidade(False, None, "verif.identidade.diferenca_constante",
                                       opacos=opacos)
        num = comparar_numerico(oe.expr, oo.expr, self.tabela, self.avaliador, list(condicoes),
                                originais=(esperado, obtido))
        if simb == "prova":
            if not num.aprovado and num.motivo in ("verif.identidade.residuo",
                                                   "verif.identidade.dominio_inconsistente"):
                return ResultadoIdentidade(False, None, "verif.identidade.contraprova_divergente",
                                           num.pior_residuo, num, opacos)
            return ResultadoIdentidade(True, "simbolico", residuo=num.pior_residuo,
                                       numerico=num, opacos=opacos)
        if num.aprovado:
            return ResultadoIdentidade(True, "numerico", residuo=num.pior_residuo, numerico=num,
                                       opacos=opacos)
        return ResultadoIdentidade(False, None, num.motivo, num.pior_residuo, num, opacos)


def identicas(a: Expr, b: Expr, tabela: TabelaDeSimbolos,
              condicoes: Sequence[Expr] = ()) -> ResultadoIdentidade:
    """Atalho: identidade entre duas AmsiorExpr."""
    return Comparador(tabela).comparar(a, b, condicoes)
