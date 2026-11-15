# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Erros do Amsior. Cada erro carrega uma chave de tradução e seus argumentos."""

from __future__ import annotations

from amsior.i18n import IDIOMA_PADRAO, t


class ErroAmsior(Exception):
    def __init__(self, chave: str, **args: object) -> None:
        self.chave = chave
        self.args_msg = args
        super().__init__(chave, args)

    def mensagem(self, idioma: str = IDIOMA_PADRAO) -> str:
        return t(self.chave, idioma, **self.args_msg)

    def __str__(self) -> str:
        try:
            return self.mensagem()
        except Exception:  # pragma: no cover - só se o catálogo estiver quebrado
            return f"{self.chave} {self.args_msg}"


class ErroDeAnalise(ErroAmsior):
    """Entrada LaTeX que o analisador não aceita."""

    def __init__(self, chave: str, posicao: int, **args: object) -> None:
        super().__init__(chave, posicao=posicao, **args)
        self.posicao = posicao


class AmbiguidadeDeSimbolo(ErroDeAnalise):
    """Sequência de letras que pode ser um símbolo só ou um produto."""

    def __init__(self, posicao: int, palavra: str, opcoes: list[str]) -> None:
        super().__init__(
            "erro.analise.palavra_ambigua", posicao, palavra=palavra,
            opcoes=" | ".join(opcoes),
        )
        self.palavra = palavra
        self.opcoes = opcoes


class ErroDimensional(ErroAmsior):
    """Expressão dimensionalmente inconsistente."""


class ErroDeUnidade(ErroAmsior):
    """Unidade desconhecida ou incompatível com a grandeza."""
