# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Achados da revisão do verificador (docs/revisoes/0001-verificador-fase-1a.md).

Cada caso é um passo errado que o verificador da fase 1A aprova, ou uma entrada
que o derruba. Todos estão marcados ``xfail(strict=True)``: a integração
contínua continua verde enquanto a falha existe e quebra no dia em que ela for
corrigida, obrigando a retirar a marca. É a regra de regressão da seção 5.4:
todo erro encontrado vira teste antes da correção.
"""

from __future__ import annotations

import pytest

from amsior.expr import Sym, TabelaDeSimbolos, analisar
from amsior.units import Glossario
from amsior.verify import certificar
from amsior.verify.certificador import Verificador
from tests.corpus.passos_ataque import Caso, tabelas
from tests.corpus.test_ataque import montar

R = "reescrever"

# (achado, caso). O achado remete à seção do relatório de revisão.
ACHADOS: list[tuple[str, Caso]] = [
    # A1: a variável mantida constante é descartada na conversão para o SymPy
    ("A1", Caso("C_p vira C_v: (dH/dT)_P reescrita como (dH/dT)_V", "termo",
                r"\left(\frac{\partial H}{\partial T}\right)_P = n R",
                r"\left(\frac{\partial H}{\partial T}\right)_V = n R", R)),
    ("A1", Caso("(dU/dT)_V reescrita como (dU/dT)_P", "termo",
                r"\left(\frac{\partial U}{\partial T}\right)_V = n R",
                r"\left(\frac{\partial U}{\partial T}\right)_P = n R", R)),
    # A2: símbolo sem dependência declarada é tratado como constante
    ("A2", Caso("derivar PV = nRT em T dá 0 = nR", "termo", r"P V = n R T", r"0 = n R",
                "derivar_ambos", "T", relacao="implica")),
    ("A2", Caso("dU/dT some", "termo", r"\frac{dU}{dT} = n R", r"0 = n R", R)),
    # A3: derivar ou integrar uma equação que não é identidade; integral sem constante
    ("A3", Caso("derivar x² = 4", "geral", r"x^2 = 4", r"2x = 0", "derivar_ambos", "x",
                relacao="implica")),
    ("A3", Caso("integrar dy/dx = 2x sem constante", "geral", r"\frac{dy}{dx} = 2x",
                r"y = x^2", "integrar_ambos", "x", relacao="implica")),
    # A4: a amostragem só cobre módulos entre 0,01 e 100
    ("A4", Caso("|Re − 2300| vira 2300 − Re", "geral", r"|u - 2300| = z", r"2300 - u = z", R)),
    ("A4", Caso("|x − 200| vira 200 − x", "geral", r"|x - 200| = z", r"200 - x = z", R)),
    ("A4", Caso("raiz de (u − 300)² vira 300 − u", "geral", r"\sqrt{(u-300)^2} = z",
                r"300 - u = z", R)),
    # A5: o resíduo é dividido por max(|a|, |b|, 1)
    ("A5", Caso("constante de Planck dobrada", "geral", r"6.626 \cdot 10^{-34} u = 10^{-34} z",
                r"13.252 \cdot 10^{-34} u = 10^{-34} z", R)),
    ("A5", Caso("sinal trocado em escala pequena", "geral", r"10^{-33} (u - v) = 0",
                r"10^{-33} (u + v) = 0", R)),
    ("A5", Caso("parcela de 10⁻³¹ somada", "geral", r"x = z", r"x = z + 10^{-31}", R)),
    # A6: a via simbólica não conhece o domínio de definição
    ("A6", Caso("cancelar (x − 1) como equivalência", "geral", r"\frac{(x-1)(x+1)}{x-1} = z",
                r"x + 1 = z", R)),
    ("A6", Caso("introduzir polo como equivalência", "geral", r"x + 1 = z",
                r"\frac{(x-1)(x+1)}{x-1} = z", R)),
    ("A6", Caso("tg x cos x vira sen x", "geral", r"\tan x \cos x = z", r"\sin x = z", R)),
    ("A6", Caso("exp(ln x) vira x com x real", "geral", r"e^{\ln x} = z", r"x = z", R)),
    ("A6", Caso("(raiz de x)² vira x com x real", "geral", r"(\sqrt{x})^2 = z", r"x = z", R)),
    ("A6", Caso("ln de negativos", "geral", r"\ln(-u) - \ln(-v) = z", r"\ln u - \ln v = z", R)),
    ("A6", Caso("raiz de negativo", "geral", r"\sqrt{-u}\sqrt{-u} = z", r"-u = z", R)),
    ("A6", Caso("somar 1/x perde a solução x = 0", "geral", r"x = 0",
                r"x + \frac{1}{x} = \frac{1}{x}", "somar_ambos", r"\frac{1}{x}")),
    ("A6", Caso("multiplicar por 1/x perde x = 0", "geral", r"x^2 = x", r"x = 1",
                "multiplicar_ambos", r"\frac{1}{x}", relacao="implica")),
    ("A6", Caso("integral definida atravessando o polo", "geral",
                r"z = \int_{a}^{b} \frac{1}{x^2} dx", r"z = \frac{1}{a} - \frac{1}{b}", R)),
    # A7: lacunas na tabela de operações
    ("A7", Caso("elevar a zero como equivalência", "geral", r"u = v", r"1 = 1",
                "elevar_ambos", "0")),
    ("A7", Caso("elevar a expoente que pode ser zero", "geral", r"u = v", r"u^a = v^a",
                "elevar_ambos", "a")),
    ("A7", Caso("raiz de índice simbólico", "geral", r"u = v", r"u^{1/a} = v^{1/a}",
                "raiz_ambos", "a")),
    # A8: desigualdades são aceitas por acidente
    ("A8", Caso("x > 100 vira x > 150", "geral", r"x > 100", r"x > 150", R)),
    ("A8", Caso("x > 1 vira x > 2", "geral", r"x > 1", r"x > 2", R)),
    # A9: substituição e condições sem conferência mínima
    ("A9", Caso("substituir x por x + 1", "geral", r"x = z", r"x + 1 = z", "substituir",
                "x + 1", relacao="restringe", simbolo="x")),
    ("A9", Caso("condições contraditórias", "geral", r"x z = x", r"z = 1", "dividir_ambos",
                "x", relacao="restringe", condicoes=(r"x > 1", r"x < 0"))),
]

# A10: entradas que fazem o verificador levantar exceção em vez de reprovar
EXCECOES: list[Caso] = [
    Caso("derivar em relação a um número", "geral", r"u = v", r"u = v", "derivar_ambos", "2",
         relacao="implica"),
    Caso("substituir a variável de uma derivada", "reator", r"\frac{dC_{A}}{dt} = -k C_{A}",
         r"\frac{dC_{A}}{dt} = -k C_{A}", "substituir", "5", relacao="restringe", simbolo="t"),
]

# A6 na camada V2: (equação, solução falsa de x)
V2_FALSAS: list[tuple[str, str]] = [
    (r"\frac{(x-1)(x+1)}{x-1} = 2", "1"),
    (r"x \cdot \frac{1}{x} = 1", "0"),
    (r"e^{\ln x} = -3", "-3"),
    (r"(\sqrt{x})^2 = -4", "-4"),
]


@pytest.fixture(scope="module")
def tabs(glossario: Glossario) -> dict[str, TabelaDeSimbolos]:
    return tabelas(glossario)


@pytest.mark.xfail(strict=True, reason="achado da revisão 0001, ainda sem correção")
@pytest.mark.parametrize(("achado", "caso"), ACHADOS,
                         ids=[f"{a}: {c.nome}" for a, c in ACHADOS])
def test_passo_errado_e_reprovado(achado: str, caso: Caso, tabs: dict[str, TabelaDeSimbolos],
                                  glossario: Glossario) -> None:
    cert = certificar(montar(caso, tabs[caso.tabela]), tabs[caso.tabela], glossario)
    assert cert.estado == "reprovado"


@pytest.mark.xfail(strict=True, reason="achado A10 da revisão 0001, ainda sem correção")
@pytest.mark.parametrize("caso", EXCECOES, ids=[c.nome for c in EXCECOES])
def test_entrada_ruim_reprova_sem_excecao(caso: Caso, tabs: dict[str, TabelaDeSimbolos],
                                          glossario: Glossario) -> None:
    cert = certificar(montar(caso, tabs[caso.tabela]), tabs[caso.tabela], glossario)
    assert cert.estado == "reprovado"


@pytest.mark.xfail(strict=True, reason="achado A6 da revisão 0001, ainda sem correção")
@pytest.mark.parametrize(("equacao", "solucao"), V2_FALSAS, ids=[e for e, _ in V2_FALSAS])
def test_v2_recusa_solucao_fora_do_dominio(equacao: str, solucao: str,
                                           tabs: dict[str, TabelaDeSimbolos],
                                           glossario: Glossario) -> None:
    tab = tabs["geral"]
    x = analisar("x", tab)
    assert isinstance(x, Sym)
    r = Verificador(tab, glossario).verificar_solucao(
        analisar(equacao, tab), x, analisar(solucao, tab))
    assert not r.aprovado
