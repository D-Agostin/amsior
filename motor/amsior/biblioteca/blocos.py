# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Blocos de conteúdo das fichas de conceito (seção 3.5 e padrão de redação da 8.6).

Uma seção de ficha é uma lista de blocos, cada um com um papel só:

``texto``     parágrafo; matemática em linha só para símbolos e expressões curtas
``equacao``   equação em linha própria, numerada; ``destaque`` põe em caixa o
              resultado central; ``onde`` explica cada símbolo logo abaixo;
              ``nota`` é uma observação curta sob a equação
``lista``     itens curtos
``caixa``     blocos dentro de uma caixa com título: ``resumo`` (a resposta em
              poucas linhas), ``destaque`` (a ideia central), ``atencao`` (a
              pegadinha, o erro comum), ``hipoteses`` (premissas adotadas)
``passos``    dedução em passos com título; cada passo é uma lista de blocos
``tabela``    colunas e linhas de texto curto
``figura``    SVG da pasta de figuras, com legenda

A regra que motivou o formato: **nenhuma equação no texto corrido**. Relação
(=, <, ≤, ≈, ⇒...) dentro de ``\\( \\)`` num texto é erro de esquema; ela vai
para um bloco ``equacao``. Isso vale também para resumo, enunciados, itens de
lista e células de tabela.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

#: tipos de caixa e o que cada um significa (o título padrão vem do catálogo de textos)
CAIXAS = ("resumo", "destaque", "atencao", "hipoteses")
_TIPOS = ("texto", "equacao", "lista", "caixa", "passos", "tabela", "figura")

_INLINE = re.compile(r"\\\((.+?)\\\)", re.S)
_RELACAO = re.compile(r"(?<!\\)[=<>]|\\(?:leq?|geq?|neq?|ne|approx|equiv|sim|propto|Rightarrow|"
                      r"Leftarrow|Leftrightarrow|iff|implies|to|lt|gt|leqslant|geqslant)(?![A-Za-z])")


def relacoes_em_linha(texto: str) -> list[str]:
    """Trechos ``\\( \\)`` de um texto que contêm uma relação (são equações, não símbolos)."""
    return [m.group(1).strip() for m in _INLINE.finditer(texto) if _RELACAO.search(m.group(1))]


Erro = Callable[[str, str], None]


def validar_blocos(blocos: Any, campo: str, erro: Erro, raiz: Path | None,
                   profundidade: int = 0) -> int:
    """Valida uma lista de blocos; devolve quantas equações ela tem (para numerar)."""
    if not isinstance(blocos, list):
        erro(campo, "esperada uma lista de blocos")
        return 0
    if not blocos:
        erro(campo, "lista de blocos vazia")
    n_eq = 0
    for i, bl in enumerate(blocos):
        c = f"{campo}[{i}]"
        if not isinstance(bl, dict):
            erro(c, "esperado um bloco {tipo: ...}")
            continue
        tipos = [t for t in _TIPOS if t in bl]
        if len(tipos) != 1:
            erro(c, f"um bloco tem exatamente um destes campos: {list(_TIPOS)}")
            continue
        tipo = tipos[0]
        extras = set(bl) - {tipo} - _EXTRAS[tipo]
        for k in sorted(extras):
            erro(c, f"campo desconhecido em bloco {tipo}: {k}")
        if tipo == "texto":
            _texto(bl["texto"], f"{c}.texto", erro)
        elif tipo == "equacao":
            n_eq += 1
            if not isinstance(bl["equacao"], str) or not bl["equacao"].strip():
                erro(f"{c}.equacao", "LaTeX da equação")
            if "destaque" in bl and not isinstance(bl["destaque"], bool):
                erro(f"{c}.destaque", "verdadeiro ou falso")
            if "nota" in bl:
                _texto(bl["nota"], f"{c}.nota", erro)
            onde = bl.get("onde")
            if onde is not None:
                if not isinstance(onde, list) or not onde:
                    erro(f"{c}.onde", "lista de {simbolo, texto}")
                else:
                    for k, o in enumerate(onde):
                        if not isinstance(o, dict) or set(o) != {"simbolo", "texto"} \
                                or not isinstance(o["simbolo"], str):
                            erro(f"{c}.onde[{k}]", "esperado {simbolo: LaTeX, texto: {pt}}")
                        else:
                            _texto(o["texto"], f"{c}.onde[{k}].texto", erro)
        elif tipo == "lista":
            itens = bl["lista"]
            if not isinstance(itens, list) or not itens:
                erro(f"{c}.lista", "lista de itens {pt: ...}")
            else:
                for k, it in enumerate(itens):
                    _texto(it, f"{c}.lista[{k}]", erro)
        elif tipo == "caixa":
            if bl["caixa"] not in CAIXAS:
                erro(f"{c}.caixa", f"tipo de caixa fora de {list(CAIXAS)}")
            if "titulo" in bl:
                _texto(bl["titulo"], f"{c}.titulo", erro)
            if profundidade > 0:
                erro(c, "caixa dentro de caixa ou de passo: deixe a caixa no nível da seção")
            n_eq += validar_blocos(bl.get("blocos"), f"{c}.blocos", erro, raiz, profundidade + 1)
        elif tipo == "passos":
            passos = bl["passos"]
            if profundidade > 0:
                erro(c, "passos dentro de caixa ou de passo")
            if not isinstance(passos, list) or len(passos) < 2:
                erro(f"{c}.passos", "pelo menos dois passos, cada um {titulo, blocos}")
            else:
                for k, p in enumerate(passos):
                    pc = f"{c}.passos[{k}]"
                    if not isinstance(p, dict) or set(p) != {"titulo", "blocos"}:
                        erro(pc, "esperado {titulo: {pt}, blocos: [...]}")
                        continue
                    _texto(p["titulo"], f"{pc}.titulo", erro)
                    n_eq += validar_blocos(p["blocos"], f"{pc}.blocos", erro, raiz, profundidade + 1)
        elif tipo == "tabela":
            t = bl["tabela"]
            if not isinstance(t, dict) or set(t) != {"colunas", "linhas"}:
                erro(f"{c}.tabela", "esperado {colunas: [...], linhas: [[...], ...]}")
                continue
            cols = t["colunas"]
            if not isinstance(cols, list) or not cols:
                erro(f"{c}.tabela.colunas", "lista de títulos {pt}")
                continue
            for k, col in enumerate(cols):
                _texto(col, f"{c}.tabela.colunas[{k}]", erro)
            linhas = t["linhas"]
            if not isinstance(linhas, list) or not linhas:
                erro(f"{c}.tabela.linhas", "pelo menos uma linha")
                continue
            for k, ln in enumerate(linhas):
                if not isinstance(ln, list) or len(ln) != len(cols):
                    erro(f"{c}.tabela.linhas[{k}]", f"esperadas {len(cols)} células")
                    continue
                for j, cel in enumerate(ln):
                    _texto(cel, f"{c}.tabela.linhas[{k}][{j}]", erro)
        elif tipo == "figura":
            fig = bl["figura"]
            if not isinstance(fig, str) or not fig.endswith(".svg"):
                erro(f"{c}.figura", "caminho de um .svg da pasta de figuras")
            elif raiz is not None and not (raiz / "figuras" / fig).is_file():
                erro(f"{c}.figura", f"figura ausente: figuras/{fig}")
            if "legenda" in bl:
                _texto(bl["legenda"], f"{c}.legenda", erro)
    return n_eq


_EXTRAS: dict[str, set[str]] = {
    "texto": set(),
    "equacao": {"destaque", "onde", "nota"},
    "lista": set(),
    "caixa": {"titulo", "blocos"},
    "passos": set(),
    "tabela": set(),
    "figura": {"legenda"},
}


def _texto(v: Any, campo: str, erro: Erro) -> None:
    if not isinstance(v, dict) or not isinstance(v.get("pt"), str) or not v["pt"].strip():
        erro(campo, "esperado {pt: \"...\"} não vazio")
        return
    for idioma, t in v.items():
        if idioma not in ("pt", "en"):
            erro(campo, f"idioma desconhecido: {idioma}")
        elif isinstance(t, str):
            verificar_texto_corrido(t, f"{campo}.{idioma}", erro)


def verificar_texto_corrido(texto: str, campo: str, erro: Erro) -> None:
    for trecho in relacoes_em_linha(texto):
        erro(campo, f"equação no texto corrido: \\({trecho}\\); use um bloco equacao")


def textos(blocos: Any) -> Iterator[str]:
    """Todos os textos em português de uma lista de blocos (para busca e revisão)."""
    for bl in blocos if isinstance(blocos, list) else ():
        if not isinstance(bl, dict):
            continue
        for k in ("texto", "nota", "titulo", "legenda"):
            v = bl.get(k)
            if isinstance(v, dict) and isinstance(v.get("pt"), str):
                yield v["pt"]
        for it in bl.get("lista") or ():
            if isinstance(it, dict) and isinstance(it.get("pt"), str):
                yield it["pt"]
        yield from textos(bl.get("blocos"))
        for p in bl.get("passos") or ():
            if isinstance(p, dict):
                yield from textos(p.get("blocos"))
