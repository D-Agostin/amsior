# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Critério de aceite da fase 1B: toda variável do corpus isola com passos ou é recusada
corretamente, e nenhum passo sai sem certificado aprovado."""

from __future__ import annotations

import pytest

from amsior.expr import Sym, analisar
from amsior.units import Glossario
from amsior.steps import isolar
from amsior.verify.arvore import livres
from tests.corpus.corpus_isolar import CORPUS, EqCorpus, tabela

CASOS = [(e, s) for e in CORPUS for s in e.simbolos
         if not e.simbolos[s].endswith(":constante")]


@pytest.mark.parametrize(("eq", "alvo"), CASOS, ids=[f"{e.nome} → {s}" for e, s in CASOS])
def test_isolar_corpus(eq: EqCorpus, alvo: str, glossario: Glossario) -> None:
    tab = tabela(eq, glossario)
    r = isolar(analisar(eq.latex, tab), Sym(alvo), tab, glossario)
    esperado = eq.esperado.get(alvo, "passos")
    if esperado == "passos":
        assert r.estado == "com_passos", (r.motivo, r.rejeitados)
        for ramo in r.ramos:
            assert ramo.resultado.esq == Sym(alvo)
            assert alvo not in livres(ramo.resultado.dir)
            assert all(p.certificado is not None and p.certificado.estado == "aprovado"
                       for p in ramo.passos)
            assert ramo.cadeia.estado == "aprovado"
    else:
        assert r.estado in ("sem_passos", "recusado")
        assert not r.ramos  # nenhum passo é exibido


def test_corpus_tem_60_equacoes() -> None:
    assert len(CORPUS) >= 60
