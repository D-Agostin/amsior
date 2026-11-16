// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Medição da fase 1C (endereço com #medir): quanto o navegador baixou, quanto o
// motor levou para partir e quanto leva para isolar cada exemplo, nesta máquina.

import { useEffect, useState } from "react";
import { motor } from "../api";
import exemplos from "../dados/exemplos.json";
import { useEstado } from "../estado";
import type { Exemplo } from "../estado";
import type { Isolamento } from "../api";
import { textoDoMotor } from "../App";
import { t } from "../textos";

interface Linha { id: string; estado: string; passos: number; motorMs: number; totalMs: number }

const mb = (b: number) => (b / 1048576).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
const s1 = (ms: number) => (ms / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 2 });

export function Medicao() {
  const estado = useEstado((s) => s.motor);
  const [linhas, setLinhas] = useState<Linha[]>([]);
  const [fim, setFim] = useState(false);
  const [aberturaMs] = useState(() => performance.now());

  useEffect(() => {
    let vivo = true;
    void (async () => {
      for (const ex of exemplos as Exemplo[]) {
        const t0 = performance.now();
        const r = await motor.pedir("isolar", { latex: ex.latex, alvo: ex.alvo, simbolos: ex.simbolos });
        const ok = r.ok as Isolamento | undefined;
        const linha: Linha = { id: ex.id, estado: ok?.estado ?? String((r.erro as { codigo?: string } | undefined)?.codigo),
          passos: ok ? ok.ramos.reduce((n, ramo) => n + ramo.passos.length, 0) : 0,
          motorMs: r.ms, totalMs: performance.now() - t0 };
        if (!vivo) return;
        setLinhas((ls) => [...ls, linha]);
      }
      if (vivo) setFim(true);
    })();
    return () => { vivo = false; };
  }, []);

  const partida = motor.partida;
  // transferSize é 0 quando o arquivo vem do cache do navegador: esses contam à parte.
  const baixados = partida?.recursos.reduce((n, r) => n + r.transferidos, 0) ?? 0;
  const doCache = partida?.recursos.reduce((n, r) => n + (r.transferidos === 0 ? r.bytes : 0), 0) ?? 0;
  const relatorio = {
    navegador: navigator.userAgent, nucleos: navigator.hardwareConcurrency,
    partida_ms: partida ? Math.round(partida.ms) : null, baixados_bytes: baixados, cache_bytes: doCache,
    recursos: partida?.recursos.map((r) => ({ ...r, ms: Math.round(r.ms) })),
    isolar: linhas.map((l) => ({ ...l, motorMs: Math.round(l.motorMs), totalMs: Math.round(l.totalMs) })),
  };

  return (
    <main className="medicao">
      <h2>{t("ui.medir.titulo")}</h2>
      <p className="nota">{t("ui.medir.nota")}</p>
      <dl className="medicao-resumo">
        <dt>{t("ui.medir.estado")}</dt><dd role="status">{textoDoMotor(estado)}</dd>
        <dt>{t("ui.medir.partida")}</dt><dd>{partida ? `${s1(partida.ms)} s` : "—"}</dd>
        <dt>{t("ui.medir.baixados")}</dt><dd>{partida ? `${mb(baixados)} MB` : "—"}</dd>
        <dt>{t("ui.medir.do_cache")}</dt><dd>{partida ? `${mb(doCache)} MB` : "—"}</dd>
        <dt>{t("ui.medir.aberta_em")}</dt><dd>{`${s1(aberturaMs)} s`}</dd>
      </dl>
      <table className="tabela medicao-tabela">
        <thead><tr>
          <th scope="col">{t("ui.medir.col.exemplo")}</th><th scope="col">{t("ui.medir.col.estado")}</th>
          <th scope="col">{t("ui.medir.col.passos")}</th><th scope="col">{t("ui.medir.col.motor")}</th>
          <th scope="col">{t("ui.medir.col.total")}</th>
        </tr></thead>
        <tbody>
          {linhas.map((l) => (
            <tr key={l.id}>
              <th scope="row">{t(`ui.exemplo.${l.id}`)}</th><td>{l.estado}</td><td>{l.passos}</td>
              <td>{`${s1(l.motorMs)} s`}</td><td>{`${s1(l.totalMs)} s`}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {fim ? (
        <button type="button" className="botao-simbolo medicao-copiar"
          onClick={() => void navigator.clipboard?.writeText(JSON.stringify(relatorio, null, 2))}>
          {t("ui.medir.copiar")}
        </button>
      ) : <p className="nota">{t("ui.medir.rodando", { n: linhas.length, total: (exemplos as Exemplo[]).length })}</p>}
      <pre className="medicao-json" data-pronto={fim ? "sim" : undefined}>{fim ? JSON.stringify(relatorio) : ""}</pre>
    </main>
  );
}
