// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Prepara public/ para a compilação. Tudo é servido pelo próprio site, sem CDN
// (T-07: nenhum pedido de rede sai para terceiros):
// - fontes e sons do MathLive (que buscaria em CDN por padrão);
// - o Pyodide (Python em WebAssembly), copiado do pacote npm;
// - o motor (public/motor), montado à parte por ferramentas/web/montar_motor.py.
import { cpSync, existsSync, mkdirSync } from "node:fs";

mkdirSync("public/mathlive", { recursive: true });
cpSync("node_modules/mathlive/fonts", "public/mathlive/fonts", { recursive: true });
cpSync("node_modules/mathlive/sounds", "public/mathlive/sounds", { recursive: true });

mkdirSync("public/pyodide", { recursive: true });
for (const f of ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]) {
  cpSync(`node_modules/pyodide/${f}`, `public/pyodide/${f}`);
}
console.log("MathLive e Pyodide copiados para public/");

if (!existsSync("public/motor/motor.json")) {
  console.warn("Aviso: public/motor não existe. Rode, da raiz do repositório: python ferramentas/web/montar_motor.py");
}
