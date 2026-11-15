// Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
import { carregarTextos, plano, t, trechos } from "../textos";

describe("catálogo de textos", () => {
  beforeEach(() => carregarTextos({ "ui.a": "Isolar {simbolo}", "ui.b": "chave {{literal}} e {n}" }));

  it("substitui argumentos e mantém os ausentes visíveis", () => {
    expect(t("ui.a", { simbolo: "V" })).toBe("Isolar V");
    expect(t("ui.a")).toBe("Isolar {simbolo}");
  });

  it("segue o formato do Python: {{ e }} são chaves literais", () => {
    expect(t("ui.b", { n: 2 })).toBe("chave {literal} e 2");
  });

  it("sem a chave no catálogo, devolve a própria chave", () => {
    expect(t("ui.inexistente")).toBe("ui.inexistente");
  });
});

describe("separador de texto e matemática", () => {
  it("divide prosa e trechos \\( \\)", () => {
    expect(trechos("Equação do 1º grau em \\(x_{1}\\), ok")).toEqual([
      { mat: false, conteudo: "Equação do 1º grau em " },
      { mat: true, conteudo: "x_{1}" },
      { mat: false, conteudo: ", ok" },
    ]);
  });

  it("aceita vários trechos e texto só com matemática", () => {
    expect(trechos("\\(a\\) e \\(b\\)").map((x) => x.mat)).toEqual([true, false, true]);
    expect(trechos("sem fórmula")).toEqual([{ mat: false, conteudo: "sem fórmula" }]);
  });

  it("texto plano para atributos tira só a marcação", () => {
    expect(plano("Equação racional em \\(T_{2}\\)")).toBe("Equação racional em T_{2}");
  });
});
