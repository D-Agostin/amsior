// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Textos da interface: vêm do catálogo do motor (chaves "ui.*"), nunca do código.

let catalogo: Record<string, string> = {};

export function carregarTextos(dados: Record<string, string>): void {
  catalogo = dados;
}

/** Texto da chave com {argumentos}; sem catálogo, devolve a própria chave. */
export function t(chave: string, args: Record<string, string | number> = {}): string {
  const modelo = catalogo[chave] ?? chave;
  // Mesmo formato do Python (str.format): {nome} é argumento, {{ e }} são chaves literais.
  return modelo.replace(/\{\{|\}\}|\{(\w+)\}/g, (todo, nome?: string) =>
    nome === undefined ? todo[0] : String(args[nome] ?? todo));
}

export interface Trecho { mat: boolean; conteudo: string }

/** Divide um texto em trechos de prosa e de matemática \( ... \). */
export function trechos(texto: string): Trecho[] {
  const out: Trecho[] = [];
  const re = /\\\((.+?)\\\)/g;
  let ultimo = 0;
  for (let m = re.exec(texto); m; m = re.exec(texto)) {
    if (m.index > ultimo) out.push({ mat: false, conteudo: texto.slice(ultimo, m.index) });
    out.push({ mat: true, conteudo: m[1] });
    ultimo = m.index + m[0].length;
  }
  if (ultimo < texto.length) out.push({ mat: false, conteudo: texto.slice(ultimo) });
  return out;
}

/** Texto sem a marcação de matemática, para atributos (title, aria-label). */
export function plano(texto: string): string {
  return texto.replace(/\\\((.+?)\\\)/g, "$1");
}
