// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Cliente do trabalhador de cálculo. Manda um pedido por vez; cada pedido tem
// tempo limite contado a partir do momento em que começa a rodar (T-06). Se
// estourar, o trabalhador é encerrado e recriado, e o pedido volta com o erro
// "tempo_esgotado"; os pedidos que estavam na fila seguem depois da partida.

import type { DoTrabalhador, Etapa, ParaTrabalhador, Recurso } from "./protocolo";

export interface ErroMotor { codigo: string; mensagem: string; chave: string; detalhe: unknown }

export type EstadoDoMotor =
  | { estado: "carregando"; etapa: Etapa; fracao: number | null }
  | { estado: "pronto" }
  | { estado: "ocupado" }
  | { estado: "reiniciando" }
  | { estado: "falhou"; detalhe: string };

interface Pedido {
  id: number;
  rota: string;
  dados: unknown;
  chave?: string;
  limiteMs: number;
  resolver: (r: { ok?: unknown; erro?: ErroMotor; ms: number }) => void;
}

/** Tempo limite padrão por pedido, provisório até a medição da fase 1C (decisão 0006). */
export const LIMITE_MS = 30_000;

export class Motor {
  private trabalhador: Worker | null = null;
  private pronto = false;
  private fila: Pedido[] = [];
  private emCurso: Pedido | null = null;
  private relogio: ReturnType<typeof setTimeout> | undefined;
  private proximoId = 1;
  private ouvintes = new Set<(e: EstadoDoMotor) => void>();
  estado: EstadoDoMotor = { estado: "carregando", etapa: "python", fracao: null };
  /** Medição da última partida: tempo e o que foi baixado. */
  partida: { ms: number; recursos: Recurso[] } | null = null;

  constructor(private base: string, private criar: () => Worker) {}

  ouvir(f: (e: EstadoDoMotor) => void): () => void {
    this.ouvintes.add(f);
    f(this.estado);
    return () => this.ouvintes.delete(f);
  }

  private mudar(e: EstadoDoMotor): void {
    this.estado = e;
    for (const f of this.ouvintes) f(e);
  }

  iniciar(): void {
    this.pronto = false;
    const w = this.criar();
    this.trabalhador = w;
    w.onmessage = (ev: MessageEvent<DoTrabalhador>) => this.receber(ev.data);
    w.onerror = (ev) => this.mudar({ estado: "falhou", detalhe: ev.message });
    w.postMessage({ tipo: "iniciar", base: this.base } satisfies ParaTrabalhador);
  }

  /**
   * Pede um cálculo. Com `chave`, um pedido novo substitui o que ainda espera na
   * fila com a mesma chave (só o último "analisar" de uma digitação importa).
   */
  pedir(rota: string, dados: unknown, opcoes: { chave?: string; limiteMs?: number } = {}):
    Promise<{ ok?: unknown; erro?: ErroMotor; ms: number }> {
    return new Promise((resolver) => {
      if (opcoes.chave) {
        for (const p of this.fila.filter((q) => q.chave === opcoes.chave)) {
          p.resolver({ erro: { codigo: "cancelado", mensagem: "", chave: "", detalhe: null }, ms: 0 });
        }
        this.fila = this.fila.filter((q) => q.chave !== opcoes.chave);
      }
      this.fila.push({ id: this.proximoId++, rota, dados, chave: opcoes.chave,
        limiteMs: opcoes.limiteMs ?? LIMITE_MS, resolver });
      this.despachar();
    });
  }

  private despachar(): void {
    if (!this.pronto || this.emCurso || !this.trabalhador) return;
    const p = this.fila.shift();
    if (!p) {
      if (this.estado.estado === "ocupado") this.mudar({ estado: "pronto" });
      return;
    }
    this.emCurso = p;
    this.mudar({ estado: "ocupado" });
    this.relogio = setTimeout(() => this.estourou(p), p.limiteMs);
    this.trabalhador.postMessage({ tipo: "pedido", id: p.id, rota: p.rota, dados: p.dados } satisfies ParaTrabalhador);
  }

  private estourou(p: Pedido): void {
    if (this.emCurso !== p) return;
    this.trabalhador?.terminate();
    this.trabalhador = null;
    this.emCurso = null;
    p.resolver({ erro: { codigo: "tempo_esgotado", mensagem: "", chave: "ui.erro.tempo_esgotado",
      detalhe: { segundos: Math.round(p.limiteMs / 1000) } }, ms: p.limiteMs });
    this.mudar({ estado: "reiniciando" });
    this.iniciar();
  }

  private receber(m: DoTrabalhador): void {
    if (m.tipo === "progresso") {
      if (this.estado.estado === "reiniciando") return;
      const fracao = m.total ? (m.baixado ?? 0) / m.total : null;
      this.mudar({ estado: "carregando", etapa: m.etapa, fracao });
    } else if (m.tipo === "pronto") {
      this.pronto = true;
      this.partida = { ms: m.ms, recursos: m.recursos };
      this.mudar({ estado: "pronto" });
      this.despachar();
    } else if (m.tipo === "falhou") {
      this.mudar({ estado: "falhou", detalhe: m.detalhe });
      for (const p of this.fila.splice(0)) p.resolver({ erro: semMotor(m.detalhe), ms: 0 });
    } else if (m.tipo === "resposta" && this.emCurso?.id === m.id) {
      clearTimeout(this.relogio);
      const p = this.emCurso;
      this.emCurso = null;
      p.resolver({ ...(m.resposta as { ok?: unknown; erro?: ErroMotor }), ms: m.ms });
      this.despachar();
    }
  }
}

function semMotor(detalhe: unknown): ErroMotor {
  return { codigo: "sem_motor", mensagem: "", chave: "ui.estado.falhou", detalhe };
}
