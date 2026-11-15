// Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
import { aplicar, gravarPreferencias, lerPreferencias, modoEfetivo, PADRAO } from "../preferencias";

describe("preferências de aparência", () => {
  beforeEach(() => localStorage.clear());

  it("padrão: aparência D, seguir o sistema, completo", () => {
    expect(lerPreferencias()).toEqual(PADRAO);
    expect(PADRAO.aparencia).toBe("d");
  });

  it("grava e lê de volta", () => {
    gravarPreferencias({ aparencia: "h", modo: "escuro", nivel: "resumido" });
    expect(lerPreferencias()).toEqual({ aparencia: "h", modo: "escuro", nivel: "resumido" });
  });

  it("valor estranho ou JSON quebrado volta ao padrão", () => {
    localStorage.setItem("amsior.preferencias", '{"aparencia":"z","modo":1}');
    expect(lerPreferencias()).toEqual(PADRAO);
    localStorage.setItem("amsior.preferencias", "{quebrado");
    expect(lerPreferencias()).toEqual(PADRAO);
  });

  it("seguir o Windows resolve para claro ou escuro", () => {
    expect(modoEfetivo("sistema", true)).toBe("escuro");
    expect(modoEfetivo("sistema", false)).toBe("claro");
    expect(modoEfetivo("claro", true)).toBe("claro");
  });

  it("aplica os atributos que os tokens leem", () => {
    const el = document.createElement("html");
    aplicar({ aparencia: "h", modo: "sistema", nivel: "completo" }, true, el);
    expect(el.dataset).toMatchObject({ aparencia: "h", modo: "escuro" });
  });
});
