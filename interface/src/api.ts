// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Cliente da API local (especificação 9.2). O token da sessão chega no fragmento
// da URL (#token=...), aberto pela janela do aplicativo, e vai em todo pedido.

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

function token(): string {
  const m = /token=([^&]+)/.exec(window.location.hash);
  if (m) {
    try { sessionStorage.setItem("amsior.token", m[1]); } catch { /* armazenamento indisponível */ }
    return m[1];
  }
  try { return sessionStorage.getItem("amsior.token") ?? ""; } catch { return ""; }
}

async function pedir<T>(metodo: "GET" | "POST" | "PUT", rota: string, corpo?: unknown): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`./api/v1/${rota}`, {
      method: metodo,
      headers: { "content-type": "application/json", "x-amsior-token": token() },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  } catch {
    throw new FalhaDaApi({ codigo: "sem_conexao", mensagem: "", chave: "ui.estado.sem_motor", detalhe: null });
  }
  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) throw new FalhaDaApi(dados as ErroApi);
  return dados as T;
}

export const api = {
  textos: () => pedir<Record<string, string>>("GET", "textos"),
  preferencias: () => pedir<Record<string, string>>("GET", "preferencias"),
  gravarPreferencias: (p: object) => pedir<Record<string, string>>("PUT", "preferencias", p),
  glossario: () => pedir<{ grandezas: Grandeza[] }>("GET", "glossario"),
  analisar: (latex: string, simbolos: SimboloPedido[]) => pedir<Analise>("POST", "analisar", { latex, simbolos }),
  isolar: (latex: string, alvo: string, simbolos: SimboloPedido[]) =>
    pedir<Isolamento>("POST", "isolar", { latex, alvo, simbolos }),
};
