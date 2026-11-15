// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Cliente do trabalhador de cálculo (T-06): fila, substituição e tempo limite.
import { Motor } from "../motor/cliente";
import type { DoTrabalhador, ParaTrabalhador } from "../motor/protocolo";

/** Trabalhador falso: responde quando o teste manda, ou nunca (para estourar o tempo). */
class Falso {
  static criados: Falso[] = [];
  onmessage: ((e: MessageEvent<DoTrabalhador>) => void) | null = null;
  onerror: ((e: ErrorEvent) => void) | null = null;
  recebidos: ParaTrabalhador[] = [];
  encerrado = false;
  constructor() { Falso.criados.push(this); }
  postMessage(m: ParaTrabalhador) { this.recebidos.push(m); }
  terminate() { this.encerrado = true; }
  emitir(m: DoTrabalhador) { this.onmessage?.({ data: m } as MessageEvent<DoTrabalhador>); }
  pedidos() { return this.recebidos.filter((m) => m.tipo === "pedido") as Extract<ParaTrabalhador, { tipo: "pedido" }>[]; }
}

function novo() {
  Falso.criados = [];
  const m = new Motor("/", () => new Falso() as unknown as Worker);
  m.iniciar();
  return { m, w: () => Falso.criados[Falso.criados.length - 1] };
}

describe("cliente do motor", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("guarda os pedidos até o motor ficar pronto e manda um por vez", async () => {
    const { m, w } = novo();
    const a = m.pedir("isolar", { n: 1 });
    const b = m.pedir("isolar", { n: 2 });
    expect(w().pedidos()).toHaveLength(0);
    w().emitir({ tipo: "pronto", ms: 10, recursos: [] });
    expect(w().pedidos()).toHaveLength(1);
    w().emitir({ tipo: "resposta", id: w().pedidos()[0].id, ms: 5, resposta: { ok: 1 } });
    expect((await a).ok).toBe(1);
    expect(w().pedidos()).toHaveLength(2);
    w().emitir({ tipo: "resposta", id: w().pedidos()[1].id, ms: 5, resposta: { ok: 2 } });
    expect((await b).ok).toBe(2);
    expect(m.estado.estado).toBe("pronto");
  });

  it("pedido novo com a mesma chave substitui o que ainda espera na fila", async () => {
    const { m, w } = novo();
    const velho = m.pedir("analisar", { x: 1 }, { chave: "analisar" });
    const novoPedido = m.pedir("analisar", { x: 2 }, { chave: "analisar" });
    expect((await velho).erro?.codigo).toBe("cancelado");
    w().emitir({ tipo: "pronto", ms: 1, recursos: [] });
    expect(w().pedidos().map((p) => p.dados)).toEqual([{ x: 2 }]);
    w().emitir({ tipo: "resposta", id: w().pedidos()[0].id, ms: 1, resposta: { ok: "x2" } });
    expect((await novoPedido).ok).toBe("x2");
  });

  it("estouro de tempo encerra o trabalhador, devolve o erro e recria o motor", async () => {
    const { m, w } = novo();
    w().emitir({ tipo: "pronto", ms: 1, recursos: [] });
    const travado = m.pedir("isolar", {}, { limiteMs: 1000 });
    const depois = m.pedir("isolar", { depois: true });
    const primeiro = w();
    vi.advanceTimersByTime(1001);
    const r = await travado;
    expect(r.erro?.codigo).toBe("tempo_esgotado");
    expect(r.erro?.detalhe).toEqual({ segundos: 1 });
    expect(primeiro.encerrado).toBe(true);
    expect(Falso.criados).toHaveLength(2);
    expect(m.estado.estado).toBe("reiniciando");
    // o pedido seguinte espera a nova partida e roda no trabalhador novo
    expect(w().pedidos()).toHaveLength(0);
    w().emitir({ tipo: "pronto", ms: 1, recursos: [] });
    expect(w().pedidos()[0].dados).toEqual({ depois: true });
    w().emitir({ tipo: "resposta", id: w().pedidos()[0].id, ms: 1, resposta: { ok: true } });
    expect((await depois).ok).toBe(true);
  });

  it("resposta atrasada de um pedido já encerrado é ignorada", async () => {
    const { m, w } = novo();
    w().emitir({ tipo: "pronto", ms: 1, recursos: [] });
    const p = m.pedir("isolar", {}, { limiteMs: 10 });
    const velho = w();
    const id = velho.pedidos()[0].id;
    vi.advanceTimersByTime(11);
    expect((await p).erro?.codigo).toBe("tempo_esgotado");
    velho.emitir({ tipo: "resposta", id, ms: 1, resposta: { ok: "tarde" } });
    expect(m.estado.estado).toBe("reiniciando");
  });

  it("falha na partida devolve erro aos pedidos da fila", async () => {
    const { m, w } = novo();
    const p = m.pedir("isolar", {});
    w().emitir({ tipo: "falhou", detalhe: "sem wasm" });
    expect((await p).erro?.codigo).toBe("sem_motor");
    expect(m.estado.estado).toBe("falhou");
  });
});
