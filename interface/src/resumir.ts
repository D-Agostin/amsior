// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Nível resumido (especificação 4.4): os passos de apresentação ("fundíveis")
// somem da tela, mas o certificado de cada um continua valendo. O último passo
// do ramo sempre aparece, porque é ele que mostra o resultado.

import type { PassoApi } from "./api";

export interface Resumo { visiveis: PassoApi[]; ocultos: number }

export function resumir(passos: PassoApi[], nivel: "completo" | "resumido"): Resumo {
  if (nivel === "completo") return { visiveis: passos, ocultos: 0 };
  const visiveis = passos.filter((p, i) => !p.fundivel || i === passos.length - 1);
  return { visiveis, ocultos: passos.length - visiveis.length };
}

/** Contagem do cabeçalho: passos e passos com certificado aprovado, somando os ramos. */
export function contar(ramos: { passos: PassoApi[] }[]): { passos: number; verificados: number } {
  let passos = 0;
  let verificados = 0;
  for (const r of ramos) {
    for (const p of r.passos) {
      passos += 1;
      if (p.selo?.estado === "aprovado") verificados += 1;
    }
  }
  return { passos, verificados };
}
