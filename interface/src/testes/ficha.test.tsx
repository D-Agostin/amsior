// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Ficha de conceito: numeração das equações, seções, caixas e passos (especificação 8.6).
import { flushSync } from "react-dom";
import { createRoot } from "react-dom/client";
import type { FichaApi } from "../api";
import { Ficha, numerarEquacoes } from "../componentes/Ficha";
import { useEstado } from "../estado";
import { carregarTextos } from "../textos";

const FICHA: FichaApi = {
  id: "matematica.teste", area: "matematica", estado: "auto_verificada", versao: 1,
  grupo: { pt: "Tipos de equação" }, titulo: { pt: "Teste" }, tipos: ["tipo.racional"],
  resumo: [{ texto: { pt: "Resumo com **negrito**." } }, { equacao: "x = 1", destaque: true }],
  variaveis: [{ simbolo: "X", grandeza: "conversao", nome: { pt: "conversão" } }],
  secoes: [
    { titulo: { pt: "Primeira" }, blocos: [
      { equacao: "a = b", onde: [{ simbolo: "a", texto: { pt: "um símbolo" } }] },
      { passos: [
        { titulo: { pt: "Um" }, blocos: [{ equacao: "c = d" }] },
        { titulo: { pt: "Dois" }, blocos: [{ texto: { pt: "texto com \\(x\\)" } }] },
      ] },
      { caixa: "atencao", titulo: { pt: "Cuidado" }, blocos: [{ equacao: "e = f" }] },
    ] },
  ],
  exemplos: [{ enunciado: { pt: "Resolva." }, equacao: "2x = 4", pede: "x", simbolos: [{ id: "x", grandeza: "adimensional" }], passos: true }],
  referencias: [{ titulo: "Livro", autores: ["A"], edicao: 2, ano: 2020, licenca: null, url: null, uso: "citacao",
    adaptacao: null, capitulo: null, secao: null, equacao: null, pagina: null, conferido: false }],
  relacionadas: [],
};

describe("ficha de conceito", () => {
  beforeAll(() => {
    carregarTextos({ "ui.ficha.passo": "Passo {n}", "ui.ficha.caixa.resumo": "Resumo", "ui.ficha.variaveis": "Variáveis",
      "ui.area.matematica": "Matemática" });
    useEstado.setState({ biblioteca: { areas: [{ id: "matematica", fichas: [FICHA.id] }], fichas: { [FICHA.id]: FICHA }, tipos: {} },
      glossario: [{ id: "conversao", nome: "Conversão", unidade: "", suposicoes: [] }] });
  });

  it("numera as equações na ordem de leitura, entrando em passos e caixas", () => {
    const nums = numerarEquacoes(FICHA);
    expect([...nums.values()]).toEqual([1, 2, 3, 4]);
    const passos = FICHA.secoes[0].blocos[1] as { passos: { blocos: unknown[] }[] };
    expect(nums.get(passos.passos[0].blocos[0] as never)).toBe(3);
  });

  it("desenha resumo, seções numeradas, passos, caixa e exemplos", () => {
    // render de cliente: o estado vem do zustand como no site
    const el = document.createElement("div");
    const raiz = createRoot(el);
    flushSync(() => raiz.render(<Ficha id={FICHA.id} />));
    const html = el.innerHTML;
    raiz.unmount();
    expect(html).toContain("<strong>");
    expect(html).toContain("ficha-eq-destaque");
    expect(html).toContain("(4)");
    expect(html).toContain("Passo 1");
    expect(html).toContain("ficha-caixa-atencao");
    expect(html.match(/ficha-secao-num">(\d+)</g)).toEqual([
      'ficha-secao-num">1<', 'ficha-secao-num">2<', 'ficha-secao-num">3<', 'ficha-secao-num">4<']);
  });
});

const EQUACAO: FichaApi = {
  ...FICHA, id: "termodinamica.teste", area: "termodinamica", tipos: [], tipo: "equacao", exemplos: [], secoes: [],
  equacao: {
    latex: "P V = n R T",
    simbolos: [{ id: "P", grandeza: "pressao_absoluta", papel: "variavel" }],
    hipoteses: [{ id: "gas_ideal", enunciado: { pt: "Gás ideal." } }],
    validade: { pt: "Pressões baixas." },
    isolaveis: ["P", "V"], nao_isolaveis: ["T_{1}"],
    demonstracao: {
      inicio: { tipo: "principio", titulo: { pt: "Partida" }, equacao: "a = b" },
      passos: [
        { titulo: { pt: "Integrar" }, texto: null, tipo: "calculo", relacao: "implica", depois: "c = d", condicoes: ["x \\neq 0"],
          usa: { id: "gas_ideal", enunciado: { pt: "Gás ideal." } }, usa_ficha: null, estado: "aprovado", metodo: "simbolico" },
        { titulo: null, texto: null, tipo: "aproximacao", relacao: "equivalente", depois: "e = f", condicoes: [],
          usa: null, usa_ficha: null, estado: "pendente", metodo: "revisao_humana" },
      ],
    },
    exemplo: { enunciado: { pt: "Calcule." }, dados: [{ simbolo: "n", valor: "1 mol" }], funcoes: [], origem_dos_dados: null,
      pede: "P", resultado: "P = \\frac{n R T}{V}", valor: 101.3958, unidade: "kPa",
      comparacao: { fonte: "CoolProp", valor: 101.378, desvio_rel: 0.000177 } },
  },
};

describe("ficha de equação", () => {
  it("formata números com vírgula para o KaTeX", async () => {
    const { numeroTex } = await import("../componentes/Ficha");
    expect(numeroTex(197.50676)).toBe("197{,}5");
    expect(numeroTex(10535.8)).toBe("10540");
    expect(numeroTex(300)).toBe("300");
  });

  it("desenha usar na folha, hipóteses, demonstração com selos e o exemplo", () => {
    carregarTextos({ "ui.ficha.passo": "Passo {n}", "ui.ficha.passo_ok": "Verificado", "ui.ficha.passo_pendente": "Revisão humana",
      "ui.ficha.comparacao": "Fonte {fonte}, desvio {desvio}:", "ui.ficha.usar": "Usar na folha" });
    useEstado.setState({ biblioteca: { areas: [], fichas: { [EQUACAO.id]: EQUACAO }, tipos: {} } });
    const el = document.createElement("div");
    const raiz = createRoot(el);
    flushSync(() => raiz.render(<Ficha id={EQUACAO.id} />));
    const html = el.innerHTML;
    const botoes = el.querySelectorAll(".ficha-usar-botoes button").length;
    raiz.unmount();
    expect(html).toContain("Usar na folha");
    expect(botoes).toBe(2);
    expect(html).toContain("ficha-caixa-hipoteses");
    expect(html).toContain("Verificado");
    expect(html).toContain("Revisão humana");
    expect(html).toContain("⇒");
    expect(html).toContain("Fonte CoolProp, desvio 0,018 %");
  });
});
