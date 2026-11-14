# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Identidade, verificação de solução (V2), serialização do passo e catálogo de textos."""

from __future__ import annotations

import json
import re
from pathlib import Path

import sympy as sp

from amsior.expr import TabelaDeSimbolos, analisar, Sym
from amsior.i18n import IDIOMA_PADRAO, campos, catalogo
from amsior.units import Glossario
from amsior.verify import Condicao, Operacao, Passo, Verificador, certificar, identicas

PACOTE = Path(__file__).resolve().parents[2] / "amsior"


def _tab_geral(g: Glossario) -> TabelaDeSimbolos:
    return TabelaDeSimbolos.de([g.simbolo(s, "numero_adimensional") for s in "ab"]
                               + [g.simbolo(s, "adimensional") for s in "xy"])


def test_identidade_simbolica_e_numerica(glossario: Glossario) -> None:
    tab = _tab_geral(glossario)
    A = lambda s: analisar(s, tab)  # noqa: E731
    assert identicas(A(r"\ln(ab)"), A(r"\ln a + \ln b"), tab).metodo == "simbolico"
    r = identicas(A(r"\sqrt{x^2}"), A("x"), tab, [A(r"x \geq 0")])
    assert r.aprovado and r.metodo == "numerico"
    assert not identicas(A(r"\sqrt{x^2}"), A("x"), tab).aprovado
    assert not identicas(A("a + b"), A("ab"), tab).aprovado


def test_contraprova_numerica_roda_mesmo_com_prova_simbolica(glossario: Glossario) -> None:
    tab = _tab_geral(glossario)
    r = identicas(analisar(r"\ln(ab)", tab), analisar(r"\ln a + \ln b", tab), tab)
    assert r.numerico is not None and r.numerico.pontos >= 20


def test_diferenca_constante_e_refutada_sem_amostragem(glossario: Glossario) -> None:
    tab = _tab_geral(glossario)
    r = identicas(analisar("x", tab), analisar("x + 10^{-31}", tab), tab)
    assert not r.aprovado and r.motivo == "verif.identidade.diferenca_constante"


def test_semente_fixa_resultado_reprodutivel(glossario: Glossario) -> None:
    tab = _tab_geral(glossario)
    A = lambda s: analisar(s, tab)  # noqa: E731
    r1 = identicas(A(r"\sqrt{x^2}"), A("x"), tab, [A(r"x \geq 0")])
    r2 = identicas(A(r"\sqrt{x^2}"), A("x"), tab, [A(r"x \geq 0")])
    assert r1.numerico is not None and r2.numerico is not None
    assert r1.numerico.auditoria() == r2.numerico.auditoria()


def _tab_reator(g: Glossario) -> TabelaDeSimbolos:
    return TabelaDeSimbolos.de([
        g.simbolo("C_{A}", "concentracao_molar", depende_de=("t",)),
        g.simbolo("C_{A0}", "concentracao_molar", papel="parametro"),
        g.simbolo("k", "frequencia", papel="parametro"),
        g.simbolo("t", "tempo"),
    ])


def test_v2_solucao_da_edo_de_primeira_ordem(glossario: Glossario) -> None:
    tab = _tab_reator(glossario)
    ver = Verificador(tab, glossario)
    edo = analisar(r"\frac{dC_A}{dt} = -kC_A", tab)
    assert ver.verificar_solucao(edo, Sym("C_{A}"), analisar(r"C_{A0} e^{-kt}", tab)).aprovado
    assert not ver.verificar_solucao(edo, Sym("C_{A}"), analisar(r"C_{A0} e^{kt}", tab)).aprovado


def test_v2_isolamento_algebrico(glossario: Glossario) -> None:
    tab = TabelaDeSimbolos.de([glossario.simbolo(s, g) for s, g in (
        ("P", "pressao_absoluta"), ("V", "volume"), ("n", "quantidade_materia"),
        ("R", "constante_gases"), ("T", "temperatura_absoluta"))])
    ver = Verificador(tab, glossario)
    eq = analisar("PV = nRT", tab)
    assert ver.verificar_solucao(eq, Sym("T"), analisar(r"\frac{PV}{nR}", tab)).aprovado
    assert not ver.verificar_solucao(eq, Sym("T"), analisar(r"\frac{PV}{n}", tab)).aprovado


def test_passo_serializa_e_volta(glossario: Glossario) -> None:
    tab = TabelaDeSimbolos.de([glossario.simbolo(s, "adimensional") for s in "xz"])
    passo = Passo(analisar("(x-1)z = x-1", tab), analisar("z = 1", tab),
                  Operacao("dividir_ambos", analisar("x - 1", tab)),
                  condicoes=(Condicao(analisar(r"x \neq 1", tab)),))
    certificar(passo, tab, glossario)
    dado = json.loads(json.dumps(passo.para_json()))
    volta = Passo.de_json(dado)
    assert volta.antes == passo.antes and volta.depois == passo.depois
    assert volta.condicoes == passo.condicoes and volta.operacao == passo.operacao
    assert dado["certificado"]["estado"] == "aprovado"
    assert dado["certificado"]["sob_hipotese"] is True
    assert dado["certificado"]["versoes"]["sympy"] == sp.__version__
    assert {"tipo": "dominio", "expressao": "x - 1", "predicado": "nao_nulo",
            "atendida_por": "condicao"} in dado["certificado"]["exigencias"]


# ------------------------------------------------------------ catálogo de textos

_CHAVE = re.compile(r"""["']((?:erro|verif|predicado|hipotese|origem|regra|isolar|ramo)\.[a-z0-9_.]+)["']""")


def _chaves_usadas() -> set[str]:
    chaves: set[str] = set()
    for arq in PACOTE.rglob("*.py"):
        chaves |= set(_CHAVE.findall(arq.read_text(encoding="utf-8")))
    return chaves


def test_toda_chave_usada_no_codigo_existe_em_pt_br() -> None:
    cat = catalogo(IDIOMA_PADRAO)
    faltando = {c for c in _chaves_usadas() if c not in cat and not c.endswith(".")}
    faltando -= {"predicado.", "origem."}
    assert not faltando, sorted(faltando)


def test_catalogo_sem_chaves_orfas_de_erro() -> None:
    usadas = _chaves_usadas()
    cat = catalogo(IDIOMA_PADRAO)
    orfas = {c for c in cat if c.startswith(("erro.", "verif.", "hipotese.", "regra.", "isolar.", "ramo.")) and c not in usadas}
    assert not orfas, sorted(orfas)


def test_catalogo_em_ingles_nao_tem_campos_divergentes() -> None:
    pt, en = catalogo("pt-BR"), catalogo("en")
    for chave, modelo in en.items():
        assert chave in pt
        assert campos(modelo) == campos(pt[chave]), chave


def test_substituicao_e_sempre_hipotese_exibida(glossario: Glossario) -> None:
    """Sem a biblioteca (fase 2), nem uma definição declarada é conferível: fica sob hipótese."""
    tab = TabelaDeSimbolos.de([glossario.simbolo(s, "energia") for s in ("H", "U", "Q")]
                              + [glossario.simbolo("P", "pressao_absoluta"),
                                 glossario.simbolo("V", "volume")])
    antes, depois = analisar("Q = H", tab), analisar("Q = U + PV", tab)
    op = Operacao("substituir", analisar("U + PV", tab), simbolo=Sym("H"), origem="definicao")
    cert = certificar(Passo(antes, depois, op), tab, glossario)
    assert cert.estado == "aprovado" and cert.sob_hipotese
    assert [h.texto() for h in cert.hipoteses] == ["H = U + P V (definição)"]
