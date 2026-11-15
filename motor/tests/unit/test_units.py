# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import math

import pytest

from amsior.erros import ErroDeUnidade
from amsior.expr import TabelaDeSimbolos, analisar
from amsior.units import (
    UM, Glossario, dimensao_de_unidade, para_si, de_si, pressao_absoluta,
    verificar_homogeneidade,
)


def test_glossario_carrega_e_tem_dimensoes_coerentes(glossario: Glossario) -> None:
    assert len(glossario) >= 50
    assert glossario["pressao_absoluta"].dimensao.texto() == "kg·m⁻¹·s⁻²"
    assert glossario["constante_gases"].dimensao == (
        dimensao_de_unidade("J") / dimensao_de_unidade("mol*K"))
    assert glossario["numero_adimensional"].dimensao.adimensional()
    for g in glossario:
        assert g.suposicoes, g.id


def test_suposicoes_vem_da_grandeza(glossario: Glossario) -> None:
    s = glossario.simbolo("T", "temperatura_absoluta")
    assert s.suposicoes == frozenset({"positivo"})
    assert glossario.simbolo("q", "potencia").suposicoes == frozenset({"real"})


@pytest.mark.parametrize(("valor", "unidade", "grandeza", "esperado"), [
    (25, "°C", "temperatura_absoluta", 298.15),
    (25, "degC", "temperatura_absoluta", 298.15),
    (25, "°C", "diferenca_temperatura", 25.0),
    (77, "°F", "temperatura_absoluta", 298.15),
    (1, "atm", "pressao_absoluta", 101325.0),
    (1, "bar", "pressao_absoluta", 1e5),
    (760, "torr", "pressao_absoluta", 101325.0),
    (1, "mmHg", "pressao_absoluta", 133.322387415),
    (40.66, "kJ/mol", "entalpia_vaporizacao_molar", 40660.0),
    (2, "L", "volume", 0.002),
    (1, "cP", "viscosidade_dinamica", 1e-3),
    (50, "%", "conversao", 0.5),
    (1, "kmol", "quantidade_materia", 1000.0),
    (1, "kg/kmol", "massa_molar", 1e-3),
])
def test_conversao_para_si(valor: float, unidade: str, grandeza: str, esperado: float,
                           glossario: Glossario) -> None:
    assert math.isclose(para_si(valor, unidade, glossario[grandeza]), esperado, rel_tol=1e-9)


def test_volta_do_si(glossario: Glossario) -> None:
    assert math.isclose(de_si(298.15, "°C", glossario["temperatura_absoluta"]), 25.0)
    assert math.isclose(de_si(10.0, "°C", glossario["diferenca_temperatura"]), 10.0)


@pytest.mark.parametrize(("unidade", "grandeza", "chave"), [
    ("kg", "pressao_absoluta", "erro.unidade.incompativel"),
    ("delta_degC", "temperatura_absoluta", "erro.unidade.diferenca_em_absoluta"),
    ("xyz", "massa", "erro.unidade.desconhecida"),
])
def test_conversao_recusa(unidade: str, grandeza: str, chave: str, glossario: Glossario) -> None:
    with pytest.raises(ErroDeUnidade) as info:
        para_si(1, unidade, glossario[grandeza])
    assert info.value.chave == chave
    assert info.value.mensagem()


def test_pressao_manometrica_exige_atmosferica_explicita() -> None:
    assert pressao_absoluta(2e5, 101325.0) == 301325.0
    with pytest.raises(ErroDeUnidade):
        pressao_absoluta(2e5, 0.0)


def _tab(glossario: Glossario, **mapa: str) -> TabelaDeSimbolos:
    return TabelaDeSimbolos.de([glossario.simbolo(k.replace("__", "_"), v)
                                for k, v in mapa.items()])


@pytest.mark.parametrize(("latex", "estado", "chave"), [
    (r"PV = nRT", "aprovado", None),
    (r"P V = n T", "reprovado", "erro.dim.lados_diferentes"),
    (r"P + T = 0", "reprovado", "erro.dim.soma_inconsistente"),
    (r"\ln P = 1", "reprovado", "erro.dim.argumento_nao_adimensional"),
    (r"\ln\frac{P}{P} = 0", "aprovado", None),
    (r"e^{T} = 1", "reprovado", "erro.dim.argumento_nao_adimensional"),
    (r"e^{\frac{-E}{RT}} = 1", "aprovado", None),
    (r"P^{T} = 1", "reprovado", "erro.dim.argumento_nao_adimensional"),
    (r"\sqrt{P^2} = P", "aprovado", None),
    (r"x = 1", "indeterminado", None),
    (r"PV - nRT = 0", "aprovado", None),
    (r"T + 1 = T", "reprovado", "erro.dim.soma_inconsistente"),
    (r"\int_0^T P\,dT = P T", "aprovado", None),
    (r"\int_0^P P\,dT = P T", "reprovado", "erro.dim.limite_inconsistente"),
    (r"\frac{dP}{dT} = \frac{P}{T}", "aprovado", None),
])
def test_homogeneidade(latex: str, estado: str, chave: str | None, glossario: Glossario) -> None:
    tab = _tab(glossario, P="pressao_absoluta", V="volume", n="quantidade_materia",
               R="constante_gases", T="temperatura_absoluta", E="energia_ativacao")
    r = verificar_homogeneidade(analisar(rf"{latex}", tab), tab, glossario)
    assert r.estado == estado
    if chave:
        assert r.erro is not None and r.erro.chave == chave
        assert r.erro.mensagem()


def test_expoente_simbolico_politropico(glossario: Glossario) -> None:
    tab = _tab(glossario, P__1="pressao_absoluta", P__2="pressao_absoluta", V__1="volume",
               V__2="volume", n="expoente")
    tab2 = TabelaDeSimbolos.de([glossario.simbolo(s, g) for s, g in (
        ("P_{1}", "pressao_absoluta"), ("P_{2}", "pressao_absoluta"), ("V_{1}", "volume"),
        ("V_{2}", "volume"), ("n", "expoente"))])
    assert len(tab) == 5
    ok = verificar_homogeneidade(analisar("P_1 V_1^n = P_2 V_2^n", tab2), tab2, glossario)
    ruim = verificar_homogeneidade(analisar("P_1 V_1^n = P_2 V_2", tab2), tab2, glossario)
    assert ok.estado == "aprovado"
    assert ruim.estado == "reprovado"


def test_empirica_dimensional_e_dispensada(glossario: Glossario) -> None:
    tab = TabelaDeSimbolos()
    r = verificar_homogeneidade(analisar("x", tab, "produto"), tab, glossario,
                                empirica_dimensional=True)
    assert r.estado == "dispensado"
    assert UM.adimensional()
