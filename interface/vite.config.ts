import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { defineConfig } from "vitest/config";
import type { Plugin } from "vite";
import react from "@vitejs/plugin-react";

// Interface do Amsior: site estático em dist/. O motor roda no navegador, num
// trabalhador de cálculo (src/motor); antes de compilar, monte o motor com
// "python ferramentas/web/montar_motor.py" (da raiz do repositório).
const versao = /^version\s*=\s*"([^"]+)"/m.exec(readFileSync("../motor/pyproject.toml", "utf-8"))?.[1] ?? "0";

/** O que fica fora do cache de uso sem internet: formatos de fonte que o navegador não usa e sons. */
const FORA_DO_CACHE = /\.(ttf|woff|map)$|^mathlive\/sounds\//;

function listar(pasta: string): string[] {
  return readdirSync(pasta).flatMap((n) => {
    const caminho = join(pasta, n);
    return statSync(caminho).isDirectory() ? listar(caminho) : [caminho];
  });
}

/** Gera dist/sw.js a partir de sw/sw.js, com a lista de arquivos e o hash de cada um. */
function serviceWorker(): Plugin {
  return {
    name: "amsior-service-worker",
    apply: "build",
    closeBundle() {
      const arquivos = listar("dist")
        .map((c) => relative("dist", c).split(sep).join("/"))
        .filter((u) => u !== "sw.js" && !FORA_DO_CACHE.test(u))
        .sort()
        .map((url) => ({ url, hash: createHash("sha256").update(readFileSync(join("dist", url))).digest("hex").slice(0, 16) }));
      const versaoSw = createHash("sha256").update(JSON.stringify(arquivos)).digest("hex").slice(0, 12);
      const modelo = readFileSync("sw/sw.js", "utf-8");
      const marcas = ['const VERSAO = "__VERSAO__";', "const ARQUIVOS = __ARQUIVOS__;"];
      if (!marcas.every((m) => modelo.split(m).length === 2)) throw new Error("sw/sw.js: marcas de VERSAO e ARQUIVOS não encontradas");
      writeFileSync("dist/sw.js", modelo
        .replace(marcas[0], `const VERSAO = ${JSON.stringify(versaoSw)};`)
        .replace(marcas[1], `const ARQUIVOS = ${JSON.stringify(arquivos)};`));
      console.log(`sw.js: ${arquivos.length} arquivos no cache sem internet (versão ${versaoSw})`);
    },
  };
}

export default defineConfig({
  plugins: [react(), serviceWorker()],
  base: "./",
  define: { __VERSAO__: JSON.stringify(versao) },
  worker: { format: "es" },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false, chunkSizeWarningLimit: 2500 },
  test: { environment: "jsdom", globals: true },
});
