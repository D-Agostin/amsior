// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only

import { useState } from "react";
import { useEstado } from "./estado";
import type { EstadoDoMotor } from "./motor/cliente";
import { Medicao } from "./componentes/Medicao";
import { t } from "./textos";
import { Cabecalho } from "./componentes/Cabecalho";
import { Folha } from "./componentes/Folha";
import { PainelExemplos, Trilho } from "./componentes/Lateral";
import { TabelaVariaveis } from "./componentes/TabelaVariaveis";

/** Texto da barra de estado para o estado do motor. */
export function textoDoMotor(m: EstadoDoMotor): string {
  if (m.estado === "carregando") {
    return m.etapa === "motor" && m.fracao !== null
      ? t("ui.motor.baixando", { pct: Math.round(m.fracao * 100) })
      : t(`ui.motor.${m.etapa}`);
  }
  return t(`ui.motor.${m.estado}`);
}

function Rodape() {
  const motor = useEstado((s) => s.motor);
  return (
    <footer className="rodape">
      <span className={`estado-motor estado-${motor.estado}`} role="status">
        <span aria-hidden="true">●</span> {textoDoMotor(motor)}
      </span>
      <span>{t("ui.estado.si")}</span>
      <span className="espaco" />
      <a className="rodape-link" href={t("ui.codigo.url")} target="_blank" rel="noreferrer">{t("ui.codigo.rotulo")}</a>
      <span>{t("ui.marca")} {__VERSAO__}</span>
    </footer>
  );
}

export function App() {
  const [painel, setPainel] = useState(true);
  if (window.location.hash.includes("medir")) return <Medicao />;
  return (
    <div className="app">
      <Cabecalho />
      <div className="corpo">
        <Trilho aberto={painel} alternar={() => setPainel((p) => !p)} />
        {painel ? <PainelExemplos /> : null}
        <Folha />
        <TabelaVariaveis />
      </div>
      <Rodape />
    </div>
  );
}
