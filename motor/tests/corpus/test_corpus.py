# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Critério de aceite da fase 1A: ida e volta LaTeX → árvore → LaTeX estável em 200 expressões."""

from __future__ import annotations

import pytest

from amsior.erros import ErroDeAnalise
from amsior.expr import analisar, de_json, para_json, para_latex, para_sympy
from tests.conftest import tabela_corpus
from tests.corpus.corpus_latex import CORPUS, RECUSADAS


def test_corpus_tem_ao_menos_200_expressoes() -> None:
    assert len(CORPUS) >= 200
    assert len({s for s, _ in CORPUS}) == len(CORPUS), "entradas repetidas"


@pytest.mark.parametrize(("latex", "funcoes"), CORPUS, ids=[s for s, _ in CORPUS])
def test_ida_e_volta(latex: str, funcoes: tuple[str, ...]) -> None:
    tab = tabela_corpus(funcoes)
    arvore = analisar(latex, tab)
    canonico = para_latex(arvore)
    assert analisar(canonico, tab) == arvore
    assert para_latex(analisar(canonico, tab)) == canonico
    # também em inglês (ponto decimal)
    en = para_latex(arvore, "en")
    assert analisar(en, tab) == arvore
    # JSON e SymPy
    assert de_json(para_json(arvore)) == arvore
    para_sympy(arvore, tab)


@pytest.mark.parametrize("latex", RECUSADAS)
def test_construcoes_fora_da_v1_sao_recusadas_com_mensagem(latex: str) -> None:
    with pytest.raises(ErroDeAnalise) as info:
        analisar(latex, tabela_corpus())
    assert info.value.mensagem()
