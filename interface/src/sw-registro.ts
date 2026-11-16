// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Registro do service worker (sw/sw.js): só na versão compilada, e só depois de o
// motor ficar pronto, para a cópia no cache sair do cache HTTP e não baixar
// tudo de novo na primeira visita.

let pedimosAtualizar = false;

/** Registra e avisa quando houver versão nova esperando; `atualizar` a coloca em uso e recarrega. */
export async function registrarServiceWorker(aoTerVersaoNova: (atualizar: () => void) => void): Promise<void> {
  if (import.meta.env.DEV || !("serviceWorker" in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.register("./sw.js", { scope: "./" });
    const avisar = (w: ServiceWorker) => aoTerVersaoNova(() => {
      pedimosAtualizar = true;
      w.postMessage("pular_espera");
    });
    if (reg.waiting && navigator.serviceWorker.controller) avisar(reg.waiting);
    reg.addEventListener("updatefound", () => {
      const w = reg.installing;
      w?.addEventListener("statechange", () => {
        if (w.state === "installed" && navigator.serviceWorker.controller) avisar(w);
      });
    });
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (pedimosAtualizar) window.location.reload();
    });
  } catch {
    // Sem service worker o Amsior funciona igual; só não abre sem internet.
  }
}
