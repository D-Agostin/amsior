// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Service worker: guarda o site inteiro (interface, Python e motor) para o Amsior
// abrir e calcular sem internet depois da primeira visita (especificação 2 e 9.1).
//
// A compilação (vite.config.ts) troca __VERSAO__ e __ARQUIVOS__ pela lista de
// arquivos com o hash do conteúdo de cada um. Cada arquivo fica no cache com a
// chave "endereço?v=hash": numa versão nova, o que não mudou é copiado do cache
// velho e só o que mudou é baixado. A versão nova espera em segundo plano e
// entra quando o usuário pede para atualizar ou na próxima abertura.

const VERSAO = "__VERSAO__";
/** @type {{url: string, hash: string}[]} */
const ARQUIVOS = __ARQUIVOS__;
const PREFIXO = "amsior-";
const CACHE = PREFIXO + VERSAO;
const BASE = new URL("./", self.location.href).href;

const hashPorEndereco = new Map(ARQUIVOS.map((a) => [new URL(a.url, BASE).href, a.hash]));
const chave = (endereco, hash) => `${endereco}?v=${hash}`;

async function sha256(buffer) {
  const d = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Baixa e confere o hash; se o cache HTTP devolver uma cópia velha, busca de novo na rede. */
async function baixar(endereco, hash) {
  for (const modo of ["default", "reload"]) {
    const r = await fetch(endereco, { cache: modo });
    if (!r.ok) throw new Error(`${endereco}: ${r.status}`);
    const corpo = await r.clone().arrayBuffer();
    if ((await sha256(corpo)).startsWith(hash)) return r;
  }
  throw new Error(`${endereco}: conteúdo diferente do esperado`);
}

self.addEventListener("install", (evento) => {
  evento.waitUntil((async () => {
    const novo = await caches.open(CACHE);
    const velhos = (await caches.keys()).filter((n) => n.startsWith(PREFIXO) && n !== CACHE);
    for (const [endereco, hash] of hashPorEndereco) {
      const k = chave(endereco, hash);
      if (await novo.match(k)) continue;
      let resposta;
      for (const v of velhos) {
        resposta = await (await caches.open(v)).match(k);
        if (resposta) break;
      }
      await novo.put(k, resposta ?? (await baixar(endereco, hash)));
    }
  })());
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil((async () => {
    for (const n of await caches.keys()) {
      if (n.startsWith(PREFIXO) && n !== CACHE) await caches.delete(n);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("message", (evento) => {
  if (evento.data === "pular_espera") self.skipWaiting();
});

self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;
  if (pedido.method !== "GET" || !pedido.url.startsWith(BASE)) return;
  const url = new URL(pedido.url);
  url.search = "";
  url.hash = "";
  let endereco = url.href;
  // Qualquer navegação dentro do site abre a página (index.html).
  if (pedido.mode === "navigate") endereco = new URL("index.html", BASE).href;
  const hash = hashPorEndereco.get(endereco);
  if (!hash) return;
  evento.respondWith((async () => {
    const guardada = await (await caches.open(CACHE)).match(chave(endereco, hash));
    return guardada ?? fetch(pedido);
  })());
});
