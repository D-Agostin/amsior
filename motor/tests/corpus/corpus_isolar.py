# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Corpus de isolamento da fase 1B (critério de aceite, seção 10.1).

Equações da lista de fichas (seção 8.7), com as grandezas do glossário. Para
cada símbolo de papel variável ou parâmetro, o resultado esperado é "passos"
(isola com passos certificados), salvo quando declarado outro:

* ``"sem_passos"``: sem forma fechada pelas regras; vale o resultado do
  oráculo, se passar em V2;
* ``"nao_isolavel"``: aceita ``sem_passos`` ou ``recusado`` (forma
  transcendental, como o LMTD em ΔT₂).

Constantes físicas (``papel="constante"``) não são isoladas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from amsior.expr import Simbolo, TabelaDeSimbolos
from amsior.units import Glossario


@dataclass(frozen=True)
class EqCorpus:
    nome: str
    latex: str
    simbolos: dict[str, str]  # id → grandeza ("grandeza:papel" para mudar o papel)
    esperado: dict[str, str] = field(default_factory=dict)


def tabela(e: EqCorpus, g: Glossario) -> TabelaDeSimbolos:
    out: list[Simbolo] = []
    for sid, spec in e.simbolos.items():
        grandeza, _, papel = spec.partition(":")
        out.append(g.simbolo(sid, grandeza, papel=papel or "variavel"))  # type: ignore[arg-type]
    return TabelaDeSimbolos.de(out)


R = "constante_gases:constante"
CORPUS: list[EqCorpus] = [
    # ------------------------------------------------------------ termodinâmica
    EqCorpus("gás ideal", "PV = nRT", {"P": "pressao_absoluta", "V": "volume",
             "n": "quantidade_materia", "R": R, "T": "temperatura_absoluta"}),
    EqCorpus("gás ideal molar", "P V_{m} = R T", {"P": "pressao_absoluta",
             "V_{m}": "volume_molar", "R": R, "T": "temperatura_absoluta"}),
    EqCorpus("Boyle", "P_{1} V_{1} = P_{2} V_{2}", {"P_{1}": "pressao_absoluta",
             "P_{2}": "pressao_absoluta", "V_{1}": "volume", "V_{2}": "volume"}),
    EqCorpus("Charles", r"\frac{V_{1}}{T_{1}} = \frac{V_{2}}{T_{2}}", {"V_{1}": "volume",
             "V_{2}": "volume", "T_{1}": "temperatura_absoluta", "T_{2}": "temperatura_absoluta"}),
    EqCorpus("massa específica do gás ideal", r"\rho = \frac{P M}{R T}", {
             "\\rho": "massa_especifica", "P": "pressao_absoluta", "M": "massa_molar", "R": R,
             "T": "temperatura_absoluta"}),
    EqCorpus("fator de compressibilidade", r"Z = \frac{P V}{n R T}", {
             "Z": "fator_compressibilidade", "P": "pressao_absoluta", "V": "volume",
             "n": "quantidade_materia", "R": R, "T": "temperatura_absoluta"}),
    EqCorpus("1ª lei, sistema fechado", r"\Delta U = Q + W", {"\\Delta U": "energia",
             "Q": "energia", "W": "energia"}),
    EqCorpus("entalpia", "H = U + P V", {"H": "energia", "U": "energia",
             "P": "pressao_absoluta", "V": "volume"}),
    EqCorpus("calor sensível com C_p constante", "Q = n C_{p} (T_{2} - T_{1})", {
             "Q": "energia", "n": "quantidade_materia", "C_{p}": "capacidade_calorifica_molar",
             "T_{1}": "temperatura_absoluta", "T_{2}": "temperatura_absoluta"}),
    EqCorpus("calor latente", r"Q = n \Delta H_{vap}", {"Q": "energia",
             "n": "quantidade_materia", "\\Delta H_{\\mathrm{vap}}": "entalpia_vaporizacao_molar"}),
    EqCorpus("C_p − C_v = R", "C_{p} - C_{v} = R", {"C_{p}": "capacidade_calorifica_molar",
             "C_{v}": "capacidade_calorifica_molar", "R": R}),
    EqCorpus("adiabático reversível", r"T_{2} = T_{1} \left(\frac{P_{2}}{P_{1}}\right)^{R/C_{p}}", {
             "T_{1}": "temperatura_absoluta", "T_{2}": "temperatura_absoluta",
             "P_{1}": "pressao_absoluta", "P_{2}": "pressao_absoluta", "R": R,
             "C_{p}": "capacidade_calorifica_molar"}),
    EqCorpus("trabalho isotérmico reversível", r"W = -n R T \ln\frac{V_{2}}{V_{1}}", {
             "W": "energia", "n": "quantidade_materia", "R": R, "T": "temperatura_absoluta",
             "V_{1}": "volume", "V_{2}": "volume"}),
    EqCorpus("entropia de gás ideal",
             r"\Delta S = n C_{p} \ln\frac{T_{2}}{T_{1}} - n R \ln\frac{P_{2}}{P_{1}}", {
             "\\Delta S": "entropia", "n": "quantidade_materia",
             "C_{p}": "capacidade_calorifica_molar", "R": R, "T_{1}": "temperatura_absoluta",
             "T_{2}": "temperatura_absoluta", "P_{1}": "pressao_absoluta",
             "P_{2}": "pressao_absoluta"}, {"n": "passos"}),
    EqCorpus("Clausius-Clapeyron",
             r"\ln\frac{P_{2}}{P_{1}} = -\frac{\Delta H_{vap}}{R}\left(\frac{1}{T_{2}}-\frac{1}{T_{1}}\right)", {
             "P_{1}": "pressao_saturacao", "P_{2}": "pressao_saturacao", "R": R,
             "\\Delta H_{\\mathrm{vap}}": "entalpia_vaporizacao_molar",
             "T_{1}": "temperatura_absoluta", "T_{2}": "temperatura_absoluta"}),
    EqCorpus("lei de Raoult", "y P = x P_{s}", {"y": "fracao", "P": "pressao_absoluta",
             "x": "fracao", "P_{s}": "pressao_saturacao"}),
    EqCorpus("lei de Henry", "p = H x", {"p": "pressao_absoluta", "H": "pressao_absoluta",
             "x": "fracao"}),
    # ------------------------------------------------------------ balanços
    EqCorpus("balanço de massa", "w_{1} + w_{2} = w_{3}", {"w_{1}": "vazao_massica",
             "w_{2}": "vazao_massica", "w_{3}": "vazao_massica"}),
    EqCorpus("balanço por componente", "x_{1} F_{1} + x_{2} F_{2} = x_{3} F_{3}", {
             "x_{1}": "fracao", "x_{2}": "fracao", "x_{3}": "fracao", "F_{1}": "vazao_molar",
             "F_{2}": "vazao_molar", "F_{3}": "vazao_molar"}),
    EqCorpus("conversão em escoamento", r"X = \frac{F_{A0} - F_{A}}{F_{A0}}", {
             "X": "conversao", "F_{A0}": "vazao_molar", "F_{A}": "vazao_molar"}),
    EqCorpus("conversão em batelada", "N_{A} = N_{A0} (1 - X)", {
             "N_{A}": "quantidade_materia", "N_{A0}": "quantidade_materia", "X": "conversao"}),
    EqCorpus("energia em regime permanente", "Q - W_{s} = F (H_{2} - H_{1})", {
             "Q": "potencia", "W_{s}": "potencia", "F": "vazao_molar", "H_{1}": "energia_molar",
             "H_{2}": "energia_molar"}),
    EqCorpus("lei de Hess (dois estados)", r"\Delta H = H_{2} - H_{1}", {"\\Delta H": "energia",
             "H_{1}": "energia", "H_{2}": "energia"}),
    EqCorpus("calor de reação em outra temperatura",
             r"\Delta H_{2} = \Delta H_{1} + \Delta C (T_{2} - T_{1})", {
             "\\Delta H_{2}": "energia_molar", "\\Delta H_{1}": "energia_molar",
             "\\Delta C": "capacidade_calorifica_molar", "T_{1}": "temperatura_absoluta",
             "T_{2}": "temperatura_absoluta"}),
    # ------------------------------------------------------------ reatores
    EqCorpus("Arrhenius", r"k = A e^{-E_a/(RT)}", {"k": "constante_velocidade_primeira_ordem",
             "A": "frequencia", "E_{a}": "energia_ativacao", "R": R, "T": "temperatura_absoluta"}),
    EqCorpus("Arrhenius em duas temperaturas",
             r"\ln\frac{k_{2}}{k_{1}} = \frac{E_{a}}{R}\left(\frac{1}{T_{1}} - \frac{1}{T_{2}}\right)", {
             "k_{1}": "constante_velocidade_primeira_ordem",
             "k_{2}": "constante_velocidade_primeira_ordem", "E_{a}": "energia_ativacao", "R": R,
             "T_{1}": "temperatura_absoluta", "T_{2}": "temperatura_absoluta"}),
    EqCorpus("batelada de 1ª ordem integrada", r"\ln\frac{C_{A0}}{C_{A}} = k t", {
             "C_{A0}": "concentracao_molar", "C_{A}": "concentracao_molar",
             "k": "constante_velocidade_primeira_ordem", "t": "tempo"}),
    EqCorpus("decaimento de 1ª ordem", "C_{A} = C_{A0} e^{-kt}", {
             "C_{A0}": "concentracao_molar", "C_{A}": "concentracao_molar",
             "k": "constante_velocidade_primeira_ordem", "t": "tempo"}),
    EqCorpus("CSTR", r"V = \frac{F_{A0} X}{-r_A}", {"V": "volume", "F_{A0}": "vazao_molar",
             "X": "conversao", "r_{A}": "taxa_reacao"}),
    EqCorpus("lei de velocidade de 1ª ordem", "r_{A} = -k C_{A}", {"r_{A}": "taxa_reacao",
             "k": "constante_velocidade_primeira_ordem", "C_{A}": "concentracao_molar"}),
    EqCorpus("tempo espacial", r"\tau = \frac{V}{v_{0}}", {"\\tau": "tempo_espacial",
             "V": "volume", "v_{0}": "vazao_volumetrica"}),
    EqCorpus("PFR de 1ª ordem", r"\tau = \frac{1}{k}\ln\frac{1}{1-X}", {
             "\\tau": "tempo_espacial", "k": "constante_velocidade_primeira_ordem",
             "X": "conversao"}),
    # ------------------------------------------------------------ mecânica dos fluidos
    EqCorpus("lei de Newton da viscosidade", r"\tau = \mu \frac{v}{L}", {
             "\\tau": "diferenca_pressao", "\\mu": "viscosidade_dinamica", "v": "velocidade",
             "L": "comprimento"}),
    EqCorpus("número de Reynolds", r"\mathrm{Re} = \frac{\rho v D}{\mu}", {
             "\\mathrm{Re}": "numero_adimensional", "\\rho": "massa_especifica",
             "v": "velocidade", "D": "comprimento", "\\mu": "viscosidade_dinamica"}),
    EqCorpus("continuidade", r"\rho_{1} v_{1} A_{1} = \rho_{2} v_{2} A_{2}", {
             "\\rho_{1}": "massa_especifica", "\\rho_{2}": "massa_especifica",
             "v_{1}": "velocidade", "v_{2}": "velocidade", "A_{1}": "area", "A_{2}": "area"}),
    EqCorpus("vazão e velocidade média", "Q = v A", {"Q": "vazao_volumetrica",
             "v": "velocidade", "A": "area"}),
    EqCorpus("Bernoulli",
             r"\frac{P_{1}}{\rho} + \frac{v_{1}^2}{2} + g z_{1} = \frac{P_{2}}{\rho} + \frac{v_{2}^2}{2} + g z_{2}", {
             "P_{1}": "pressao_absoluta", "P_{2}": "pressao_absoluta", "\\rho": "massa_especifica",
             "v_{1}": "velocidade", "v_{2}": "velocidade", "g": "aceleracao_gravidade:constante",
             "z_{1}": "comprimento", "z_{2}": "comprimento"}),
    EqCorpus("Darcy-Weisbach", r"h_{f} = f \frac{L}{D}\frac{v^2}{2g}", {"h_{f}": "comprimento",
             "f": "numero_adimensional", "L": "comprimento", "D": "comprimento",
             "v": "velocidade", "g": "aceleracao_gravidade:constante"}),
    EqCorpus("Hagen-Poiseuille", r"\Delta P = \frac{128 \mu L Q}{\pi D^4}", {
             "\\Delta P": "diferenca_pressao", "\\mu": "viscosidade_dinamica", "L": "comprimento",
             "Q": "vazao_volumetrica", "D": "comprimento"}),
    EqCorpus("potência de bomba", r"W = \frac{\rho g Q h}{\eta}", {"W": "potencia",
             "\\rho": "massa_especifica", "g": "aceleracao_gravidade:constante",
             "Q": "vazao_volumetrica", "h": "comprimento", "\\eta": "eficiencia"}),
    EqCorpus("energia mecânica com perdas",
             r"\frac{P_{2} - P_{1}}{\rho} + g (z_{2} - z_{1}) + e_{f} = w_{s}", {
             "P_{1}": "pressao_absoluta", "P_{2}": "pressao_absoluta", "\\rho": "massa_especifica",
             "g": "aceleracao_gravidade:constante", "z_{1}": "comprimento", "z_{2}": "comprimento",
             "e_{f}": "energia_especifica", "w_{s}": "energia_especifica"}),
    # ------------------------------------------------------------ transferência de calor
    EqCorpus("lei de Fourier", r"q = \frac{kA(T_1 - T_2)}{L}", {"q": "potencia",
             "k": "condutividade_termica", "A": "area", "T_{1}": "temperatura_absoluta",
             "T_{2}": "temperatura_absoluta", "L": "comprimento"}),
    EqCorpus("resistência de condução", r"R_{t} = \frac{L}{k A}", {"R_{t}": "resistencia_termica",
             "L": "comprimento", "k": "condutividade_termica", "A": "area"}),
    EqCorpus("parede composta", r"q = \frac{T_{1} - T_{2}}{R_{1} + R_{2}}", {"q": "potencia",
             "T_{1}": "temperatura_absoluta", "T_{2}": "temperatura_absoluta",
             "R_{1}": "resistencia_termica", "R_{2}": "resistencia_termica"}),
    EqCorpus("condução radial em cilindro",
             r"q = \frac{2\pi k L (T_{1} - T_{2})}{\ln(r_{2}/r_{1})}", {"q": "potencia",
             "k": "condutividade_termica", "L": "comprimento", "T_{1}": "temperatura_absoluta",
             "T_{2}": "temperatura_absoluta", "r_{1}": "comprimento", "r_{2}": "comprimento"}),
    EqCorpus("raio crítico de isolamento", r"r_{c} = \frac{k}{h}", {"r_{c}": "comprimento",
             "k": "condutividade_termica", "h": "coeficiente_conveccao"}),
    EqCorpus("resfriamento de Newton", r"q = hA(T_s - T_\infty)", {"q": "potencia",
             "h": "coeficiente_conveccao", "A": "area", "T_{s}": "temperatura_absoluta",
             "T_{\\infty}": "temperatura_absoluta"}),
    EqCorpus("capacitância global",
             r"\frac{T - T_{\infty}}{T_{i} - T_{\infty}} = e^{-\frac{h A}{\rho V c} t}", {
             "T": "temperatura_absoluta", "T_{\\infty}": "temperatura_absoluta",
             "T_{i}": "temperatura_absoluta", "h": "coeficiente_conveccao", "A": "area",
             "\\rho": "massa_especifica", "V": "volume", "c": "calor_especifico", "t": "tempo"}),
    EqCorpus("número de Biot", r"\mathrm{Bi} = \frac{h L}{k}", {
             "\\mathrm{Bi}": "numero_adimensional", "h": "coeficiente_conveccao",
             "L": "comprimento", "k": "condutividade_termica"}),
    EqCorpus("número de Nusselt", r"\mathrm{Nu} = \frac{h D}{k}", {
             "\\mathrm{Nu}": "numero_adimensional", "h": "coeficiente_conveccao",
             "D": "comprimento", "k": "condutividade_termica"}),
    EqCorpus("Dittus-Boelter", r"\mathrm{Nu} = 0.023 \mathrm{Re}^{0.8} \mathrm{Pr}^{0.4}", {
             "\\mathrm{Nu}": "numero_adimensional", "\\mathrm{Re}": "numero_adimensional",
             "\\mathrm{Pr}": "numero_adimensional"}),
    EqCorpus("calor numa aleta pela eficiência", r"q = \eta h A (T_{b} - T_{\infty})", {
             "q": "potencia", "\\eta": "eficiencia", "h": "coeficiente_conveccao", "A": "area",
             "T_{b}": "temperatura_absoluta", "T_{\\infty}": "temperatura_absoluta"}),
    EqCorpus("Stefan-Boltzmann",
             r"q = \varepsilon \sigma A (T_{s}^{4} - T_{v}^{4})", {"q": "potencia",
             "\\varepsilon": "emissividade", "\\sigma": "constante_stefan_boltzmann:constante",
             "A": "area", "T_{s}": "temperatura_absoluta", "T_{v}": "temperatura_absoluta"}),
    EqCorpus("coeficiente global",
             r"\frac{1}{U} = \frac{1}{h_{1}} + \frac{L}{k} + \frac{1}{h_{2}}", {
             "U": "coeficiente_global", "h_{1}": "coeficiente_conveccao",
             "h_{2}": "coeficiente_conveccao", "L": "comprimento", "k": "condutividade_termica"}),
    EqCorpus("trocador de calor", r"q = U A \Delta T_{lm}", {"q": "potencia",
             "U": "coeficiente_global", "A": "area",
             "\\Delta T_{\\mathrm{lm}}": "diferenca_temperatura"}),
    EqCorpus("LMTD",
             r"\Delta T_{lm} = \frac{\Delta T_{2} - \Delta T_{1}}{\ln(\Delta T_{2}/\Delta T_{1})}", {
             "\\Delta T_{\\mathrm{lm}}": "diferenca_temperatura",
             "\\Delta T_{1}": "diferenca_temperatura", "\\Delta T_{2}": "diferenca_temperatura"},
             {"\\Delta T_{1}": "nao_isolavel", "\\Delta T_{2}": "nao_isolavel"}),
    EqCorpus("efetividade", r"\varepsilon = \frac{q}{q_{max}}", {"\\varepsilon": "eficiencia",
             "q": "potencia", "q_{\\mathrm{max}}": "potencia"}),
    EqCorpus("calor sensível em escoamento", "q = w c (T_{2} - T_{1})", {"q": "potencia",
             "w": "vazao_massica", "c": "calor_especifico", "T_{1}": "temperatura_absoluta",
             "T_{2}": "temperatura_absoluta"}),
    # ------------------------------------------------------------ transferência de massa
    EqCorpus("1ª lei de Fick", r"J = -D \frac{C_{2} - C_{1}}{L}", {"J": "fluxo_molar",
             "D": "difusividade", "C_{1}": "concentracao_molar", "C_{2}": "concentracao_molar",
             "L": "comprimento"}),
    EqCorpus("coeficiente de transferência de massa", "J = k_{c} (C_{s} - C_{b})", {
             "J": "fluxo_molar", "k_{c}": "coeficiente_transferencia_massa",
             "C_{s}": "concentracao_molar", "C_{b}": "concentracao_molar"}),
    # ------------------------------------------------------------ operações unitárias
    EqCorpus("equilíbrio com volatilidade relativa",
             r"y = \frac{\alpha x}{1 + (\alpha - 1) x}", {"y": "fracao",
             "\\alpha": "volatilidade_relativa", "x": "fracao"}),
    EqCorpus("constante de equilíbrio", "y = K x", {"y": "fracao",
             "K": "constante_equilibrio", "x": "fracao"}),
    EqCorpus("linha de retificação",
             r"y = \frac{R_{f}}{R_{f} + 1} x + \frac{x_{D}}{R_{f} + 1}", {"y": "fracao",
             "R_{f}": "numero_adimensional", "x": "fracao", "x_{D}": "fracao"}),
    EqCorpus("Fenske",
             r"N = \frac{\ln\left(\frac{x_{D}}{1-x_{D}}\frac{1-x_{B}}{x_{B}}\right)}{\ln \alpha}", {
             "N": "numero_adimensional", "x_{D}": "fracao", "x_{B}": "fracao",
             "\\alpha": "volatilidade_relativa"},
             {"x_{D}": "nao_isolavel", "x_{B}": "nao_isolavel"}),
]
