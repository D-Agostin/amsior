// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Estado da primeira tela: uma folha com uma equação, a tabela de símbolos e a
// resolução do alvo escolhido. Cada pedido leva um número de ordem; a resposta
// de um pedido velho (o usuário já mudou a equação) é descartada.

import { create } from "zustand";
import { api, FalhaDaApi } from "./api";
import type { EstadoDoMotor } from "./motor/cliente";
import type { Analise, BibliotecaApi, ErroApi, Grandeza, Isolamento, SimboloPedido } from "./api";
import { aplicar, gravarPreferencias, lerPreferencias } from "./preferencias";
import type { Preferencias } from "./preferencias";

export interface Exemplo {
  id: string;
  area: string;
  latex: string;
  alvo: string;
  simbolos: SimboloPedido[];
}

export interface Simb { grandeza: string | null; papel: string }


interface Estado {
  prefs: Preferencias;
  sistemaEscuro: boolean;
  glossario: Grandeza[];
  biblioteca: BibliotecaApi;
  /** Ficha aberta no centro, no lugar da folha (id), ou nenhuma. */
  fichaAberta: string | null;
  motor: EstadoDoMotor;
  /** Versão nova do site esperando: chamar põe em uso e recarrega. */
  atualizar: (() => void) | null;
  /** O navegador ofereceu instalar como aplicativo. */
  instalar: (() => void) | null;

  exemplo: string | null;
  latex: string;
  simbolos: Record<string, Simb>;
  analise: Analise | null;
  erroAnalise: ErroApi | null;
  lendo: boolean;

  alvo: string | null;
  isolamento: Isolamento | null;
  erroIsolar: ErroApi | null;
  isolando: boolean;

  definirPrefs: (p: Partial<Preferencias>) => void;
  definirSistemaEscuro: (escuro: boolean) => void;
  definirGlossario: (g: Grandeza[]) => void;
  definirBiblioteca: (b: BibliotecaApi) => void;
  abrirFicha: (id: string | null) => void;
  definirLatex: (latex: string) => void;
  carregarExemplo: (ex: Exemplo) => void;
  definirGrandeza: (id: string, grandeza: string | null) => void;
  isolar: (alvo: string) => void;
}

const ESPERA_MS = 280;
let ordemAnalise = 0;
let ordemIsolar = 0;
let temporizador: ReturnType<typeof setTimeout> | undefined;

function pedidoDeSimbolos(simbolos: Record<string, Simb>, ids?: string[]): SimboloPedido[] {
  return (ids ?? Object.keys(simbolos))
    .filter((id) => simbolos[id])
    .map((id) => ({ id, grandeza: simbolos[id].grandeza, papel: simbolos[id].papel }));
}

function comoErro(e: unknown): ErroApi {
  if (e instanceof FalhaDaApi) return e.erro;
  return { codigo: "interno", mensagem: "", chave: "ui.erro.titulo", detalhe: String(e) };
}

/** Faltam grandezas? Só isola quando todos os símbolos têm a sua (T-03, unidades). */
export function faltamGrandezas(analise: Analise | null, simbolos: Record<string, Simb>): string[] {
  if (!analise) return [];
  return analise.simbolos.filter((s) => !simbolos[s]?.grandeza);
}

export const useEstado = create<Estado>((set, get) => {
  const analisarAgora = async (depois?: () => void) => {
    const { latex, simbolos } = get();
    const ordem = ++ordemAnalise;
    if (!latex.trim()) {
      set({ analise: null, erroAnalise: null, lendo: false, isolamento: null, erroIsolar: null, alvo: null });
      return;
    }
    set({ lendo: true });
    try {
      const a = await api.analisar(latex, pedidoDeSimbolos(simbolos));
      if (ordem !== ordemAnalise) return;
      // Mantém o que o usuário escolheu para os símbolos que continuam na equação.
      const novos: Record<string, Simb> = {};
      for (const s of a.simbolos) novos[s] = get().simbolos[s] ?? { grandeza: null, papel: "variavel" };
      const alvo = get().alvo;
      set({ analise: a, erroAnalise: null, lendo: false, simbolos: novos,
            alvo: alvo && a.simbolos.includes(alvo) && a.equacao ? alvo : null });
      if (!(alvo && a.simbolos.includes(alvo))) set({ isolamento: null, erroIsolar: null });
      depois?.();
    } catch (e) {
      if (ordem !== ordemAnalise) return;
      const erro = comoErro(e);
      set({ erroAnalise: erro, lendo: false });
    }
  };

  const isolarAgora = async (alvo: string) => {
    const { latex, simbolos, analise } = get();
    if (!analise?.equacao) return;
    const ordem = ++ordemIsolar;
    set({ alvo, isolando: true, erroIsolar: null });
    try {
      const r = await api.isolar(latex, alvo, pedidoDeSimbolos(simbolos, analise.simbolos));
      if (ordem !== ordemIsolar) return;
      set({ isolamento: r, isolando: false });
    } catch (e) {
      if (ordem !== ordemIsolar) return;
      const erro = comoErro(e);
      set({ isolamento: null, erroIsolar: erro, isolando: false });
    }
  };

  const prefs = lerPreferencias();
  return {
    prefs,
    sistemaEscuro: false,
    glossario: [],
    biblioteca: { areas: [], fichas: {}, tipos: {} },
    fichaAberta: null,
    motor: { estado: "carregando", etapa: "python", fracao: null },
    atualizar: null,
    instalar: null,
    exemplo: null,
    latex: "",
    simbolos: {},
    analise: null,
    erroAnalise: null,
    lendo: false,
    alvo: null,
    isolamento: null,
    erroIsolar: null,
    isolando: false,

    definirPrefs: (p) => {
      const nova = { ...get().prefs, ...p };
      gravarPreferencias(nova);
      aplicar(nova, get().sistemaEscuro);
      set({ prefs: nova });
    },
    definirSistemaEscuro: (escuro) => {
      aplicar(get().prefs, escuro);
      set({ sistemaEscuro: escuro });
    },
    definirGlossario: (g) => set({ glossario: g }),
    definirBiblioteca: (b) => set({ biblioteca: b }),
    abrirFicha: (id) => set({ fichaAberta: id && get().biblioteca.fichas[id] ? id : null }),

    definirLatex: (latex) => {
      if (latex === get().latex) return;
      set({ latex, exemplo: null });
      clearTimeout(temporizador);
      temporizador = setTimeout(() => {
        const alvo = get().alvo;
        void analisarAgora(() => {
          // Com a mesma variável escolhida, a resolução acompanha a edição.
          if (alvo && get().alvo === alvo && faltamGrandezas(get().analise, get().simbolos).length === 0)
            void isolarAgora(alvo);
        });
      }, ESPERA_MS);
    },

    carregarExemplo: (ex) => {
      clearTimeout(temporizador);
      const simbolos: Record<string, Simb> = {};
      for (const s of ex.simbolos) simbolos[s.id] = { grandeza: s.grandeza ?? null, papel: s.papel ?? "variavel" };
      set({ exemplo: ex.id, latex: ex.latex, simbolos, alvo: null, isolamento: null, erroIsolar: null,
            fichaAberta: null });
      void analisarAgora(() => void isolarAgora(ex.alvo));
    },

    definirGrandeza: (id, grandeza) => {
      const simbolos = { ...get().simbolos, [id]: { ...(get().simbolos[id] ?? { papel: "variavel" }), grandeza } };
      set({ simbolos });
      const alvo = get().alvo;
      void analisarAgora(() => {
        if (alvo && faltamGrandezas(get().analise, get().simbolos).length === 0) void isolarAgora(alvo);
      });
    },

    isolar: (alvo) => {
      if (faltamGrandezas(get().analise, get().simbolos).length > 0) {
        set({ alvo, isolamento: null, erroIsolar: null });
        return;
      }
      void isolarAgora(alvo);
    },
  };
});
