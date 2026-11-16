// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Trilho de ferramentas, painel de exemplos e painel da biblioteca de fichas.

import { useMemo, useState } from "react";
import exemplos from "../dados/exemplos.json";
import { useEstado } from "../estado";
import type { Exemplo } from "../estado";
import { t } from "../textos";
import { IconeBiblioteca, IconeBusca, IconeExemplos } from "./icones";

const LISTA = exemplos as Exemplo[];
const AREAS = [...new Set(LISTA.map((e) => e.area))];

/** Busca sem acento e sem caixa: "reacao" acha "Reação". */
export function normalizar(s: string): string {
  return s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

export type Painel = "exemplos" | "biblioteca";

export function Trilho({ painel, alternar }: { painel: Painel | null; alternar: (p: Painel) => void }) {
  return (
    <nav className="trilho" aria-label={t("ui.trilho.rotulo")}>
      <button type="button" className="botao-trilho" aria-pressed={painel === "exemplos"} aria-controls="painel-exemplos"
        aria-label={t("ui.trilho.exemplos")} title={t("ui.trilho.exemplos")} onClick={() => alternar("exemplos")}>
        <IconeExemplos />
      </button>
      <button type="button" className="botao-trilho" aria-pressed={painel === "biblioteca"} aria-controls="painel-biblioteca"
        aria-label={t("ui.trilho.biblioteca")} title={t("ui.trilho.biblioteca")} onClick={() => alternar("biblioteca")}>
        <IconeBiblioteca />
      </button>
    </nav>
  );
}

export function PainelBiblioteca() {
  const [busca, setBusca] = useState("");
  const bib = useEstado((s) => s.biblioteca);
  const aberta = useEstado((s) => s.fichaAberta);
  const abrir = useEstado((s) => s.abrirFicha);
  const areas = useMemo(() => {
    const q = normalizar(busca.trim());
    return bib.areas.map((a) => {
      const fichas = a.fichas.map((id) => bib.fichas[id])
        .filter((f) => !q || normalizar(f.titulo.pt).includes(q) || normalizar(f.grupo?.pt ?? "").includes(q)
          || normalizar(t(`ui.area.${a.id}`)).includes(q));
      return { id: a.id, fichas };
    }).filter((a) => a.fichas.length > 0);
  }, [busca, bib]);

  return (
    <div className="painel" id="painel-biblioteca">
      <div className="painel-titulo">{t("ui.biblioteca.titulo")}</div>
      <label className="busca">
        <IconeBusca />
        <input type="search" aria-label={t("ui.biblioteca.buscar")} placeholder={t("ui.biblioteca.buscar")}
          value={busca} onChange={(e) => setBusca(e.target.value)} />
      </label>
      <div className="arvore">
        {areas.map((a) => (
          <div key={a.id} role="group" aria-label={t(`ui.area.${a.id}`)}>
            <div className="arvore-grupo">{t(`ui.area.${a.id}`)}<span className="contagem">{a.fichas.length}</span></div>
            {a.fichas.map((f) => (
              <button key={f.id} type="button" className="arvore-item" aria-current={aberta === f.id ? "true" : undefined}
                onClick={() => abrir(f.id)}>
                {f.titulo.pt}
              </button>
            ))}
          </div>
        ))}
        {areas.length === 0 ? <p className="nota">{t("ui.biblioteca.vazio")}</p> : null}
      </div>
      <p className="nota painel-rodape">{t("ui.biblioteca.nota")}</p>
    </div>
  );
}

export function PainelExemplos() {
  const [busca, setBusca] = useState("");
  const atual = useEstado((s) => s.exemplo);
  const carregar = useEstado((s) => s.carregarExemplo);
  const grupos = useMemo(() => {
    const q = normalizar(busca.trim());
    return AREAS.map((area) => ({
      area,
      itens: LISTA.filter((e) => e.area === area && (!q || normalizar(t(`ui.exemplo.${e.id}`)).includes(q)
        || normalizar(t(`ui.area.${area}`)).includes(q))),
    })).filter((g) => g.itens.length > 0);
  }, [busca]);

  return (
    <div className="painel" id="painel-exemplos">
      <div className="painel-titulo">{t("ui.exemplos.titulo")}</div>
      <label className="busca">
        <IconeBusca />
        <input type="search" aria-label={t("ui.exemplos.buscar")} placeholder={t("ui.exemplos.buscar")}
          value={busca} onChange={(e) => setBusca(e.target.value)} />
      </label>
      <div className="arvore">
        {grupos.map((g) => (
          <div key={g.area} role="group" aria-label={t(`ui.area.${g.area}`)}>
            <div className="arvore-grupo">{t(`ui.area.${g.area}`)}<span className="contagem">{g.itens.length}</span></div>
            {g.itens.map((e) => (
              <button key={e.id} type="button" className="arvore-item" aria-current={atual === e.id ? "true" : undefined}
                onClick={() => carregar(e)}>
                {t(`ui.exemplo.${e.id}`)}
              </button>
            ))}
          </div>
        ))}
        {grupos.length === 0 ? <p className="nota">{t("ui.exemplos.vazio")}</p> : null}
      </div>
      <p className="nota painel-rodape">{t("ui.exemplos.nota")}</p>
    </div>
  );
}
