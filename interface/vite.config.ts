import { readFileSync } from "node:fs";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Interface do Amsior: compilada para dist/ e servida pelo servidor local (amsior.api).
// Em desenvolvimento, `npm run dev` repassa /api ao servidor em 127.0.0.1:8765
// (python -m amsior.janela --servidor --porta 8765 --token dev).
const versao = /^version\s*=\s*"([^"]+)"/m.exec(readFileSync("../motor/pyproject.toml", "utf-8"))?.[1] ?? "0";

export default defineConfig({
  plugins: [react()],
  base: "./",
  define: { __VERSAO__: JSON.stringify(versao) },
  server: { proxy: { "/api": "http://127.0.0.1:8765" } },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false, chunkSizeWarningLimit: 2500 },
  test: { environment: "jsdom", globals: true },
});
