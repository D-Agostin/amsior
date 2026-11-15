// Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
// D-11: contraste do texto ≥ 4,5:1 na aparência D e ≥ 7:1 na H, nos dois modos,
// lido do próprio tokens.css (o único lugar com cores).
import { readFileSync } from "node:fs";
import { join } from "node:path";

// O Vitest roda na pasta interface/ (package.json).
const ler = (arq: string) => readFileSync(join(process.cwd(), "src", "estilo", arq), "utf-8");
const css = ler("tokens.css");
const base = ler("base.css");

function tema(aparencia: string, modo: string): Record<string, string> {
  const re = new RegExp(`\\[data-aparencia="${aparencia}"\\]\\[data-modo="${modo}"\\]\\s*\\{([^}]*)\\}`);
  const bloco = re.exec(css);
  if (!bloco) throw new Error(`tema ${aparencia}/${modo} ausente`);
  const cores: Record<string, string> = {};
  for (const m of bloco[1].matchAll(/--cor-([\w-]+):\s*(#[0-9A-Fa-f]{6})/g)) cores[m[1]] = m[2];
  return cores;
}

function luminancia(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}

function contraste(a: string, b: string): number {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

// Cada texto e o fundo em que ele aparece na interface.
const PARES: [string, string][] = [
  ["texto", "fundo"], ["texto", "superficie"], ["texto", "acento-suave"], ["texto", "aviso-suave"],
  ["texto-2", "fundo"], ["texto-2", "superficie"],
  ["acento-texto", "superficie"], ["acento-texto", "acento-suave"], ["acento-texto", "fundo"],
  ["sobre-acento", "acento"],
  ["ok", "superficie"], ["aviso", "superficie"], ["aviso", "aviso-suave"],
  ["erro", "superficie"], ["erro", "erro-suave"],
];

describe.each([["d", 4.5], ["h", 7]])("aparência %s", (aparencia, minimo) => {
  it.each(["claro", "escuro"])(`modo %s: todo texto com contraste ≥ ${minimo}:1`, (modo) => {
    const cores = tema(aparencia as string, modo);
    const falhas = PARES.filter(([t, f]) => contraste(cores[t], cores[f]) < (minimo as number))
      .map(([t, f]) => `${t} sobre ${f}: ${contraste(cores[t], cores[f]).toFixed(2)}`);
    expect(falhas).toEqual([]);
  });
});

it("os quatro temas declaram as mesmas cores", () => {
  const nomes = (a: string, m: string) => Object.keys(tema(a, m)).sort();
  for (const [a, m] of [["d", "escuro"], ["h", "claro"], ["h", "escuro"]]) expect(nomes(a, m)).toEqual(nomes("d", "claro"));
});

it("base.css não tem cor solta: só variáveis dos tokens", () => {
  expect(base.match(/#[0-9A-Fa-f]{3,8}\b|rgba?\(|hsla?\(/g) ?? []).toEqual([]);
});
