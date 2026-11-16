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

// ---------------------------------------------------------------- biblioteca (seções 3.5 e 8.6)

export interface TextoML { pt: string; en?: string }

export type Bloco =
  | { texto: TextoML }
  | { equacao: string; destaque?: boolean; nota?: TextoML; onde?: { simbolo: string; texto: TextoML }[] }
  | { lista: TextoML[] }
  | { caixa: "resumo" | "destaque" | "atencao" | "hipoteses"; titulo?: TextoML; blocos: Bloco[] }
  | { passos: { titulo: TextoML; blocos: Bloco[] }[] }
  | { tabela: { colunas: TextoML[]; linhas: TextoML[][] } }
  | { figura: string; svg?: string; legenda?: TextoML };

export interface ExemploFicha {
  enunciado: TextoML;
  equacao: string;
  pede: string;
  simbolos: { id: string; grandeza: string }[];
  passos: boolean;
  /** exemplo de classificação (D-12): o tipo que o motor dá na variável pedida */
  tipo?: string | null;
  tem_resultado?: boolean;
}

export interface ReferenciaFicha {
  titulo: string;
  autores: string[];
  edicao: number | null;
  ano: number | null;
  licenca: string | null;
  url: string | null;
  uso: "citacao" | "adaptacao";
  adaptacao: TextoML | null;
  capitulo: string | null;
  secao: string | null;
  equacao: string | null;
  pagina: string | number | null;
  conferido: boolean;
}

export interface FichaApi {
  id: string;
  area: string;
  estado: "auto_verificada" | "verificada";
  versao: number;
  grupo: TextoML | null;
  titulo: TextoML;
  tipos: string[];
  resumo: Bloco[];
  variaveis: { simbolo: string; grandeza: string; nome?: TextoML; nota?: TextoML }[];
  secoes: { titulo: TextoML; blocos: Bloco[] }[];
  exemplos: ExemploFicha[];
  referencias: ReferenciaFicha[];
  relacionadas: string[];
}

export interface BibliotecaApi {
  areas: { id: string; fichas: string[] }[];
  fichas: Record<string, FichaApi>;
  /** tipo de equação (D-12) → ficha de Matemática que o explica */
  tipos: Record<string, string>;
}

export interface DadosIniciais {
  textos: Record<string, string>;
  glossario: { grandezas: Grandeza[] };
  biblioteca: BibliotecaApi;
}

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
