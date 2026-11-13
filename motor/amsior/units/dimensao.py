# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Dimensões físicas e análise dimensional simbólica.

A dimensão de um símbolo vem da sua grandeza no glossário, não do valor
digitado. Assim a homogeneidade é conferida antes de existir qualquer número.
Expoentes podem ser simbólicos: em ``P V^{n}`` a dimensão de ``V^{n}`` é
``m^{3n}``, e ``P_1 V_1^{n} = P_2 V_2^{n}`` continua homogênea.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache
from typing import Any

import pint
import sympy as sp

BASES = ("[mass]", "[length]", "[time]", "[temperature]", "[substance]", "[current]",
         "[luminosity]")
_SI = {"[mass]": "kg", "[length]": "m", "[time]": "s", "[temperature]": "K",
       "[substance]": "mol", "[current]": "A", "[luminosity]": "cd"}
_SOBRESCRITO = str.maketrans("-0123456789/", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹ᐟ")


@cache
def registro() -> pint.UnitRegistry:
    """Registro único de unidades do Amsior."""
    return pint.UnitRegistry()


@dataclass(frozen=True)
class Dim:
    """Dimensão como expoentes (expressões SymPy) das grandezas de base do SI."""

    expoentes: tuple[tuple[str, Any], ...] = field(default=())

    @staticmethod
    def de(mapa: Mapping[str, Any]) -> Dim:
        itens = []
        for base in BASES:
            v = sp.nsimplify(mapa.get(base, 0))
            if v != 0:
                itens.append((base, v))
        return Dim(tuple(itens))

    def mapa(self) -> dict[str, Any]:
        return dict(self.expoentes)

    def __mul__(self, outra: Dim) -> Dim:
        m = self.mapa()
        for b, v in outra.expoentes:
            m[b] = sp.simplify(m.get(b, 0) + v)
        return Dim.de(m)

    def __truediv__(self, outra: Dim) -> Dim:
        return self * outra ** -1

    def __pow__(self, k: Any) -> Dim:
        return Dim.de({b: sp.simplify(v * k) for b, v in self.expoentes})

    def igual(self, outra: Dim) -> bool:
        a, b = self.mapa(), outra.mapa()
        return all(sp.simplify(a.get(x, 0) - b.get(x, 0)) == 0 for x in BASES)

    def __eq__(self, outra: object) -> bool:
        return isinstance(outra, Dim) and self.igual(outra)

    def __hash__(self) -> int:
        return hash(self.expoentes)

    def adimensional(self) -> bool:
        return all(sp.simplify(v) == 0 for _, v in self.expoentes)

    def texto(self) -> str:
        """Dimensão em unidades de base do SI, como ``kg·m⁻¹·s⁻²``."""
        if self.adimensional():
            return "1"
        partes = []
        for b, v in self.expoentes:
            if v == 1:
                partes.append(_SI[b])
            elif v.is_Rational:
                partes.append(_SI[b] + str(v).translate(_SOBRESCRITO))
            else:
                partes.append(f"{_SI[b]}^({v})")
        return "·".join(partes)


UM = Dim()


def dimensao_de_unidade(unidade: str) -> Dim:
    if unidade.strip() in ("1", "", "dimensionless"):
        return UM
    dim = registro()(unidade).dimensionality
    return Dim.de({str(k): v for k, v in dim.items()})
