# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
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


# ------------------------------------------------------------------ 2º grau (seção 4.2, item 4)


def _resultados(r) -> list[str]:  # type: ignore[no-untyped-def]
    return sorted(para_latex(ramo.resultado) for ramo in r.ramos)


@pytest.mark.parametrize(("latex", "esperado"), [
    ("x^2 - 2x - 8 = 0", ["x = -2", "x = 4"]),
    ("2x^2 + 3x - 2 = 0", [r"x = -2", r"x = \frac{1}{2}"]),
    ("-x^2 + 4 x = 3", ["x = 1", "x = 3"]),
    (r"1 - \frac{2}{x} = \frac{8}{x^2}", ["x = -2", "x = 4"]),  # racional que vira do 2º grau
    (r"\frac{x+1}{x-1} = x", [r"x = 1 - \sqrt{2}", r"x = \sqrt{2} + 1"]),
])
def test_segundo_grau_com_passos(latex: str, esperado: list[str], tab: TabelaDeSimbolos,
                                 glossario: Glossario) -> None:
    r = isolar(analisar(latex, tab), Sym("x"), tab, glossario)
    assert r.estado == "com_passos", r.motivo
    assert _resultados(r) == esperado
    for ramo in r.ramos:
        assert "completar_quadrado" in [p.regra for p in ramo.passos]
        assert all(p.certificado is not None and p.certificado.estado == "aprovado" for p in ramo.passos)


def test_segundo_grau_literal_da_a_formula(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    r = isolar(analisar("a x^2 + b x + c = 0", tab), Sym("x"), tab, glossario)
    assert [ramo.rotulo for ramo in r.ramos] == ["ramo.positivo", "ramo.negativo"]
    assert para_latex(r.ramos[0].resultado) == r"x = \sqrt{\frac{b^{2} - 4 a c}{4 a^{2}}} - \frac{b}{2 a}"
    regras = [p.regra for p in r.ramos[0].passos]
    assert regras[:3] == ["dividir_pelo_coeficiente", "simplificar", "completar_quadrado"]


def test_raiz_dupla_e_discriminante_negativo(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    r = isolar(analisar("x^2 - 2x + 1 = 0", tab), Sym("x"), tab, glossario)
    assert r.estado == "com_passos" and _resultados(r) == ["x = 1"]
    r = isolar(analisar("x^2 + x + 1 = 0", tab), Sym("x"), tab, glossario)
    assert r.estado == "recusado" and r.motivo is not None
    assert r.motivo.chave == "isolar.discriminante_negativo"
    r = isolar(analisar("x^2 + 1 = 0", tab), Sym("x"), tab, glossario)
    assert r.estado == "recusado" and r.motivo is not None
    assert r.motivo.chave == "isolar.potencia_par_negativa"


def test_recusa_honesta_sem_regra(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    """Grau 3 depois de reunir: o motor diz que não tem passos, não que não há forma fechada."""
    r = isolar(analisar(r"\frac{x^3 - 7x^2 + 16x - 12}{x - 2} = 0", tab), Sym("x"), tab, glossario)
    assert r.estado == "sem_passos" and r.motivo is not None
    assert r.motivo.chave == "isolar.sem_regra_reunir"
    assert [para_latex(e) for e in r.sem_passos] == ["x = 3"]  # x = 2 é raiz estranha


# ------------------------------------------------------------------ raízes estranhas (seção 4.2, item 6)


@pytest.mark.parametrize(("latex", "esperado", "estranha"), [
    (r"\sqrt{x + 2} = x", ["x = 2"], "-1"),
    (r"x = \sqrt{x + 2}", ["x = 2"], "-1"),
    (r"\sqrt{x + 6} = x", ["x = 3"], "-2"),
])
def test_radical_com_alvo_dos_dois_lados(latex: str, esperado: list[str], estranha: str,
                                         tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    r = isolar(analisar(latex, tab), Sym("x"), tab, glossario)
    assert r.estado == "com_passos" and _resultados(r) == esperado
    assert r.ramos[0].passos[0].regra == "elevar_os_dois_lados"
    assert [d.chave for d in r.descartados] == ["ramo.raiz_estranha"]
    assert r.descartados[0].args["valor"] == estranha


def test_alvo_que_some_ao_simplificar(tab: TabelaDeSimbolos, glossario: Glossario) -> None:
    r = isolar(analisar(r"\frac{x}{x - 1} = \frac{1}{x - 1}", tab), Sym("x"), tab, glossario)
    assert r.estado == "recusado" and r.motivo is not None and r.motivo.chave == "isolar.sem_solucao"
