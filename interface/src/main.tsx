// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Partida da interface: textos e glossário vêm do motor antes da primeira tela.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/stix-two-text/400.css";
import "@fontsource/stix-two-text/400-italic.css";
import "@fontsource/stix-two-text/500.css";
import "@fontsource/atkinson-hyperlegible-next/400.css";
import "@fontsource/atkinson-hyperlegible-next/500.css";
import "@fontsource/atkinson-hyperlegible-next/600.css";
import "@fontsource/atkinson-hyperlegible-mono/400.css";
import "@fontsource/atkinson-hyperlegible-mono/500.css";
import "katex/dist/katex.min.css";
import "./estilo/tokens.css";
import "./estilo/base.css";
import { api, motor } from "./api";
import { App } from "./App";
import { useEstado } from "./estado";
import { aplicar } from "./preferencias";
import { registrarServiceWorker } from "./sw-registro";
import { carregarTextos, t } from "./textos";

const raiz = createRoot(document.getElementById("raiz")!);

// Aparência antes de tudo, para não piscar no tema errado.
const escuro = window.matchMedia?.("(prefers-color-scheme: dark)");
useEstado.getState().definirSistemaEscuro(Boolean(escuro?.matches));
escuro?.addEventListener("change", (e) => useEstado.getState().definirSistemaEscuro(e.matches));
aplicar(useEstado.getState().prefs, Boolean(escuro?.matches));

// Impressão e PDF saem sempre na aparência D, modo claro (especificação 9.4).
window.addEventListener("beforeprint", () => aplicar({ ...useEstado.getState().prefs, aparencia: "d", modo: "claro" }, false));
window.addEventListener("afterprint", () => aplicar(useEstado.getState().prefs, useEstado.getState().sistemaEscuro));

// As fontes das duas aparências são locais: carregá-las logo evita a troca de
// fonte no meio da edição quando o usuário muda de D para H.
function precarregarFontes(): void {
  const familias = ['400 1em "Inter"', '500 1em "Inter"', '600 1em "Inter"', '400 1em "STIX Two Text"',
    'italic 400 1em "STIX Two Text"', '400 1em "Atkinson Hyperlegible Next"', '500 1em "Atkinson Hyperlegible Next"',
    '600 1em "Atkinson Hyperlegible Next"', '400 1em "Atkinson Hyperlegible Mono"'];
  for (const f of familias) void document.fonts?.load(f).catch(() => undefined);
}

// Instalar como aplicativo: o navegador oferece; o botão fica na tela "Sobre".
interface PedidoDeInstalacao extends Event { prompt: () => Promise<void> }
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  const pedido = e as PedidoDeInstalacao;
  useEstado.setState({ instalar: () => { void pedido.prompt(); useEstado.setState({ instalar: null }); } });
});
window.addEventListener("appinstalled", () => useEstado.setState({ instalar: null }));

async function partir(): Promise<void> {
  precarregarFontes();
  // O motor começa a carregar já; a tela abre com os textos e o glossário do site
  // e os pedidos esperam na fila até o motor ficar pronto.
  let registrado = false;
  motor.ouvir((e) => {
    useEstado.setState({ motor: e });
    if (e.estado === "pronto" && !registrado) {
      registrado = true;
      void registrarServiceWorker((atualizar) => useEstado.setState({ atualizar }));
    }
  });
  motor.iniciar();
  try {
    const dados = await api.dados();
    carregarTextos(dados.textos);
    useEstado.getState().definirGlossario(dados.glossario.grandezas);
    if (dados.biblioteca) useEstado.getState().definirBiblioteca(dados.biblioteca);
    raiz.render(<StrictMode><App /></StrictMode>);
  } catch {
    raiz.render(<p className="falha-partida" role="alert">{t("ui.estado.falhou")}</p>);
  }
}

void partir();
