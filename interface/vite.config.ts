import { readFileSync } from "node:fs";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Interface do Amsior: site estático em dist/. O motor roda no navegador, num
// trabalhador de cálculo (src/motor); antes de compilar, monte o motor com
// "python ferramentas/web/montar_motor.py" (da raiz do repositório).
const versao = /^version\s*=\s*"([^"]+)"/m.exec(readFileSync("../motor/pyproject.toml", "utf-8"))?.[1] ?? "0";

export default defineConfig({
  plugins: [react()],
  base: "./",
  define: { __VERSAO__: JSON.stringify(versao) },
  worker: { format: "es" },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false, chunkSizeWarningLimit: 2500 },
  test: { environment: "jsdom", globals: true },
});
