// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Preferências de aparência (especificação 9.4): D ou H, claro, escuro ou seguir
// o sistema, e o nível de detalhe. Ficam no armazenamento do navegador; se ele
// faltar ou falhar, valem os padrões (D, seguir o sistema, completo).

export type Aparencia = "d" | "h";
export type Modo = "claro" | "escuro" | "sistema";
export type Nivel = "completo" | "resumido";

export interface Preferencias { aparencia: Aparencia; modo: Modo; nivel: Nivel }

export const PADRAO: Preferencias = { aparencia: "d", modo: "sistema", nivel: "completo" };
const CHAVE = "amsior.preferencias";

/** Valida o que vier (armazenamento, servidor): valor estranho vira o padrão. */
export function validarPreferencias(p: Partial<Record<keyof Preferencias, unknown>>): Preferencias {
  return {
    aparencia: p.aparencia === "h" ? "h" : "d",
    modo: p.modo === "claro" || p.modo === "escuro" ? p.modo : "sistema",
    nivel: p.nivel === "resumido" ? "resumido" : "completo",
  };
}

export function lerPreferencias(): Preferencias {
  try {
    const bruto = localStorage.getItem(CHAVE);
    return bruto ? validarPreferencias(JSON.parse(bruto) as Partial<Preferencias>) : { ...PADRAO };
  } catch {
    return { ...PADRAO };
  }
}

export function gravarPreferencias(p: Preferencias): void {
  try { localStorage.setItem(CHAVE, JSON.stringify(p)); } catch { /* sem armazenamento: só nesta sessão */ }
}

/** Modo efetivo: "sistema" segue a preferência de cor do sistema. */
export function modoEfetivo(modo: Modo, sistemaEscuro: boolean): "claro" | "escuro" {
  if (modo === "sistema") return sistemaEscuro ? "escuro" : "claro";
  return modo;
}

export function aplicar(p: Preferencias, sistemaEscuro: boolean, raiz: HTMLElement = document.documentElement): void {
  raiz.dataset.aparencia = p.aparencia;
  raiz.dataset.modo = modoEfetivo(p.modo, sistemaEscuro);
}
