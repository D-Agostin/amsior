# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Peças do verificador: domínio, objetos opacos, prova, avaliador próprio, amostragem e cadeia."""

from __future__ import annotations

import mpmath as mp
import pytest
import sympy as sp

from amsior.expr import Simbolo, Sym, TabelaDeSimbolos, analisar
from amsior.units import Glossario
from amsior.verify import Operacao, Passo, Verificador, certificar
from amsior.verify.amostragem import Amostrador, comparar_numerico
from amsior.verify.avaliador import Avaliador
from amsior.verify.dominio import Obrigacao, ObrigacaoIntegral, obrigacoes, opacificar
from amsior.verify.logica import base, normalizar


@pytest.fixture()
def tab(glossario: Glossario) -> TabelaDeSimbolos:
    g = glossario
    return TabelaDeSimbolos.de([
        *(g.simbolo(s, "adimensional") for s in "abxz"),
        *(g.simbolo(s, "numero_adimensional") for s in "uv"),
        g.simbolo("y", "adimensional", depende_de=("x",)),
        g.simbolo("H", "energia"), g.simbolo("T", "temperatura_absoluta"),
        g.simbolo("P", "pressao_absoluta"), g.simbolo("V", "volume"),
        g.simbolo("k", "frequencia", papel="parametro"),
    ])


# ------------------------------------------------------------ domínio


def test_obrigacoes_de_cada_no(tab: TabelaDeSimbolos) -> None:
    A = lambda s: analisar(s, tab)  # noqa: E731
    assert Obrigacao(A("x - 1"), "nao_nulo") in obrigacoes(A(r"\frac{1}{x-1}"))
    assert Obrigacao(A("x"), "positivo") in obrigacoes(A(r"\ln x"))
    assert Obrigacao(A("x"), "nao_negativo") in obrigacoes(A(r"\sqrt{x}"))
    assert obrigacoes(A(r"\sqrt[3]{x}")) == []
    assert Obrigacao(A("x"), "positivo") in obrigacoes(A("x^{a}"))
    assert Obrigacao(A("x"), "nao_nulo") in obrigacoes(A("x^{0}"))
    assert Obrigacao(A(r"\cos x"), "nao_nulo") in obrigacoes(A(r"\tan x"))


def test_obrigacao_do_integrando_vale_no_intervalo(tab: TabelaDeSimbolos) -> None:
    obr = obrigacoes(analisar(r"\int_{a}^{b} \frac{1}{x} dx", tab))
    assert len(obr) == 1 and isinstance(obr[0], ObrigacaoIntegral)
    assert obr[0].var == Sym("x")


def test_opacos(tab: TabelaDeSimbolos) -> None:
    A = lambda s: analisar(s, tab)  # noqa: E731
    o = opacificar(A(r"\left(\frac{\partial H}{\partial T}\right)_P"), tab)
    assert isinstance(o.expr, Sym) and list(o.opacos.values())[0].tipo == "parcial_mantida"
    o = opacificar(A(r"\frac{dH}{dT}"), tab)
    assert list(o.opacos.values())[0].tipo == "derivada_sem_dependencia"
    assert opacificar(A(r"\frac{dy}{dx}"), tab).opacos == {}  # y declara depender de x
    assert opacificar(A(r"\frac{d(kx)}{dx}"), tab).opacos == {}  # k é parâmetro
    assert list(opacificar(A(r"\int x\,dx"), tab).opacos.values())[0].tipo == "primitiva"


# ------------------------------------------------------------ prova


def test_sympy_ask_nao_e_confiavel() -> None:
    """Por isto o verificador não usa ``sympy.ask``: se este teste falhar, o SymPy
    corrigiu o erro, mas a decisão continua valendo."""
    a = sp.Symbol("a", real=True)
    assert sp.ask(sp.Q.positive(-a), sp.Q.nonzero(a)) is True  # falso!


def test_prova_nao_aceita_o_falso_que_o_ask_aceita() -> None:
    a = sp.Symbol("a", real=True)
    assert base([(a, "nao_nulo", "f")]).provar(-a, "positivo") is None


def test_normalizacao_reconhece_formas_equivalentes() -> None:
    a, b = sp.symbols("a b", real=True)
    fatos = base([(b / a, "positivo", "f"), (sp.log(b / a), "nao_nulo", "g")])
    assert fatos.provar(a / b, "positivo") == {"f"}
    assert fatos.provar(b, "nao_nulo") == {"f"}
    assert fatos.provar(sp.log(a / b), "nao_nulo") == {"g"}
    assert normalizar(sp.Integer(0), "nao_nulo") is None


# ------------------------------------------------------------ avaliador


def test_avaliador_real_e_independente(tab: TabelaDeSimbolos) -> None:
    av = Avaliador(tab)
    A = lambda s: analisar(s, tab)  # noqa: E731
    with mp.workdps(50):
        assert av.valor(A(r"\sqrt[3]{x}"), {"x": mp.mpf(-8)}) == -2
        assert av.valor(A(r"\ln x"), {"x": mp.mpf(-1)}) is None
        assert av.valor(A(r"\frac{1}{x}"), {"x": mp.mpf(0)}) is None
        assert av.valor(A("x^{0}"), {"x": mp.mpf(0)}) is None
        d = av.valor(A(r"\frac{d(x^3)}{dx}"), {"x": mp.mpf(2)})
        assert abs(d - 12) < mp.mpf("1e-40")
        q = av.valor(A(r"\int_{1}^{u} \frac{1}{x} dx"), {"u": mp.mpf(1000)})
        assert abs(q - mp.log(1000)) < mp.mpf("1e-40")
        assert av.valor(A(r"\int_{a}^{b} \frac{1}{x^2} dx"), {"a": mp.mpf(-1), "b": mp.mpf(1)}) \
            is None


def test_funcao_declarada_e_suave_e_fixa(tab: TabelaDeSimbolos) -> None:
    av1, av2 = Avaliador(tab, 7), Avaliador(tab, 7)
    y = analisar("y", tab)
    with mp.workdps(50):
        assert av1.valor(y, {"x": mp.mpf(3)}) == av2.valor(y, {"x": mp.mpf(3)})


# ------------------------------------------------------------ amostragem


def test_amostragem_cobre_todas_as_escalas(tab: TabelaDeSimbolos) -> None:
    am = Amostrador(["u"], tab, [], 1)
    expoentes = {int(mp.floor(mp.log10(am.ponto(i)["u"]))) // 3 for i in range(12)}
    assert expoentes == {-3, -2, -1, 0, 1, 2}


def test_ramo_longe_da_origem_e_alcancado(tab: TabelaDeSimbolos) -> None:
    A = lambda s: analisar(s, tab)  # noqa: E731
    r = comparar_numerico(A(r"\left|u - 2300\right|"), A("2300 - u"), tab, Avaliador(tab))
    assert not r.aprovado


# ------------------------------------------------------------ certificador


def test_certificar_nunca_levanta_excecao(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    passo = Passo(analisar("x = z", tab), analisar("x = z", tab), Operacao("derivar_ambos", None))
    assert certificar(passo, tab, glossario).estado == "reprovado"


def test_principio_so_em_ficha(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    passo = Passo(analisar("x = z", tab), analisar("x = 0", tab), Operacao("reescrever"),
                  tipo="principio")
    assert certificar(passo, tab, glossario).estado == "reprovado"
    assert certificar(passo, tab, glossario, "ficha").estado == "pendente"


def test_derivar_identidade_declarada_vira_hipotese(tab: TabelaDeSimbolos,
                                                    glossario: Glossario) -> None:
    A = lambda s: analisar(s, tab)  # noqa: E731
    passo = Passo(A("a x = z x"), A(r"\frac{d(ax)}{dx} = \frac{d(zx)}{dx}"),
                  Operacao("derivar_ambos", A("x"), identidade=True), relacao="implica")
    cert = certificar(passo, tab, glossario)
    assert cert.estado == "aprovado" and cert.sob_hipotese
    passo.operacao = Operacao("derivar_ambos", A("x"))
    assert certificar(passo, tab, glossario).estado == "reprovado"


def test_cadeia(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    A = lambda s: analisar(s, tab)  # noqa: E731
    v = Verificador(tab, glossario)
    p1 = Passo(A("u z = v"), A(r"z = \frac{v}{u}"), Operacao("dividir_ambos", A("u")))
    p2 = Passo(A(r"z = \frac{v}{u}"), A(r"\frac{v}{u} = z"), Operacao("trocar_lados"))
    c = v.certificar_cadeia([p1, p2])
    assert c.estado == "aprovado" and c.relacao == "equivalente"
    p3 = Passo(A(r"\frac{v}{u} = x"), A(r"x = \frac{v}{u}"), Operacao("trocar_lados"))
    c = v.certificar_cadeia([p1, p3])
    assert c.estado == "reprovado"
    assert c.motivos[0].chave == "verif.cadeia_descontinua"


def test_simbolo_novo_conta_como_variavel(glossario: Glossario) -> None:
    tab = TabelaDeSimbolos.de([Simbolo("x"), Simbolo("z")])
    passo = Passo(analisar(r"\frac{dz}{dx} = 1", tab), analisar("0 = 1", tab),
                  Operacao("reescrever"))
    assert certificar(passo, tab, glossario).estado == "reprovado"
