# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Verificação por máquina das fichas de equação (seção 8.4, V1 a V6).

Cada ficha visível passa sem nenhum problema: os passos da demonstração são certificados,
a cadeia termina na equação da ficha, toda variável é isolada com passos (ou está em
``nao_isolaveis``) e o exemplo dá o valor calculado. A comparação com a fonte independente
(CoolProp ou tabela publicada) roda sempre que o CoolProp estiver instalado; no CI ele é
obrigatório (variável ``AMSIOR_REFERENCIA=1``).
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import os
from pathlib import Path
from typing import Any

import pytest

from amsior.biblioteca import carregar_biblioteca
from amsior.biblioteca.equacoes import ler_valor, verificar_ficha_equacao
from amsior.biblioteca.esquema import Ficha

BIB = Path(__file__).resolve().parents[3] / "biblioteca"
TEM_COOLPROP = importlib.util.find_spec("CoolProp") is not None
EXIGE_REFERENCIA = os.environ.get("AMSIOR_REFERENCIA") == "1"


@pytest.fixture(scope="module")
def biblioteca():  # type: ignore[no-untyped-def]
    return carregar_biblioteca(BIB)


MODELO = ("termodinamica.gas_ideal", "termodinamica.primeira_lei_sistema_fechado",
          "termodinamica.calor_sensivel", "termodinamica.clausius_clapeyron",
          "termodinamica.antoine")


@pytest.fixture(scope="module")
def resultados(biblioteca):  # type: ignore[no-untyped-def]
    """Cada ficha verificada uma vez só (a verificação completa leva segundos)."""
    return {f.id: verificar_ficha_equacao(biblioteca, f, referencia=TEM_COOLPROP)
            for f in _de_equacao(biblioteca)}


def _de_equacao(b: Any) -> list[Ficha]:
    return sorted((f for f in b.fichas.values() if f.tipo == "equacao" and f.visivel),
                  key=lambda f: f.id)


def _variante(f: Ficha, mudar: Any) -> Ficha:
    d = copy.deepcopy(f.dados)
    mudar(d)
    return dataclasses.replace(f, dados=d)


def test_coolprop_presente_no_ci() -> None:
    if EXIGE_REFERENCIA:
        assert TEM_COOLPROP, "AMSIOR_REFERENCIA=1 exige o CoolProp (requirements-referencia.txt)"


def test_as_cinco_fichas_modelo_existem(biblioteca) -> None:  # type: ignore[no-untyped-def]
    assert set(MODELO) <= {f.id for f in _de_equacao(biblioteca)}


def test_toda_ficha_de_equacao_visivel_sem_problemas(resultados) -> None:  # type: ignore[no-untyped-def]
    assert {fid: [str(p) for p in r.problemas] for fid, r in resultados.items()
            if r.problemas} == {}


@pytest.mark.parametrize("fid", MODELO)
def test_ficha_modelo(biblioteca, resultados, fid: str) -> None:  # type: ignore[no-untyped-def]
    f = biblioteca.fichas[fid]
    r = resultados[fid]
    assert [str(p) for p in r.problemas] == []
    assert all(p.certificado["estado"] == "aprovado" for p in r.passos)
    assert set(r.corpus.values()) <= {"com_passos", "nao_isolavel"}
    assert r.exemplo is not None and r.exemplo["valor"] is not None
    comp = f.dados["exemplo"].get("comparacao_independente")
    if comp and (TEM_COOLPROP or comp.get("valor") is not None):
        assert r.exemplo.get("desvio_rel") is not None
        assert r.exemplo["desvio_rel"] <= comp["desvio_aceito_rel"]


def test_valores_dos_exemplos(resultados) -> None:  # type: ignore[no-untyped-def]
    """Os números conferidos à mão na escrita das fichas (seção 8.7)."""
    esperado = {
        "termodinamica.gas_ideal": (101.396, "kPa"),
        "termodinamica.primeira_lei_sistema_fechado": (300.0, "J"),
        "termodinamica.calor_sensivel": (5.8568, "kJ"),
        "termodinamica.clausius_clapeyron": (197.507, "kPa"),
        "termodinamica.antoine": (10.5358, "kPa"),
    }
    for fid, (valor, unidade) in esperado.items():
        r = resultados[fid]
        assert r.exemplo is not None
        assert r.exemplo["unidade"] == unidade
        assert r.exemplo["valor"] == pytest.approx(valor, rel=1e-4), fid


def test_demonstracao_de_clausius_clapeyron_usa_as_hipoteses(resultados) -> None:  # type: ignore[no-untyped-def]
    r = resultados["termodinamica.clausius_clapeyron"]
    usa = [p.usa for p in r.passos if p.usa]
    assert usa == ["hipotese.volume_liquido_desprezivel", "hipotese.vapor_gas_ideal",
                   "hipotese.dhvap_constante"]
    # a integral com ΔH fora gera a hipótese de independência da temperatura
    assert any(h["chave"] == "hipotese.independe"
               for p in r.passos for h in p.certificado["hipoteses"])


# ------------------------------------------------------------------ casos que têm de falhar


def _problemas(b: Any, f: Ficha, **kw: Any) -> list[str]:
    return [str(p) for p in verificar_ficha_equacao(b, f, **kw).problemas]


def test_passo_errado_e_reprovado(biblioteca) -> None:  # type: ignore[no-untyped-def]
    f = biblioteca.fichas["termodinamica.clausius_clapeyron"]

    def errar(d: dict[str, Any]) -> None:  # T² vira T no passo de simplificar
        d["demonstracao"]["passos"][3]["depois"] = r'\frac{\mathrm{d}P}{\mathrm{d}T} = \frac{\Delta H_{vap} P}{R T}'
    p = _problemas(biblioteca, _variante(f, errar), corpus=False)
    assert any("passos[3]" in x and "passo reprovado" in x for x in p), p


def test_hipotese_usada_sem_ser_declarada(biblioteca) -> None:  # type: ignore[no-untyped-def]
    f = biblioteca.fichas["termodinamica.clausius_clapeyron"]

    def tirar(d: dict[str, Any]) -> None:
        d["hipoteses"].remove("vapor_gas_ideal")
    p = _problemas(biblioteca, _variante(f, tirar), corpus=False)
    assert any("vapor_gas_ideal sem declará-la" in x for x in p), p


def test_cadeia_que_nao_chega_na_equacao(biblioteca) -> None:  # type: ignore[no-untyped-def]
    f = biblioteca.fichas["termodinamica.calor_sensivel"]

    def cortar(d: dict[str, Any]) -> None:
        d["demonstracao"]["passos"].pop()
    p = _problemas(biblioteca, _variante(f, cortar), corpus=False)
    assert any("não termina na equação da ficha" in x for x in p), p


def test_nao_isolaveis_desatualizada(biblioteca) -> None:  # type: ignore[no-untyped-def]
    f = biblioteca.fichas["termodinamica.calor_sensivel"]

    def esquecer(d: dict[str, Any]) -> None:
        d["nao_isolaveis"] = ["T_{1}"]
    p = _problemas(biblioteca, _variante(f, esquecer))
    assert any("T_{2} não foi isolado com passos" in x for x in p), p

    def sobrar(d: dict[str, Any]) -> None:
        d["nao_isolaveis"] = ["T_{1}", "T_{2}", "n"]
    p = _problemas(biblioteca, _variante(f, sobrar))
    assert any("n agora é isolado com passos" in x for x in p), p


def test_exemplo_fora_da_tolerancia(biblioteca) -> None:  # type: ignore[no-untyped-def]
    f = biblioteca.fichas["termodinamica.primeira_lei_sistema_fechado"]

    def mentir(d: dict[str, Any]) -> None:
        d["exemplo"]["esperado"] = "301 J"
    p = _problemas(biblioteca, _variante(f, mentir), corpus=False)
    assert any("exemplo" in x for x in p), p


def test_referencia_publicada_divergente(biblioteca) -> None:  # type: ignore[no-untyped-def]
    f = biblioteca.fichas["termodinamica.calor_sensivel"]

    def trocar(d: dict[str, Any]) -> None:
        d["exemplo"]["comparacao_independente"]["valor"] = "6200 J"
    p = _problemas(biblioteca, _variante(f, trocar), corpus=False, referencia=True)
    assert any("exemplo" in x for x in p), p


def test_passo_de_aproximacao_fica_pendente(biblioteca) -> None:  # type: ignore[no-untyped-def]
    """Seção 8.5: em auto_verificada o passo aparece com selo de revisão humana; numa ficha
    verificada, só com a revisão humana registrada."""
    f = biblioteca.fichas["termodinamica.clausius_clapeyron"]

    def aproximar(d: dict[str, Any]) -> None:
        d["demonstracao"]["passos"][1]["tipo"] = "aproximacao"
    r = verificar_ficha_equacao(biblioteca, _variante(f, aproximar), corpus=False)
    assert r.problemas == []
    assert r.passos[1].certificado["estado"] == "pendente"

    def verificar_sem_revisao(d: dict[str, Any]) -> None:
        aproximar(d)
        d["estado"] = "verificada"
    p = _problemas(biblioteca, _variante(f, verificar_sem_revisao), corpus=False)
    assert any("sem revisão humana registrada" in x for x in p), p


@pytest.mark.parametrize(("texto", "valor", "unidade"), [
    ("373,15 K", 373.15, "K"), ("-39.485 K", -39.485, "K"), ("1 bar", 1.0, "bar"),
    ("5,20389", 5.20389, ""), ("1.0e-3 m^3", 1e-3, "m^3")])
def test_ler_valor(texto: str, valor: float, unidade: str) -> None:
    assert ler_valor(texto) == (pytest.approx(valor), unidade)


def test_ler_valor_sem_numero() -> None:
    with pytest.raises(ValueError):
        ler_valor("K")
