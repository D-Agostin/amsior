// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Ícones de traço, desenhados em 24×24 e herdando a cor do texto.

const base = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };

export const IconeSol = () => (
  <svg {...base} width={16} height={16}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
);
export const IconeLua = () => (
  <svg {...base} width={16} height={16}><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" /></svg>
);
export const IconeAjustes = () => (
  <svg {...base} width={16} height={16}><path d="M4 7h10M18 7h2M4 17h4M12 17h8" /><circle cx="16" cy="7" r="2" /><circle cx="10" cy="17" r="2" /></svg>
);
export const IconeExemplos = () => (
  <svg {...base}><path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H10v16H5.5A1.5 1.5 0 0 1 4 18.5zM10 4h4v16h-4zM14.5 5l4-1 2 15.5-4 1z" /></svg>
);
export const IconeBusca = () => (
  <svg {...base} width={14} height={14} strokeWidth={2}><circle cx="11" cy="11" r="6.5" /><path d="M20 20l-4-4" /></svg>
);
export const IconeFechar = () => (
  <svg {...base} width={16} height={16}><path d="M6 6l12 12M18 6L6 18" /></svg>
);
