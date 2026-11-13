# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Critério de aceite da fase 1A: o verificador reprova 100% dos passos errados e aprova 100% dos certos."""

from __future__ import annotations

import pytest

from amsior.expr import Sym, TabelaDeSimbolos, analisar
from amsior.units import Glossario
from amsior.verify import Condicao, Operacao, Passo, certificar
from tests.corpus.passos_ataque import CERTOS, ERRADOS, PENDENTES, Caso, tabelas


@pytest.fixture(scope="module")
def tabs(glossario: Glossario) -> dict[str, TabelaDeSimbolos]:
    return tabelas(glossario)


def montar(c: Caso, tab: TabelaDeSimbolos) -> Passo:
    A = lambda s: analisar(s, tab)  # noqa: E731
    simbolo = A(c.simbolo) if c.simbolo else None
    assert simbolo is None or isinstance(simbolo, Sym)
    return Passo(
        antes=A(c.antes), depois=A(c.depois),
        operacao=Operacao(c.op, A(c.arg) if c.arg else None, c.lado, simbolo, c.origem),  # type: ignore[arg-type]
        relacao=c.relacao,  # type: ignore[arg-type]
        tipo=c.tipo,  # type: ignore[arg-type]
        condicoes=tuple(Condicao(A(x), c.origem_condicao) for x in c.condicoes),  # type: ignore[arg-type]
    )


def _ids(casos: list[Caso]) -> list[str]:
    return [c.nome for c in casos]


@pytest.mark.parametrize("caso", CERTOS, ids=_ids(CERTOS))
def test_passos_certos_sao_aprovados(caso: Caso, tabs: dict[str, TabelaDeSimbolos],
                                     glossario: Glossario) -> None:
    cert = certificar(montar(caso, tabs[caso.tabela]), tabs[caso.tabela], glossario)
    assert cert.estado == "aprovado", [m.texto() for m in cert.motivos]


@pytest.mark.parametrize("caso", ERRADOS, ids=_ids(ERRADOS))
def test_passos_errados_sao_reprovados_pelo_motivo_certo(
        caso: Caso, tabs: dict[str, TabelaDeSimbolos], glossario: Glossario) -> None:
    cert = certificar(montar(caso, tabs[caso.tabela]), tabs[caso.tabela], glossario)
    assert cert.estado == "reprovado"
    chaves = [m.chave for m in cert.motivos]
    assert caso.motivo in chaves, [m.texto() for m in cert.motivos]
    for m in cert.motivos:
        assert m.texto()  # toda mensagem existe no catálogo


@pytest.mark.parametrize("caso", PENDENTES, ids=_ids(PENDENTES))
def test_passos_de_principio_ficam_pendentes(caso: Caso, tabs: dict[str, TabelaDeSimbolos],
                                             glossario: Glossario) -> None:
    cert = certificar(montar(caso, tabs[caso.tabela]), tabs[caso.tabela], glossario)
    assert cert.estado == "pendente"
    assert cert.metodo == "revisao_humana"


def test_resumo_da_suite(tabs: dict[str, TabelaDeSimbolos], glossario: Glossario) -> None:
    """Placar consolidado, para o relatório de aceite."""
    certos = sum(
        certificar(montar(c, tabs[c.tabela]), tabs[c.tabela], glossario).estado == "aprovado"
        for c in CERTOS)
    errados = sum(
        certificar(montar(c, tabs[c.tabela]), tabs[c.tabela], glossario).estado == "reprovado"
        for c in ERRADOS)
    assert len(CERTOS) >= 40 and len(ERRADOS) >= 30
    assert certos == len(CERTOS)
    assert errados == len(ERRADOS)
