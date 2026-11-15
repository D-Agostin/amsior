# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Motor de isolar: apresentação, ramos, hipóteses, validade do resultado e recusa."""

from __future__ import annotations

import pytest

from amsior.expr import Sym, TabelaDeSimbolos, analisar, para_latex
from amsior.rules.simplificar import apresentar, cancelar
from amsior.steps import isolar
from amsior.units import Glossario


@pytest.fixture()
def tab(glossario: Glossario) -> TabelaDeSimbolos:
    g = glossario
    return TabelaDeSimbolos.de([
        *(g.simbolo(s, "adimensional") for s in "abcdxz"),
        *(g.simbolo(s, "numero_adimensional") for s in "uv"),
        g.simbolo("P", "pressao_absoluta"), g.simbolo("V", "volume"),
        g.simbolo("n", "quantidade_materia"), g.simbolo("R", "constante_gases", papel="constante"),
        g.simbolo("T", "temperatura_absoluta"),
    ])


def test_cancelar_e_apresentar(tab: TabelaDeSimbolos) -> None:
    A = lambda s: analisar(s, tab)  # noqa: E731
    assert cancelar(A(r"\frac{P V}{P}")) == A("V")
    assert cancelar(A("x + a - a")) == A("x")
    assert cancelar(A("a + b")) == A("a + b")  # nada a cancelar: forma do autor
    assert para_latex(apresentar(A(r"\frac{\frac{a b}{c}}{d}"))) == r"\frac{a b}{c d}"
    assert para_latex(apresentar(A(r"\frac{v}{\frac{x}{z}}"))) == r"\frac{v z}{x}"


def test_gas_ideal_em_dois_passos(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    r = isolar(analisar("PV = nRT", tab), Sym("V"), tab, glossario)
    assert r.estado == "com_passos"
    passos = r.ramos[0].passos
    assert [p.regra for p in passos] == ["dividir_ambos_lados", "simplificar"]
    assert para_latex(r.ramos[0].resultado) == r"V = \frac{n R T}{P}"
    assert not r.ramos[0].cadeia.sob_hipotese  # P > 0 vem da grandeza


def test_raiz_par_abre_dois_ramos_ou_descarta_um(tab: TabelaDeSimbolos,
                                                 glossario: Glossario) -> None:
    r = isolar(analisar("x^2 = a", tab), Sym("x"), tab, glossario)
    assert [ramo.rotulo for ramo in r.ramos] == ["ramo.positivo", "ramo.negativo"]
    r = isolar(analisar("u^2 = a", tab), Sym("u"), tab, glossario)
    assert len(r.ramos) == 1 and r.descartados[0].chave == "ramo.descartado_pelas_suposicoes"


def test_resultado_com_validade(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    r = isolar(analisar(r"z = \frac{a}{x}", tab), Sym("x"), tab, glossario)
    ramo = r.ramos[0]
    assert para_latex(ramo.resultado) == r"x = \frac{a}{z}"
    hip = [h.texto() for h in ramo.cadeia.hipoteses] + [para_latex(c.expr) for c in ramo.validade]
    assert r"x \neq 0" in hip  # o domínio da equação original fica à vista


def test_validade_extra_do_resultado(glossario: Glossario) -> None:
    g = glossario
    tab = TabelaDeSimbolos.de([g.simbolo("\\tau", "diferenca_pressao"),
                               g.simbolo("\\mu", "viscosidade_dinamica"),
                               g.simbolo("v", "velocidade"), g.simbolo("L", "comprimento")])
    r = isolar(analisar(r"\tau = \mu \frac{v}{L}", tab), Sym("L"), tab, glossario)
    assert para_latex(r.ramos[0].resultado) == r"L = \frac{\mu v}{\tau}"
    assert [para_latex(c.expr) for c in r.ramos[0].validade] == [r"v \neq 0"]


def test_linear_com_varias_ocorrencias(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    r = isolar(analisar("a x + b = c x + d", tab), Sym("x"), tab, glossario)
    assert r.estado == "com_passos"
    assert [h.texto() for h in r.ramos[0].cadeia.hipoteses] == [r"a - c \neq 0"]


def test_recusas(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    assert isolar(analisar(r"\sin x = a", tab), Sym("x"), tab, glossario).estado == "recusado"
    assert isolar(analisar("PV = nRT", tab), Sym("x"), tab, glossario).motivo.chave == \
        "isolar.alvo_ausente"  # type: ignore[union-attr]
    r = isolar(analisar("P = V", tab), Sym("P"), tab, glossario)
    assert r.motivo is not None and r.motivo.chave == "isolar.nao_homogenea"


def test_sem_passos_passa_em_v2(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    r = isolar(analisar(r"x + \ln x = a", tab), Sym("x"), tab, glossario)
    assert r.estado in ("sem_passos", "recusado") and not r.ramos


@pytest.mark.parametrize(("latex", "alvo", "chave"), [
    ("PV = nRT", "V", "tipo.polinomial_1"),
    ("x^2 = a", "x", "tipo.polinomial_2"),
    (r"z = \frac{a}{x}", "x", "tipo.racional"),
    (r"\sqrt{x} = a", "x", "tipo.irracional"),
    ("x^{0.8} = a", "x", "tipo.irracional"),
    ("e^{x} = a", "x", "tipo.exponencial"),
    ("a^{x} = z", "x", "tipo.exponencial"),
    (r"\ln\frac{a}{x} = z", "x", "tipo.logaritmica"),
    (r"x + \ln x = a", "x", "tipo.mista"),
    ("|x - a| = z", "x", "tipo.modulo"),
])
def test_tipo_da_equacao(latex: str, alvo: str, chave: str, tab: TabelaDeSimbolos) -> None:
    from amsior.rules.classificar import classificar
    c = classificar(analisar(latex, tab), alvo, tab)
    assert c is not None and c.chave == chave


def test_resultado_traz_o_tipo(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    r = isolar(analisar("PV = nRT", tab), Sym("T"), tab, glossario)
    assert r.tipo is not None and r.tipo.chave == "tipo.polinomial_1"


def test_eliminar_denominador_sem_zero_carregado(glossario: Glossario) -> None:
    """CSTR de 1ª ordem: multiplicar "... = 0" pelo denominador deixa o lado direito 0
    (nada de "0(τk + 1)" e de subtrair zero depois), e o fator aparece como na equação."""
    g = glossario
    tab = TabelaDeSimbolos.de([g.simbolo("X", "conversao"),
                               g.simbolo("k", "constante_velocidade_primeira_ordem"),
                               g.simbolo("\\tau", "tempo_espacial")])
    r = isolar(analisar(r"X = \frac{k\tau}{1 + k\tau}", tab), Sym("\\tau"), tab, glossario)
    assert r.estado == "com_passos"
    passos = r.ramos[0].passos
    elim = next(p for p in passos if p.regra == "eliminar_denominador")
    assert para_latex(elim.depois).endswith(r"\left(1 + k \tau\right) = 0")
    assert not any(r"0 \left(" in para_latex(p.depois) for p in passos)
    assert [p.regra for p in passos].count("levar_para_a_esquerda") == 1
