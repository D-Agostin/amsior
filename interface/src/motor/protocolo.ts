// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Mensagens entre a página e o trabalhador de cálculo (especificação 9.2).

export type Etapa = "python" | "motor" | "iniciando";

/** Página → trabalhador. */
export type ParaTrabalhador =
  | { tipo: "iniciar"; base: string }
  | { tipo: "pedido"; id: number; rota: string; dados: unknown };

/** Trabalhador → página. */
export type DoTrabalhador =
  | { tipo: "progresso"; etapa: Etapa; baixado?: number; total?: number }
  | { tipo: "pronto"; ms: number; recursos: Recurso[] }
  | { tipo: "falhou"; detalhe: string }
  | { tipo: "resposta"; id: number; ms: number; resposta: { ok?: unknown; erro?: unknown } };

export interface Manifesto { arquivo: string; sha256: string; bytes: number; biblioteca: string }

/** O que o trabalhador baixou para partir (medição da fase 1C). */
export interface Recurso { nome: string; bytes: number; transferidos: number; ms: number }
