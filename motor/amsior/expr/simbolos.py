# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Símbolos e tabela de símbolos.

O ``id`` de um símbolo é a sua forma LaTeX canônica, a mesma que o impressor
emite. Assim ``T_{1}``, ``\\Delta H_{\\mathrm{vap}}`` e ``\\mathrm{Re}`` são ids.
As suposições (positivo, real...) vêm da grandeza no glossário e decidem, por
exemplo, se um passo mostra ``ln x`` ou ``ln |x|``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Literal

Papel = Literal["variavel", "parametro", "constante", "funcao"]
Suposicao = Literal["real", "positivo", "nao_negativo", "nao_nulo", "inteiro"]

SUPOSICOES_VALIDAS: frozenset[str] = frozenset(
    {"real", "positivo", "nao_negativo", "nao_nulo", "inteiro"}
)

_MATHRM_BASE = re.compile(r"^\\mathrm\{([A-Za-z]+)\}")
_LETRA_BASE = re.compile(r"^([A-Za-z])")


@dataclass(frozen=True)
class Simbolo:
    id: str
    grandeza: str | None = None
    papel: Papel = "variavel"
    suposicoes: frozenset[str] = frozenset({"real"})
    depende_de: tuple[str, ...] = ()
    nome: str | None = None

    def __post_init__(self) -> None:
        invalidas = set(self.suposicoes) - SUPOSICOES_VALIDAS
        if invalidas:
            raise ValueError(f"suposições inválidas para {self.id}: {sorted(invalidas)}")

    @property
    def latex(self) -> str:
        return self.id

    def palavra_base(self) -> str | None:
        """Letras da base quando ela é uma palavra comum (``R``, ``Re``)."""
        m = _MATHRM_BASE.match(self.id)
        if m:
            return m.group(1)
        m = _LETRA_BASE.match(self.id)
        if m:
            return m.group(1)
        return None


@dataclass
class TabelaDeSimbolos:
    """Símbolos conhecidos numa folha ou ficha."""

    _simbolos: dict[str, Simbolo] = field(default_factory=dict)

    @classmethod
    def de(cls, simbolos: Iterable[Simbolo]) -> TabelaDeSimbolos:
        t = cls()
        for s in simbolos:
            t.adicionar(s)
        return t

    def adicionar(self, s: Simbolo) -> None:
        self._simbolos[s.id] = s

    def obter(self, id_: str) -> Simbolo | None:
        return self._simbolos.get(id_)

    def __contains__(self, id_: object) -> bool:
        return id_ in self._simbolos

    def __iter__(self) -> Iterator[Simbolo]:
        return iter(self._simbolos.values())

    def __len__(self) -> int:
        return len(self._simbolos)

    def suposicoes(self, id_: str) -> frozenset[str]:
        s = self._simbolos.get(id_)
        return s.suposicoes if s else frozenset({"real"})

    def eh_funcao(self, id_: str) -> bool:
        s = self._simbolos.get(id_)
        return bool(s and s.papel == "funcao")

    def palavras_conhecidas(self) -> set[str]:
        """Bases em letras comuns presentes na tabela (``R``, ``T``, ``Re``)."""
        resultado: set[str] = set()
        for s in self._simbolos.values():
            p = s.palavra_base()
            if p:
                resultado.add(p)
        return resultado
