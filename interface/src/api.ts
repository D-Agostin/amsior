// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Pedidos ao motor (especificação 9.2). O motor roda no próprio navegador, num
// trabalhador de cálculo (motor/trabalhador.ts); nada sai do dispositivo (T-07).

import { Motor } from "./motor/cliente";
import type { ErroMotor } from "./motor/cliente";
import { t } from "./textos";

export interface Grandeza { id: string; nome: string; unidade: string; suposicoes: string[] }

export interface Tipo { chave: string; texto: string }

export interface Analise {
  latex: string;
  equacao: boolean;
  simbolos: string[];
  novos: string[];
  tipos: Record<string, Tipo>;
}

export interface Selo { estado: string; metodo: string; sob_hipotese: boolean; hipoteses: string[] }

export interface PassoApi {
  indice: number;
  regra: string;
  latex: string;
  justificativa: string;
  fundivel: boolean;
  condicoes: string[];
  selo: Selo | null;
}

export interface RamoApi {
  rotulo: string;
  passos: PassoApi[];
  resultado: string;
  hipoteses: string[];
  validade: string[];
}

export interface Isolamento {
  estado: "com_passos" | "sem_passos" | "recusado";
  alvo: string;
  tipo: Tipo | null;
  ramos: RamoApi[];
  descartados: string[];
  sem_passos: string[];
  motivo: { chave: string; texto: string } | null;
}

export interface ErroApi { codigo: string; mensagem: string; chave: string; detalhe: unknown }

export class FalhaDaApi extends Error {
  constructor(public erro: ErroApi) {
    super(erro.mensagem);
  }
}

export interface SimboloPedido { id: string; grandeza?: string | null; papel?: string }

export interface DadosIniciais { textos: Record<string, string>; glossario: { grandezas: Grandeza[] } }

const BASE = new URL("./", document.baseURI).href;

/** O motor; só começa a carregar quando main.tsx chama motor.iniciar(). */
export const motor = new Motor(BASE, () =>
  new Worker(new URL("./motor/trabalhador.ts", import.meta.url), { type: "module", name: "amsior-motor" }));

async function pedir<T>(rota: string, dados: unknown, chave?: string): Promise<T> {
  const r = await motor.pedir(rota, dados, { chave });
  if (r.erro) {
    const erro: ErroMotor = { ...r.erro };
    if (!erro.mensagem && erro.chave.startsWith("ui.")) {
      erro.mensagem = t(erro.chave, (erro.detalhe ?? {}) as Record<string, string | number>);
    }
    throw new FalhaDaApi(erro);
  }
  return r.ok as T;
}

export const api = {
  /** Textos e glossário prontos no site: a tela abre antes de o motor terminar de carregar. */
  dados: async (): Promise<DadosIniciais> => {
    const r = await fetch(`${BASE}motor/dados.json`);
    if (!r.ok) throw new FalhaDaApi({ codigo: "sem_motor", mensagem: "", chave: "ui.estado.falhou", detalhe: r.status });
    return (await r.json()) as DadosIniciais;
  },
  analisar: (latex: string, simbolos: SimboloPedido[]) => pedir<Analise>("analisar", { latex, simbolos }, "analisar"),
  isolar: (latex: string, alvo: string, simbolos: SimboloPedido[]) =>
    pedir<Isolamento>("isolar", { latex, alvo, simbolos }, "isolar"),
};
