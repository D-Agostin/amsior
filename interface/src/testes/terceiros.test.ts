// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// A tela "Sobre" lista as bibliotecas de terceiros com a licença de cada uma: a
// lista tem de bater com o arquivo de trava do npm e cobrir tudo o que vai ao site.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import terceiros from "../dados/terceiros.json";

const trava = JSON.parse(readFileSync(join(process.cwd(), "package-lock.json"), "utf-8")) as
  { packages: Record<string, { license?: string }> };
const pacote = JSON.parse(readFileSync(join(process.cwd(), "package.json"), "utf-8")) as
  { dependencies: Record<string, string> };

describe("bibliotecas de terceiros na tela Sobre", () => {
  it.each(terceiros.filter((b) => b.origem.startsWith("npm:")))("$nome: licença igual à do pacote", (b) => {
    const nome = b.origem.slice(4);
    expect(trava.packages[`node_modules/${nome}`]?.license).toBe(b.licenca);
  });

  it("toda dependência da interface aparece (menos a ponte React-DOM, mesma licença do React)", () => {
    const listadas = new Set(terceiros.map((b) => b.origem.replace(/^npm:/, "")));
    const faltam = Object.keys(pacote.dependencies).filter((d) => d !== "react-dom" && !listadas.has(d));
    expect(faltam).toEqual([]);
  });
});
