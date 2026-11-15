# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Glossário de grandezas (biblioteca/_glossario.yaml).

No navegador (Pyodide, sem PyYAML) o motor lê a cópia em JSON, ``_glossario.json``,
gerada a partir do YAML na montagem da versão web (ferramentas/web/montar_motor.py).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from amsior.expr.simbolos import Papel, Simbolo
from amsior.units.dimensao import Dim, dimensao_de_unidade

_RAIZ_REPO = Path(__file__).resolve().parents[3]


def pasta_biblioteca() -> Path:
    """Pasta da biblioteca: variável AMSIOR_BIBLIOTECA, pacote congelado ou ``<repo>/biblioteca``."""
    if "AMSIOR_BIBLIOTECA" in os.environ:
        return Path(os.environ["AMSIOR_BIBLIOTECA"])
    congelado = getattr(sys, "_MEIPASS", None)
    if congelado:
        return Path(congelado) / "biblioteca"
    return _RAIZ_REPO / "biblioteca"


@dataclass(frozen=True)
class Grandeza:
    id: str
    nome: str
    unidade_si: str
    suposicoes: frozenset[str]
    dimensao: Dim
    temperatura: str | None = None
    pressao: str | None = None
    exibicao: tuple[str, ...] = ()


class Glossario:
    def __init__(self, grandezas: dict[str, Grandeza]) -> None:
        self._g = grandezas

    def __getitem__(self, id_: str) -> Grandeza:
        return self._g[id_]

    def __contains__(self, id_: object) -> bool:
        return id_ in self._g

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._g.values())

    def __len__(self) -> int:
        return len(self._g)

    def simbolo(
        self,
        id_: str,
        grandeza: str,
        papel: Papel = "variavel",
        depende_de: tuple[str, ...] = (),
        nome: str | None = None,
    ) -> Simbolo:
        """Cria um símbolo com as suposições herdadas da grandeza."""
        g = self._g[grandeza]
        return Simbolo(id_, grandeza, papel, g.suposicoes, depende_de, nome)

    @classmethod
    def de_dados(cls, dados: dict[str, Any]) -> Glossario:
        if dados.get("formato") != 1:
            raise ValueError("formato de glossário desconhecido")
        grandezas: dict[str, Grandeza] = {}
        for gid, g in dados["grandezas"].items():
            grandezas[gid] = Grandeza(
                id=gid,
                nome=str(g["nome"]),
                unidade_si=str(g["unidade_si"]),
                suposicoes=frozenset(g.get("suposicoes", ["real"])),
                dimensao=dimensao_de_unidade(str(g["unidade_si"])),
                temperatura=g.get("temperatura"),
                pressao=g.get("pressao"),
                exibicao=tuple(g.get("exibicao", ())),
            )
        return cls(grandezas)


def ler_dados(arquivo: Path) -> Any:
    """YAML ou JSON, pela extensão. O PyYAML só é importado quando é preciso."""
    texto = arquivo.read_text(encoding="utf-8")
    if arquivo.suffix == ".json":
        return json.loads(texto)
    import yaml

    return yaml.safe_load(texto)


@cache
def carregar_glossario(caminho: str | None = None) -> Glossario:
    if caminho:
        arquivo = Path(caminho)
    else:
        pasta = pasta_biblioteca()
        arquivo = pasta / "_glossario.yaml"
        if not arquivo.exists() and (pasta / "_glossario.json").exists():
            arquivo = pasta / "_glossario.json"
    return Glossario.de_dados(ler_dados(arquivo))
