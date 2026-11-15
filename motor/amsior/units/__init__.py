# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Grandezas, dimensões, homogeneidade dimensional e conversão de unidades."""

from amsior.units.conversao import de_si, para_si, pressao_absoluta
from amsior.units.dimensao import UM, Dim, dimensao_de_unidade, registro
from amsior.units.glossario import Glossario, Grandeza, carregar_glossario
from amsior.units.homogeneidade import (
    AnalisadorDimensional, ResultadoDimensional, verificar_homogeneidade,
)

__all__ = [
    "UM", "AnalisadorDimensional", "Dim", "Glossario", "Grandeza", "ResultadoDimensional",
    "carregar_glossario", "de_si", "dimensao_de_unidade", "para_si", "pressao_absoluta",
    "registro", "verificar_homogeneidade",
]
