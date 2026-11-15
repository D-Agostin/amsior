// Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
// Trilho de ferramentas e painel de exemplos (a biblioteca completa vem depois).

import { useMemo, useState } from "react";
import exemplos from "../dados/exemplos.json";
import { useEstado } from "../estado";
import type { Exemplo } from "../estado";
import { t } from "../textos";
import { IconeBusca, IconeExemplos } from "./icones";

const LISTA = exemplos as Exemplo[];
const AREAS = [...new Set(LISTA.map((e) => e.area))];

/** Busca sem acento e sem caixa: "reacao" acha "Reação". */
export function normalizar(s: string): string {
  return s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

export function Trilho({ aberto, alternar }: { aberto: boolean; alternar: () => void }) {
  return (
    <nav className="trilho" aria-label={t("ui.trilho.rotulo")}>
      <button type="button" className="botao-trilho" aria-pressed={aberto} aria-controls="painel-exemplos"
        aria-label={t("ui.trilho.exemplos")} title={t("ui.trilho.exemplos")} onClick={alternar}>
        <IconeExemplos />
      </button>
    </nav>
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
