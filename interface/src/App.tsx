// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only

import { useState } from "react";
import { useEstado } from "./estado";
import { t } from "./textos";
import { Cabecalho } from "./componentes/Cabecalho";
import { Folha } from "./componentes/Folha";
import { PainelExemplos, Trilho } from "./componentes/Lateral";
import { TabelaVariaveis } from "./componentes/TabelaVariaveis";

function Rodape() {
  const motor = useEstado((s) => s.motor);
  return (
    <footer className="rodape">
      <span className={`estado-motor estado-${motor}`} role="status">
        <span aria-hidden="true">●</span> {t(`ui.estado.${motor}`)}
      </span>
      <span>{t("ui.estado.si")}</span>
      <span className="espaco" />
      <span>{t("ui.marca")} {__VERSAO__}</span>
    </footer>
  );
}

export function App() {
  const [painel, setPainel] = useState(true);
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
