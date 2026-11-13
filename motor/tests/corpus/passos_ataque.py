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
        S("n", "quantidade_materia"), S("R", "constante_gases"),
        S("W", "energia"), S("Q", "energia"), S("H", "energia"), S("U", "energia"),
        S("\\Delta H_{\\mathrm{vap}}", "entalpia_vaporizacao_molar"),
        S("\\Delta U", "energia"),
    ])
    reator = TabelaDeSimbolos.de([
        S("k", "constante_velocidade_primeira_ordem"), S("A", "frequencia"),
        S("E_{a}", "energia_ativacao"), S("R", "constante_gases"), S("T", "temperatura_absoluta"),
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
         "dividir_ambos", r"\frac{1}{T_2}-\frac{1}{T_1}", relacao="restringe",
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
         "substituir", r"\frac{nRT}{V}", relacao="restringe", simbolo="P", origem="hipotese"),
    Caso("calcular a integral do trabalho isotérmico", "termo",
         r"W = -\int_{V_1}^{V_2} \frac{nRT}{V}\,dV", r"W = -nRT\ln\frac{V_2}{V_1}",
         "reescrever", lado="direito"),
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
         "dividir_ambos", "C_A", relacao="restringe", condicoes=("C_A > 0",)),
    Caso("CSTR: multiplicar por -r_A ≠ 0", "reator",
         r"V = \frac{F_{A0}X}{-r_A}", r"V\left(-r_A\right) = F_{A0}X",
         "multiplicar_ambos", "-r_A", relacao="restringe", condicoes=(r"r_A \neq 0",)),
    Caso("CSTR: multiplicar sem condição, declarando só implica", "reator",
         r"V = \frac{F_{A0}X}{-r_A}", r"V\left(-r_A\right) = F_{A0}X",
         "multiplicar_ambos", "-r_A", relacao="implica"),
    # ---------------------------------------------------- calor
    Caso("Fourier: multiplicar por L", "calor", r"q = \frac{kA(T_1 - T_2)}{L}",
         r"qL = kA(T_1 - T_2)", "multiplicar_ambos", "L"),
    Caso("Fourier: dividir por q ≠ 0", "calor", r"qL = kA(T_1 - T_2)",
         r"L = \frac{kA(T_1 - T_2)}{q}", "dividir_ambos", "q", relacao="restringe",
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
         relacao="restringe", condicoes=(r"x \geq 0",)),
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
         "dividir_ambos", "x - 1", relacao="restringe", condicoes=(r"x \neq 1",)),
    Caso("derivar os dois lados (implica)", "geral", r"y = x^2", r"\frac{dy}{dx} = 2x",
         "derivar_ambos", "x", relacao="implica", tipo="calculo"),
    Caso("integrar os dois lados (implica)", "geral", r"\frac{dy}{dx} = 2x",
         r"\int \frac{dy}{dx}\,dx = \int 2x\,dx", "integrar_ambos", "x", relacao="implica",
         tipo="calculo"),
    Caso("ln de x com x > 0 declarado restringe", "geral", r"x = u", r"\ln x = \ln u",
         "ln_ambos", relacao="restringe", condicoes=("x > 0",)),
    Caso("condição garantida pela suposição", "geral", r"uz = v", r"z = \frac{v}{u}",
         "dividir_ambos", "u", condicoes=(r"u \neq 0",), origem_condicao="suposicao"),
    Caso("log10 dos dois lados", "geral", r"u = 10^{z}", r"\log u = z", "log_ambos"),
    Caso("raiz cúbica de negativo é real", "geral", r"x^3 = -8", r"x = -2", "raiz_ambos", "3"),
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
    Caso("raiz com condição mas declarada equivalente", "geral", r"x^2 = 4", r"x = 2",
         "raiz_ambos", "2", condicoes=(r"x \geq 0",), espera="reprovado",
         motivo="verif.relacao_otimista"),
    Caso("dividir por x - 1 sem condição", "geral", r"(x - 1)z = x - 1", r"z = 1",
         "dividir_ambos", "x - 1", espera="reprovado", motivo="verif.condicao_ausente"),
    Caso("dividir por x - 1 com condição mas equivalente", "geral", r"(x - 1)z = x - 1",
         r"z = 1", "dividir_ambos", "x - 1", condicoes=(r"x \neq 1",), espera="reprovado",
         motivo="verif.relacao_otimista"),
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
    Caso("hipótese substituída declarada equivalente", "termo",
         r"W = -\int_{V_1}^{V_2} P\,dV", r"W = -\int_{V_1}^{V_2} \frac{nRT}{V}\,dV",
         "substituir", r"\frac{nRT}{V}", simbolo="P", origem="hipotese", espera="reprovado",
         motivo="verif.relacao_otimista"),
    Caso("condição dada como garantida sem ser", "geral", r"xz = 1", r"z = \frac{1}{x}",
         "dividir_ambos", "x", relacao="restringe", condicoes=(r"x \neq 0",),
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
         "dividir_ambos", "x", relacao="restringe", condicoes=("x = 2",), espera="reprovado",
         motivo="verif.condicao_invalida"),
]

PENDENTES: list[Caso] = [
    Caso("princípio físico exige revisão humana", "termo", r"\Delta U = Q + W",
         r"\Delta U = Q", "reescrever", tipo="principio", espera="pendente",
         motivo="verif.revisao_humana_exigida"),
]
