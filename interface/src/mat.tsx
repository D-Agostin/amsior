// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Desenho de matemática com KaTeX (só leitura; a edição é do MathLive).

import katex from "katex";
import { trechos } from "./textos";

const cache = new Map<string, string>();

function html(tex: string, bloco: boolean): string {
  const chave = (bloco ? "B" : "I") + tex;
  let h = cache.get(chave);
  if (h === undefined) {
    h = katex.renderToString(tex, {
      displayMode: bloco, throwOnError: false, output: "htmlAndMathml", strict: "ignore",
    });
    if (cache.size > 2000) cache.clear();
    cache.set(chave, h);
  }
  return h;
}

/**
 * Fórmula em LaTeX. `exibicao` usa o estilo de exibição (frações em tamanho
 * cheio) sem quebrar a linha: é o das equações da folha e dos passos.
 */
export function Mat({ tex, exibicao = false, className }: { tex: string; exibicao?: boolean; className?: string }) {
  const fonte = exibicao ? `\\displaystyle ${tex}` : tex;
  return <span className={["mat", className].filter(Boolean).join(" ")} dangerouslySetInnerHTML={{ __html: html(fonte, false) }} />;
}

/** Texto do catálogo com trechos \( ... \) desenhados como matemática em linha. */
export function Texto({ texto }: { texto: string }) {
  return (
    <>
      {trechos(texto).map((tr, i) =>
        tr.mat ? <Mat key={i} tex={tr.conteudo} className="mat-linha" /> : <span key={i}>{tr.conteudo}</span>,
      )}
    </>
  );
}
