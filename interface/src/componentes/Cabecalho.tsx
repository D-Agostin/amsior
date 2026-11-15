// Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.

import { useEstado } from "../estado";
import { modoEfetivo } from "../preferencias";
import { t } from "../textos";
import { Configuracoes } from "./Configuracoes";
import { IconeAjustes, IconeLua, IconeSol } from "./icones";

function Marca() {
  const nome = t("ui.marca");
  return (
    <span className="marca" aria-label={nome}>
      <span aria-hidden="true">{nome.slice(0, -1)}<span className="marca-r">{nome.slice(-1)}</span></span>
    </span>
  );
}

export function Cabecalho() {
  const prefs = useEstado((s) => s.prefs);
  const sistemaEscuro = useEstado((s) => s.sistemaEscuro);
  const exemplo = useEstado((s) => s.exemplo);
  const definirPrefs = useEstado((s) => s.definirPrefs);
  const atual = modoEfetivo(prefs.modo, sistemaEscuro);
  const outro = atual === "claro" ? "escuro" : "claro";

  return (
    <header className="cabecalho">
      <div className="cabecalho-marca"><Marca /></div>
      <div className="cabecalho-folha" aria-live="polite">
        {exemplo ? t(`ui.exemplo.${exemplo}`) : null}
      </div>
      <div className="cabecalho-acoes">
        <div role="group" aria-label={t("ui.nivel.rotulo")} className="segmentado" title={t("ui.nivel.dica")}>
          {(["completo", "resumido"] as const).map((n) => (
            <button key={n} type="button" aria-pressed={prefs.nivel === n} onClick={() => definirPrefs({ nivel: n })}>
              {t(`ui.nivel.${n}`)}
            </button>
          ))}
        </div>
        <button type="button" className="botao-icone" aria-label={t("ui.modo.trocar", { modo: t(`ui.modo.${outro}`) })}
          title={t("ui.modo.trocar", { modo: t(`ui.modo.${outro}`) })} onClick={() => definirPrefs({ modo: outro })}>
          {atual === "claro" ? <IconeLua /> : <IconeSol />}
        </button>
        <button type="button" className="botao-icone" aria-label={t("ui.config.abrir")} title={t("ui.config.abrir")}
          aria-haspopup="dialog" popoverTarget="configuracoes">
          <IconeAjustes />
        </button>
      </div>
      <Configuracoes />
    </header>
  );
}
