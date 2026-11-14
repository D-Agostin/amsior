# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Suíte "verificador sob ataque" (seção 5.4).

Passos certos e passos propositalmente errados, tirados de contas reais de
engenharia química. Mede o verificador, não o motor: o critério da fase 1A é
reprovar 100% dos errados e aprovar 100% dos certos.

Cada caso declara o resultado esperado e, nos errados, o motivo que precisa
aparecer, para que um passo não seja reprovado pela razão errada.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from amsior.expr import Simbolo, TabelaDeSimbolos
from amsior.units import Glossario


def tabelas(g: Glossario) -> dict[str, TabelaDeSimbolos]:
    S = g.simbolo
    termo = TabelaDeSimbolos.de([
        *(S(p, "pressao_absoluta") for p in ("P", "P_{1}", "P_{2}")),
        *(S(v, "volume") for v in ("V", "V_{1}", "V_{2}")),
        *(S(t, "temperatura_absoluta") for t in ("T", "T_{1}", "T_{2}")),
        S("n", "quantidade_materia", papel="parametro"),
        S("R", "constante_gases", papel="constante"),
        S("W", "energia"), S("Q", "energia"), S("H", "energia"), S("U", "energia"),
        S("\\Delta H_{\\mathrm{vap}}", "entalpia_vaporizacao_molar"),
        S("\\Delta U", "energia"),
    ])
    reator = TabelaDeSimbolos.de([
        S("k", "constante_velocidade_primeira_ordem", papel="parametro"), S("A", "frequencia"),
        S("E_{a}", "energia_ativacao"), S("R", "constante_gases", papel="constante"),
        S("T", "temperatura_absoluta"),
        S("t", "tempo"), S("V", "volume"), S("F_{A0}", "vazao_molar"), S("X", "conversao"),
        S("r_{A}", "taxa_reacao"),
        S("C_{A}", "concentracao_molar", depende_de=("t",)),
        Simbolo("C_{A0}", "concentracao_molar", suposicoes=frozenset({"positivo"})),
    ])
    calor = TabelaDeSimbolos.de([
        S("q", "potencia"), S("k", "condutividade_termica"), S("A", "area"),
        S("L", "comprimento"), S("h", "coeficiente_conveccao"),
        *(S(t, "temperatura_absoluta") for t in ("T_{1}", "T_{2}", "T_{s}", "T_{\\infty}")),
        *(S(t, "diferenca_temperatura") for t in (
            "\\Delta T_{1}", "\\Delta T_{2}", "\\Delta T_{\\mathrm{lm}}")),
    ])
    geral = TabelaDeSimbolos.de([
        *(S(s, "adimensional") for s in "abcdxz"),
        S("y", "adimensional", depende_de=("x",)),
        *(S(s, "numero_adimensional") for s in "uvpsw"),
    ])
    return {"termo": termo, "reator": reator, "calor": calor, "geral": geral}


@dataclass(frozen=True)
class Caso:
    nome: str
    tabela: str
    antes: str
    depois: str
    op: str
    arg: str | None = None
    relacao: str = "equivalente"
    condicoes: tuple[str, ...] = ()
    simbolo: str | None = None
    origem: str | None = None
    lado: str | None = None
    tipo: str = "algebra"
    espera: str = "aprovado"
    motivo: str | None = None
    origem_condicao: str = "hipotese"
    sob_hipotese: bool = False
    contexto: str = "motor"
    tags: tuple[str, ...] = field(default=())


CERTOS: list[Caso] = [
    # ---------------------------------------------------- termodinâmica
    Caso("gás ideal: dividir por V", "termo", r"PV = nRT", r"P = \frac{nRT}{V}",
         "dividir_ambos", "V"),
    Caso("gás ideal: dividir por nR", "termo", r"PV = nRT", r"\frac{PV}{nR} = T",
         "dividir_ambos", "nR"),
    Caso("trocar lados", "termo", r"\frac{PV}{nR} = T", r"T = \frac{PV}{nR}", "trocar_lados"),
    Caso("reescrever lado direito", "termo", r"P = \frac{nRT}{V}", r"P = nR\frac{T}{V}",
         "reescrever", lado="direito"),
    Caso("Clausius-Clapeyron: multiplicar por -R", "termo",
         r"\ln\frac{P_2}{P_1} = -\frac{\Delta H_{vap}}{R}\left(\frac{1}{T_2}-\frac{1}{T_1}\right)",
         r"-R\ln\frac{P_2}{P_1} = \Delta H_{vap}\left(\frac{1}{T_2}-\frac{1}{T_1}\right)",
         "multiplicar_ambos", "-R"),
    Caso("Clausius-Clapeyron: dividir com condição T2 ≠ T1", "termo",
         r"-R\ln\frac{P_2}{P_1} = \Delta H_{vap}\left(\frac{1}{T_2}-\frac{1}{T_1}\right)",
         r"\frac{-R\ln\frac{P_2}{P_1}}{\frac{1}{T_2}-\frac{1}{T_1}} = \Delta H_{vap}",
         "dividir_ambos", r"\frac{1}{T_2}-\frac{1}{T_1}", sob_hipotese=True,
         condicoes=(r"\frac{1}{T_2}-\frac{1}{T_1} \neq 0",)),
    Caso("Clausius-Clapeyron: ln dos dois lados", "termo",
         r"\frac{P_2}{P_1} = e^{-\frac{\Delta H_{vap}}{R}\left(\frac{1}{T_2}-\frac{1}{T_1}\right)}",
         r"\ln\frac{P_2}{P_1} = -\frac{\Delta H_{vap}}{R}\left(\frac{1}{T_2}-\frac{1}{T_1}\right)",
         "ln_ambos"),
    Caso("Clausius-Clapeyron: exponencial dos dois lados", "termo",
         r"\ln\frac{P_2}{P_1} = -\frac{\Delta H_{vap}}{R}\left(\frac{1}{T_2}-\frac{1}{T_1}\right)",
         r"\frac{P_2}{P_1} = e^{-\frac{\Delta H_{vap}}{R}\left(\frac{1}{T_2}-\frac{1}{T_1}\right)}",
         "exp_ambos"),
    Caso("substituir o gás ideal (hipótese) no trabalho", "termo",
         r"W = -\int_{V_1}^{V_2} P\,dV", r"W = -\int_{V_1}^{V_2} \frac{nRT}{V}\,dV",
         "substituir", r"\frac{nRT}{V}", sob_hipotese=True, simbolo="P", origem="hipotese"),
    Caso("calcular a integral do trabalho isotérmico", "termo",
         r"W = -\int_{V_1}^{V_2} \frac{nRT}{V}\,dV", r"W = -nRT\ln\frac{V_2}{V_1}",
         "reescrever", lado="direito", sob_hipotese=True),
    Caso("substituir a definição de entalpia", "termo",
         r"H = U + PV", r"H - U = PV", "subtrair_ambos", "U"),
    Caso("primeira lei: isolar Q", "termo", r"\Delta U = Q + W", r"\Delta U - W = Q",
         "subtrair_ambos", "W"),
    # ---------------------------------------------------- reatores
    Caso("Arrhenius: dividir por A", "reator", r"k = A e^{-E_a/(RT)}",
         r"\frac{k}{A} = e^{-\frac{E_a}{RT}}", "dividir_ambos", "A"),
    Caso("Arrhenius: ln com argumento adimensional", "reator",
         r"\frac{k}{A} = e^{-\frac{E_a}{RT}}", r"\ln\frac{k}{A} = -\frac{E_a}{RT}", "ln_ambos"),
    Caso("Arrhenius: multiplicar por -RT", "reator",
         r"\ln\frac{k}{A} = -\frac{E_a}{RT}", r"-RT\ln\frac{k}{A} = E_a",
         "multiplicar_ambos", "-RT"),
    Caso("batelada: separar dividindo por C_A > 0", "reator",
         r"\frac{dC_A}{dt} = -kC_A", r"\frac{1}{C_A}\frac{dC_A}{dt} = -k",
         "dividir_ambos", "C_A", sob_hipotese=True, condicoes=("C_A > 0",)),
    Caso("CSTR: multiplicar por -r_A ≠ 0", "reator",
         r"V = \frac{F_{A0}X}{-r_A}", r"V\left(-r_A\right) = F_{A0}X",
         "multiplicar_ambos", "-r_A", sob_hipotese=True, condicoes=(r"r_A \neq 0",)),
    Caso("CSTR: multiplicar sem condição, declarando só implica", "reator",
         r"V = \frac{F_{A0}X}{-r_A}", r"V\left(-r_A\right) = F_{A0}X",
         "multiplicar_ambos", "-r_A", relacao="implica"),
    # ---------------------------------------------------- calor
    Caso("Fourier: multiplicar por L", "calor", r"q = \frac{kA(T_1 - T_2)}{L}",
         r"qL = kA(T_1 - T_2)", "multiplicar_ambos", "L"),
    Caso("Fourier: dividir por q ≠ 0", "calor", r"qL = kA(T_1 - T_2)",
         r"L = \frac{kA(T_1 - T_2)}{q}", "dividir_ambos", "q", sob_hipotese=True,
         condicoes=(r"q \neq 0",)),
    Caso("Newton: dividir por hA", "calor", r"q = hA(T_s - T_\infty)",
         r"\frac{q}{hA} = T_s - T_\infty", "dividir_ambos", "hA"),
    Caso("Newton: somar T∞", "calor", r"\frac{q}{hA} = T_s - T_\infty",
         r"\frac{q}{hA} + T_\infty = T_s", "somar_ambos", r"T_\infty"),
    Caso("LMTD: trocar a ordem dos terminais (certificado numérico)", "calor",
         r"\Delta T_{lm} = \frac{\Delta T_2 - \Delta T_1}{\ln(\Delta T_2/\Delta T_1)}",
         r"\Delta T_{lm} = \frac{\Delta T_1 - \Delta T_2}{\ln(\Delta T_1/\Delta T_2)}",
         "reescrever", lado="direito"),
    # ---------------------------------------------------- álgebra geral
    Caso("raiz com x ≥ 0 declarado", "geral", r"x^2 = 4", r"x = 2", "raiz_ambos", "2",
         sob_hipotese=True, condicoes=(r"x \geq 0",)),
    Caso("raiz de símbolo positivo", "geral", r"u^2 = 4", r"u = 2", "raiz_ambos", "2"),
    Caso("quadrado declarado implica", "geral", r"\sqrt{x} = z", r"x = z^2", "elevar_ambos",
         "2", relacao="implica"),
    Caso("quadrado de lados positivos é equivalência", "geral", r"\sqrt{u} = v", r"u = v^2",
         "elevar_ambos", "2"),
    Caso("ln de produto de positivos", "geral", r"uv = p", r"\ln u + \ln v = \ln p", "ln_ambos"),
    Caso("fatorar a quadrática", "geral", r"x^2 - 3x + 2 = 0", r"(x - 1)(x - 2) = 0",
         "reescrever", lado="esquerdo"),
    Caso("multiplicar por -1", "geral", r"-x = z", r"x = -z", "multiplicar_ambos", "-1"),
    Caso("inverter os dois lados", "geral", r"\frac{u}{v} = p", r"\frac{v}{u} = \frac{1}{p}",
         "reciproco_ambos"),
    Caso("multiplicar em cruz", "geral", r"\frac{u}{v} = \frac{p}{s}", r"us = pv",
         "multiplicar_ambos", "vs"),
    Caso("somar expoentes", "geral", r"z = u^2 u^3", r"z = u^5", "reescrever", lado="direito"),
    Caso("distributiva", "geral", r"z = a(b + c)", r"z = ab + ac", "reescrever", lado="direito"),
    Caso("dividir por x - 1 com condição", "geral", r"(x - 1)z = x - 1", r"z = 1",
         "dividir_ambos", "x - 1", sob_hipotese=True, condicoes=(r"x \neq 1",)),
    Caso("derivar os dois lados (implica)", "geral", r"y = x^2", r"\frac{dy}{dx} = 2x",
         "derivar_ambos", "x", relacao="implica", tipo="calculo"),
    Caso("integrar os dois lados (implica)", "geral", r"\frac{dy}{dx} = 2x",
         r"\int \frac{dy}{dx}\,dx = \int 2x\,dx", "integrar_ambos", "x", relacao="implica",
         tipo="calculo"),
    Caso("ln de x com x > 0 declarado fica sob hipótese", "geral", r"x = u", r"\ln x = \ln u",
         "ln_ambos", sob_hipotese=True, condicoes=("x > 0",)),
    Caso("condição garantida pela suposição", "geral", r"uz = v", r"z = \frac{v}{u}",
         "dividir_ambos", "u", condicoes=(r"u \neq 0",), origem_condicao="suposicao"),
    Caso("log10 dos dois lados", "geral", r"u = 10^{z}", r"\log u = z", "log_ambos"),
    Caso("raiz cúbica de negativo é real", "geral", r"x^3 = -8", r"x = -2", "raiz_ambos", "3"),
    Caso("ln de quadrado vira 2 ln do módulo", "geral", r"\ln(x^2) = z", r"2\ln|x| = z",
         "reescrever"),
    Caso("recíproco do recíproco só implica", "geral", r"\frac{1}{\frac{1}{x}} = z", r"x = z",
         "reescrever", relacao="implica"),
    Caso("tangente como seno sobre cosseno", "geral", r"\frac{\sin x}{\cos x} = z",
         r"\tan x = z", "reescrever"),
]

ERRADOS: list[Caso] = [
    # ---------------------------------------------------- erros algébricos
    Caso("esqueceu de dividir um lado", "termo", r"PV = nRT", r"P = nRT", "dividir_ambos", "V",
         espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("dividiu pelo fator errado", "termo", r"PV = nRT", r"P = \frac{nRT}{n}",
         "dividir_ambos", "V", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("sinal trocado ao subtrair", "calor", r"\frac{q}{hA} = T_s - T_\infty",
         r"\frac{q}{hA} - T_\infty = T_s", "somar_ambos", r"T_\infty", espera="reprovado",
         motivo="verif.lado_nao_confere"),
    Caso("sinal trocado ao multiplicar por -RT", "reator", r"\ln\frac{k}{A} = -\frac{E_a}{RT}",
         r"RT\ln\frac{k}{A} = E_a", "multiplicar_ambos", "-RT", espera="reprovado",
         motivo="verif.lado_nao_confere"),
    Caso("multiplicou por -1 e esqueceu o sinal", "geral", r"-x = z", r"x = z",
         "multiplicar_ambos", "-1", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("fração invertida só de um lado", "geral", r"\frac{u}{v} = p", r"\frac{v}{u} = p",
         "reciproco_ambos", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("multiplicação em cruz errada", "geral", r"\frac{u}{v} = \frac{p}{s}", r"up = vs",
         "multiplicar_ambos", "vs", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("multiplicou expoentes", "geral", r"z = u^2 u^3", r"z = u^6", "reescrever",
         lado="direito", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("raiz da soma", "geral", r"z = \sqrt{u^2 + v^2}", r"z = u + v", "reescrever",
         lado="direito", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("distributiva incompleta", "geral", r"z = a(b + c)", r"z = ab + c", "reescrever",
         lado="direito", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("fatoração errada", "geral", r"x^2 - 3x + 2 = 0", r"(x + 1)(x + 2) = 0", "reescrever",
         lado="esquerdo", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("ln da soma como soma de ln", "geral", r"u + v = p", r"\ln u + \ln v = \ln p",
         "ln_ambos", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("ln do produto como produto de ln", "geral", r"uv = p", r"\ln u \ln v = \ln p",
         "ln_ambos", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("LMTD invertido só no logaritmo", "calor",
         r"\Delta T_{lm} = \frac{\Delta T_2 - \Delta T_1}{\ln(\Delta T_2/\Delta T_1)}",
         r"\Delta T_{lm} = \frac{\Delta T_2 - \Delta T_1}{\ln(\Delta T_1/\Delta T_2)}",
         "reescrever", lado="direito", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("integral do trabalho com logaritmo da diferença", "termo",
         r"W = -\int_{V_1}^{V_2} \frac{nRT}{V}\,dV", r"W = -nRT\ln(V_2 - V_1)",
         "reescrever", lado="direito", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("derivada errada", "geral", r"y = x^2", r"\frac{dy}{dx} = x", "derivar_ambos", "x",
         relacao="implica", tipo="calculo", espera="reprovado", motivo="verif.lado_nao_confere"),
    # ---------------------------------------------------- raízes e domínio
    Caso("raiz perdida: x² = 4 → x = 2 sem condição", "geral", r"x^2 = 4", r"x = 2",
         "raiz_ambos", "2", espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("dividir por x - 1 sem condição", "geral", r"(x - 1)z = x - 1", r"z = 1",
         "dividir_ambos", "x - 1", espera="reprovado", motivo="verif.condicao_ausente"),
    Caso("separar variáveis sem garantir C_A ≠ 0", "reator", r"\frac{dC_A}{dt} = -kC_A",
         r"\frac{1}{C_A}\frac{dC_A}{dt} = -k", "dividir_ambos", "C_A", espera="reprovado",
         motivo="verif.condicao_ausente"),
    Caso("dividir por q sem condição", "calor", r"qL = kA(T_1 - T_2)",
         r"L = \frac{kA(T_1 - T_2)}{q}", "dividir_ambos", "q", espera="reprovado",
         motivo="verif.condicao_ausente"),
    Caso("dividir por (1/T2 - 1/T1) sem condição", "termo",
         r"-R\ln\frac{P_2}{P_1} = \Delta H_{vap}\left(\frac{1}{T_2}-\frac{1}{T_1}\right)",
         r"\frac{-R\ln\frac{P_2}{P_1}}{\frac{1}{T_2}-\frac{1}{T_1}} = \Delta H_{vap}",
         "dividir_ambos", r"\frac{1}{T_2}-\frac{1}{T_1}", espera="reprovado",
         motivo="verif.condicao_ausente"),
    Caso("ln de um lado que pode ser negativo", "geral", r"x = z", r"\ln x = \ln z", "ln_ambos",
         espera="reprovado", motivo="verif.condicao_ausente"),
    Caso("quadrado declarado equivalente", "geral", r"\sqrt{x} = z", r"x = z^2",
         "elevar_ambos", "2", espera="reprovado", motivo="verif.relacao_otimista"),
    Caso("multiplicar por algo que pode ser zero declarado equivalente", "reator",
         r"V = \frac{F_{A0}X}{-r_A}", r"V\left(-r_A\right) = F_{A0}X",
         "multiplicar_ambos", "-r_A", espera="reprovado", motivo="verif.relacao_otimista"),
    Caso("derivar declarado equivalente", "geral", r"y = x^2", r"\frac{dy}{dx} = 2x",
         "derivar_ambos", "x", tipo="calculo", espera="reprovado",
         motivo="verif.relacao_otimista"),
    Caso("condição dada como garantida sem ser", "geral", r"xz = 1", r"z = \frac{1}{x}",
         "dividir_ambos", "x", condicoes=(r"x \neq 0",),
         origem_condicao="suposicao", espera="reprovado", motivo="verif.condicao_otimista"),
    # ---------------------------------------------------- dimensões
    Caso("ln de grandeza com dimensão (Arrhenius direto)", "reator", r"k = A e^{-E_a/(RT)}",
         r"\ln k = \ln A - \frac{E_a}{RT}", "ln_ambos", espera="reprovado",
         motivo="verif.dimensional"),
    Caso("diferença de logaritmos de pressões", "termo", r"z = \ln\frac{P_2}{P_1}",
         r"z = \ln P_2 - \ln P_1", "reescrever", lado="direito", espera="reprovado",
         motivo="verif.dimensional"),
    Caso("somar potência a temperatura", "calor", r"\frac{q}{hA} = T_s - T_\infty",
         r"\frac{q}{hA} + q = T_s - T_\infty + q", "somar_ambos", "q", espera="reprovado",
         motivo="verif.dimensional"),
    # ---------------------------------------------------- forma do passo
    Caso("operação inexistente", "geral", r"x = z", r"z = x", "magica", espera="reprovado",
         motivo="verif.operacao_desconhecida"),
    Caso("diz mexer só à esquerda mas mexe à direita", "geral", r"z = a(b + c)",
         r"z = ab + ac", "reescrever", lado="esquerdo", espera="reprovado",
         motivo="verif.lado_alterado"),
    Caso("condição que não é desigualdade", "geral", r"xz = 1", r"z = \frac{1}{x}",
         "dividir_ambos", "x", condicoes=("x = 2",), espera="reprovado",
         motivo="verif.condicao_invalida"),
]

# Achados da revisão 0001 (docs/revisoes/0001-verificador-fase-1a.md). Cada um
# era aprovado pelo verificador da fase 1A e agora precisa ser reprovado pelo
# motivo indicado.
_R = "reescrever"
ERRADOS_REVISAO: list[Caso] = [
    # A1: a variável mantida constante não pode se perder
    Caso("A1 C_p vira C_v", "termo", r"\left(\frac{\partial H}{\partial T}\right)_P = n R",
         r"\left(\frac{\partial H}{\partial T}\right)_V = n R", _R, espera="reprovado",
         motivo="verif.lado_nao_confere"),
    Caso("A1 (dU/dT)_V vira (dU/dT)_P", "termo",
         r"\left(\frac{\partial U}{\partial T}\right)_V = n R",
         r"\left(\frac{\partial U}{\partial T}\right)_P = n R", _R, espera="reprovado",
         motivo="verif.lado_nao_confere"),
    # A2: variável sem dependência declarada não deriva para zero
    Caso("A2 derivar PV = nRT em T", "termo", r"P V = n R T", r"0 = n R", "derivar_ambos",
         "T", relacao="implica", espera="reprovado", motivo="verif.dependencia_nao_declarada"),
    Caso("A2 dU/dT some", "termo", r"\frac{dU}{dT} = n R", r"0 = n R", _R,
         espera="reprovado", motivo="verif.dependencia_nao_declarada"),
    # A3: derivar ou integrar uma equação que não vale para todo x
    Caso("A3 derivar x² = 4", "geral", r"x^2 = 4", r"2x = 0", "derivar_ambos", "x",
         relacao="implica", espera="reprovado", motivo="verif.equacao_nao_e_identidade"),
    Caso("A3 integral indefinida sem constante", "geral", r"\frac{dy}{dx} = 2x", r"y = x^2",
         "integrar_ambos", "x", relacao="implica", espera="reprovado",
         motivo="verif.integral_indefinida"),
    # A4: ramos fora da faixa 0,01–100
    Caso("A4 |Re − 2300| vira 2300 − Re", "geral", r"|u - 2300| = z", r"2300 - u = z", _R,
         espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("A4 |x − 200| vira 200 − x", "geral", r"|x - 200| = z", r"200 - x = z", _R,
         espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("A4 raiz de (u − 300)² vira 300 − u", "geral", r"\sqrt{(u-300)^2} = z",
         r"300 - u = z", _R, espera="reprovado", motivo="verif.lado_nao_confere"),
    # A5: escalas pequenas
    Caso("A5 constante de Planck dobrada", "geral", r"6.626 \cdot 10^{-34} u = 10^{-34} z",
         r"13.252 \cdot 10^{-34} u = 10^{-34} z", _R, espera="reprovado",
         motivo="verif.lado_nao_confere"),
    Caso("A5 sinal trocado em escala pequena", "geral", r"10^{-33} (u - v) = 0",
         r"10^{-33} (u + v) = 0", _R, espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("A5 parcela de 10⁻³¹ somada", "geral", r"x = z", r"x = z + 10^{-31}", _R,
         espera="reprovado", motivo="verif.lado_nao_confere"),
    # A6: domínio de definição
    Caso("A6 cancelar (x − 1) como equivalência", "geral", r"\frac{(x-1)(x+1)}{x-1} = z",
         r"x + 1 = z", _R, espera="reprovado", motivo="verif.relacao_otimista"),
    Caso("A6 introduzir polo", "geral", r"x + 1 = z", r"\frac{(x-1)(x+1)}{x-1} = z", _R,
         espera="reprovado", motivo="verif.condicao_ausente"),
    Caso("A6 tg x cos x vira sen x", "geral", r"\tan x \cos x = z", r"\sin x = z", _R,
         espera="reprovado", motivo="verif.relacao_otimista"),
    Caso("A6 exp(ln x) vira x", "geral", r"e^{\ln x} = z", r"x = z", _R, espera="reprovado",
         motivo="verif.relacao_otimista"),
    Caso("A6 (raiz de x)² vira x", "geral", r"(\sqrt{x})^2 = z", r"x = z", _R,
         espera="reprovado", motivo="verif.relacao_otimista"),
    Caso("A6 ln de negativos", "geral", r"\ln(-u) - \ln(-v) = z", r"\ln u - \ln v = z", _R,
         espera="reprovado", motivo="verif.dominio_vazio"),
    Caso("A6 raiz de negativo", "geral", r"\sqrt{-u}\sqrt{-u} = z", r"-u = z", _R,
         espera="reprovado", motivo="verif.dominio_vazio"),
    Caso("A6 somar 1/x perde x = 0", "geral", r"x = 0", r"x + \frac{1}{x} = \frac{1}{x}",
         "somar_ambos", r"\frac{1}{x}", espera="reprovado", motivo="verif.condicao_ausente"),
    Caso("A6 multiplicar por 1/x perde x = 0", "geral", r"x^2 = x", r"x = 1",
         "multiplicar_ambos", r"\frac{1}{x}", relacao="implica", espera="reprovado",
         motivo="verif.condicao_ausente"),
    Caso("A6 integral atravessando o polo", "geral", r"z = \int_{a}^{b} \frac{1}{x^2} dx",
         r"z = \frac{1}{a} - \frac{1}{b}", _R, espera="reprovado",
         motivo="verif.relacao_otimista"),
    # A7: tabela de operações
    Caso("A7 elevar a zero", "geral", r"u = v", r"1 = 1", "elevar_ambos", "0",
         espera="reprovado", motivo="verif.relacao_otimista"),
    Caso("A7 expoente que pode ser zero", "geral", r"u = v", r"u^a = v^a", "elevar_ambos",
         "a", espera="reprovado", motivo="verif.relacao_otimista"),
    Caso("A7 raiz de índice simbólico", "geral", r"u = v", r"u^{1/a} = v^{1/a}",
         "raiz_ambos", "a", espera="reprovado", motivo="verif.indice_invalido"),
    # A8: desigualdades
    Caso("A8 x > 100 vira x > 150", "geral", r"x > 100", r"x > 150", _R, espera="reprovado",
         motivo="verif.desigualdade_nao_suportada"),
    Caso("A8 x > 1 vira x > 2", "geral", r"x > 1", r"x > 2", _R, espera="reprovado",
         motivo="verif.desigualdade_nao_suportada"),
    # A9: substituição e condições
    Caso("A9 substituir x por x + 1", "geral", r"x = z", r"x + 1 = z", "substituir", "x + 1",
         simbolo="x", espera="reprovado", motivo="verif.substituicao_recursiva"),
    Caso("A9 condições contraditórias", "geral", r"x z = x", r"z = 1", "dividir_ambos", "x",
         condicoes=(r"x > 1", r"x < 0"), espera="reprovado",
         motivo="verif.condicoes_insatisfativeis"),
    # A10: entradas que derrubavam o verificador
    Caso("A10 derivar em relação a um número", "geral", r"u = v", r"u = v", "derivar_ambos",
         "2", relacao="implica", espera="reprovado", motivo="verif.argumento_invalido"),
    Caso("A10 substituir a variável de uma derivada", "reator",
         r"\frac{dC_{A}}{dt} = -k C_{A}", r"\frac{dC_{A}}{dt} = -k C_{A}", "substituir", "5",
         simbolo="t", espera="reprovado", motivo="verif.substituicao_variavel_ligada"),
    # A14: tipo princípio só em ficha curada
    Caso("A14 passo do motor declarado princípio", "termo", r"\Delta U = Q + W",
         r"\Delta U = Q", _R, tipo="principio", espera="reprovado",
         motivo="verif.principio_fora_de_ficha"),
    # substitutos dos casos que o modelo novo passou a aceitar como certos
    Caso("raiz com x ≥ 0 e sinal errado", "geral", r"x^2 = 4", r"x = -2", "raiz_ambos", "2",
         condicoes=(r"x \geq 0",), espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("dividir por x − 1 com condição e resultado errado", "geral", r"(x - 1)z = x - 1",
         r"z = x", "dividir_ambos", "x - 1", condicoes=(r"x \neq 1",), espera="reprovado",
         motivo="verif.lado_nao_confere"),
    Caso("substituição com igualdade errada", "termo", r"W = -\int_{V_1}^{V_2} P\,dV",
         r"W = -\int_{V_1}^{V_2} \frac{nRT}{P}\,dV", "substituir", r"\frac{nRT}{V}",
         simbolo="P", origem="hipotese", espera="reprovado", motivo="verif.lado_nao_confere"),
    # rodada de ataque feita depois das correções
    Caso("ln de quadrado vira 2 ln x", "geral", r"\ln(x^2) = z", r"2\ln x = z", _R,
         espera="reprovado", motivo="verif.condicao_ausente"),
    Caso("raiz do produto separada sem sinais", "geral", r"\sqrt{xz} = a",
         r"\sqrt{x}\sqrt{z} = a", _R, espera="reprovado", motivo="verif.condicao_ausente"),
    Caso("recíproco do recíproco como equivalência", "geral", r"\frac{1}{\frac{1}{x}} = z",
         r"x = z", _R, espera="reprovado", motivo="verif.relacao_otimista"),
    Caso("exponencial da soma como soma", "geral", r"e^{x+z} = a", r"e^x + e^z = a", _R,
         espera="reprovado", motivo="verif.lado_nao_confere"),
    Caso("limites da integral trocados", "termo", r"W = -\int_{V_1}^{V_2} \frac{nRT}{V}\,dV",
         r"W = -nRT\ln\frac{V_1}{V_2}", _R, espera="reprovado",
         motivo="verif.lado_nao_confere"),
    Caso("relação inexistente", "geral", r"x = z", r"z = x", "trocar_lados",
         relacao="restringe", espera="reprovado", motivo="verif.relacao_invalida"),
]
ERRADOS += ERRADOS_REVISAO

PENDENTES: list[Caso] = [
    Caso("princípio físico exige revisão humana", "termo", r"\Delta U = Q + W",
         r"\Delta U = Q", "reescrever", tipo="principio", espera="pendente",
         motivo="verif.revisao_humana_exigida", contexto="ficha"),
]
