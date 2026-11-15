// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
import type { PassoApi } from "../api";
import { contar, resumir } from "../resumir";

function passo(indice: number, fundivel: boolean, aprovado = true): PassoApi {
  return { indice, regra: "r", latex: "x", justificativa: "", fundivel, condicoes: [],
    selo: { estado: aprovado ? "aprovado" : "reprovado", metodo: "simbolico", sob_hipotese: false, hipoteses: [] } };
}

describe("nível resumido", () => {
  const passos = [passo(1, false), passo(2, true), passo(3, false), passo(4, true)];

  it("completo mostra tudo", () => {
    expect(resumir(passos, "completo")).toEqual({ visiveis: passos, ocultos: 0 });
  });

  it("resumido junta os passos de apresentação, mas nunca esconde o último", () => {
    const r = resumir(passos, "resumido");
    expect(r.visiveis.map((p) => p.indice)).toEqual([1, 3, 4]);
    expect(r.ocultos).toBe(1);
  });

  it("mantém a numeração original, para casar com o certificado", () => {
    expect(resumir([passo(1, true), passo(2, false)], "resumido").visiveis[0].indice).toBe(2);
  });

  it("conta passos e certificados de todos os ramos", () => {
    expect(contar([{ passos }, { passos: [passo(1, false, false)] }])).toEqual({ passos: 5, verificados: 4 });
  });
});
