# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Biblioteca de fichas (seção 8 da especificação).

``carregar_biblioteca`` lê o registro de fontes, o vocabulário de hipóteses e as
fichas de equação e de conceito da pasta ``biblioteca/``; ``validar`` devolve a
lista de problemas de esquema e de ligação entre arquivos. A verificação
matemática das fichas (V1 a V6) usa o mesmo motor da folha e vem por cima disso.
"""

from amsior.biblioteca.esquema import (
    ESTADOS,
    Biblioteca,
    Ficha,
    Fonte,
    Hipotese,
    Problema,
    carregar_biblioteca,
    validar,
)

__all__ = [
    "ESTADOS",
    "Biblioteca",
    "Ficha",
    "Fonte",
    "Hipotese",
    "Problema",
    "carregar_biblioteca",
    "validar",
]
