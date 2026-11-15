// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Trabalhador de cálculo (T-06): carrega o Pyodide e o motor do Amsior fora da
// linha de execução da página e responde a um pedido por vez. Se um cálculo
// passar do tempo, a página encerra este trabalhador e cria outro.
//
// Tudo vem do próprio site (T-07): o Pyodide de ./pyodide/ e o motor de ./motor/.

/// <reference lib="webworker" />
import type { PyodideAPI } from "pyodide";
import partida from "./partida.py?raw";
import type { DoTrabalhador, Manifesto, ParaTrabalhador, Recurso } from "./protocolo";

declare const self: DedicatedWorkerGlobalScope;

let chamar: ((rota: string, dados: string) => string) | null = null;

function enviar(m: DoTrabalhador): void {
  self.postMessage(m);
}

/** Baixa um arquivo avisando o progresso (o motor tem alguns MB). */
async function baixar(url: string, etapa: "motor"): Promise<Uint8Array> {
  const r = await fetch(url);
  if (!r.ok || !r.body) throw new Error(`${url}: ${r.status}`);
  const total = Number(r.headers.get("content-length")) || 0;
  const partes: Uint8Array[] = [];
  let baixado = 0;
  const leitor = r.body.getReader();
  for (;;) {
    const { done, value } = await leitor.read();
    if (done) break;
    partes.push(value);
    baixado += value.length;
    enviar({ tipo: "progresso", etapa, baixado, total });
  }
  const tudo = new Uint8Array(baixado);
  let pos = 0;
  for (const p of partes) { tudo.set(p, pos); pos += p.length; }
  return tudo;
}

async function iniciar(base: string): Promise<void> {
  const t0 = performance.now();
  enviar({ tipo: "progresso", etapa: "python" });
  const { loadPyodide } = (await import(/* @vite-ignore */ `${base}pyodide/pyodide.mjs`)) as
    { loadPyodide: (o: { indexURL: string; stdout: () => void }) => Promise<PyodideAPI> };
  const py = await loadPyodide({ indexURL: `${base}pyodide/`, stdout: () => {} });

  const manifesto = (await (await fetch(`${base}motor/motor.json`)).json()) as Manifesto;
  const zip = await baixar(`${base}motor/${manifesto.arquivo}`, "motor");
  enviar({ tipo: "progresso", etapa: "iniciando" });
  const site = py.runPython("import site; site.getsitepackages()[0]") as string;
  py.unpackArchive(zip, "zip", { extractDir: site });
  py.runPython(partida);
  const f = py.globals.get("chamar") as (rota: string, dados: string) => string;
  chamar = f;
  const recursos: Recurso[] = (performance.getEntriesByType("resource") as PerformanceResourceTiming[])
    .map((r) => ({ nome: r.name.split("/").pop() ?? r.name, bytes: r.decodedBodySize || r.encodedBodySize,
      transferidos: r.transferSize, ms: r.duration }));
  enviar({ tipo: "pronto", ms: performance.now() - t0, recursos });
}

self.onmessage = (e: MessageEvent<ParaTrabalhador>) => {
  const m = e.data;
  if (m.tipo === "iniciar") {
    iniciar(m.base).catch((err: unknown) => enviar({ tipo: "falhou", detalhe: String(err) }));
    return;
  }
  const t = performance.now();
  let resposta: { ok?: unknown; erro?: unknown };
  try {
    if (!chamar) throw new Error("motor ainda não iniciado");
    resposta = JSON.parse(chamar(m.rota, JSON.stringify(m.dados))) as typeof resposta;
  } catch (err) {
    resposta = { erro: { codigo: "interno", mensagem: "", chave: "api.erro_interno", detalhe: String(err) } };
  }
  enviar({ tipo: "resposta", id: m.id, ms: performance.now() - t, resposta });
};
