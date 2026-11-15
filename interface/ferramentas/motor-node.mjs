// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Roda o motor do navegador (Pyodide + motor-<hash>.zip) no Node, para testes e
// para comparar com o Python nativo na integração contínua.
//
//   node ferramentas/motor-node.mjs pedidos.json > respostas.json
//
// pedidos.json: [{"rota": "isolar", "dados": {...}}, ...]
// Saída: {"partida_ms", "respostas": [{"ms", "resposta"}]}
import { readFileSync } from "node:fs";
import { loadPyodide } from "pyodide";

const manifesto = JSON.parse(readFileSync("public/motor/motor.json", "utf-8"));
const pedidos = JSON.parse(readFileSync(process.argv[2], "utf-8"));

const t0 = performance.now();
const pyodide = await loadPyodide({ stdout: () => {}, stderr: (t) => process.stderr.write(t + "\n") });
const site = pyodide.runPython("import site; site.getsitepackages()[0]");
pyodide.unpackArchive(new Uint8Array(readFileSync(`public/motor/${manifesto.arquivo}`)), "zip", { extractDir: site });
pyodide.runPython(readFileSync("src/motor/partida.py", "utf-8"));
const chamar = pyodide.globals.get("chamar");
const partida_ms = performance.now() - t0;

const respostas = [];
for (const p of pedidos) {
  const t = performance.now();
  const resposta = JSON.parse(chamar(p.rota, JSON.stringify(p.dados)));
  respostas.push({ ms: performance.now() - t, resposta });
}
process.stdout.write(JSON.stringify({ partida_ms, python: pyodide.runPython("import sys; sys.version"), respostas }));
