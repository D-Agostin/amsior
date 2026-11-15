// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Resolução (especificação 4.3 e 9.4): grade # | Equação | Justificativa |
// Certificado. Só chegam aqui passos com certificado (T-02); o resultado traz
// as condições de validade e as hipóteses sob as quais vale.

import type { PassoApi, RamoApi, Selo as SeloApi } from "../api";
import { faltamGrandezas, useEstado } from "../estado";
import { Mat, Texto } from "../mat";
import { contar, resumir } from "../resumir";
import { t } from "../textos";

/** Hipótese do motor: LaTeX puro ou texto com trechos \( \). */
function Hipotese({ h }: { h: string }) {
  return h.includes("\\(") ? <Texto texto={h} /> : <Mat tex={h} />;
}

function Lista({ itens }: { itens: string[] }) {
  return (
    <span className="lista-mat">
      {itens.map((c, i) => <span key={i} className="item-mat"><Hipotese h={c} /></span>)}
    </span>
  );
}

export function Selo({ selo }: { selo: SeloApi | null }) {
  if (!selo || selo.estado !== "aprovado") {
    return <span className="selo selo-erro">{t("ui.selo.reprovado")}</span>;
  }
  const metodo = selo.metodo === "simbolico" ? "simbolico" : "numerico";
  return (
    <span className="selos">
      <span className="selo selo-ok" title={t(`ui.selo.dica.${metodo}`)}>
        <span aria-hidden="true">✓</span> {t(`ui.selo.${metodo}`)}
      </span>
      {selo.sob_hipotese ? (
        <span className="selo selo-aviso" title={t("ui.selo.dica.hipotese")}>{t("ui.selo.hipotese")}</span>
      ) : null}
    </span>
  );
}

function Linha({ passo }: { passo: PassoApi }) {
  return (
    <div role="row" className="passo">
      <span role="cell" className="passo-num">{passo.indice}</span>
      <span role="cell" className="passo-eq"><Mat tex={passo.latex} exibicao /></span>
      <span role="cell" className="passo-just">
        <span><Texto texto={passo.justificativa} /></span>
        {passo.condicoes.length > 0 ? (
          <span className="passo-cond"><span className="rotulo">{t("ui.res.exige")}</span><Lista itens={passo.condicoes} /></span>
        ) : null}
      </span>
      <span role="cell" className="passo-cert"><Selo selo={passo.selo} /></span>
    </div>
  );
}

function Ramo({ ramo, dada, varios }: { ramo: RamoApi; dada: string; varios: boolean }) {
  const nivel = useEstado((s) => s.prefs.nivel);
  const { visiveis, ocultos } = resumir(ramo.passos, nivel);
  return (
    <div className="ramo">
      {varios && ramo.rotulo ? <div className="ramo-titulo">{ramo.rotulo}</div> : null}
      <div role="table" className="passos" aria-label={ramo.rotulo || t("ui.res.titulo")}>
        <div role="row" className="passo passo-cabeca">
          <span role="columnheader">{t("ui.res.col.num")}</span>
          <span role="columnheader">{t("ui.res.col.eq")}</span>
          <span role="columnheader">{t("ui.res.col.just")}</span>
          <span role="columnheader">{t("ui.res.col.cert")}</span>
        </div>
        <div role="row" className="passo passo-dada">
          <span role="cell" className="passo-num">0</span>
          <span role="cell" className="passo-eq"><Mat tex={dada} exibicao /></span>
          <span role="cell" className="passo-just">{ramo.passos.length ? t("ui.res.dada") : t("ui.res.ja_isolada")}</span>
          <span role="cell" className="passo-cert" />
        </div>
        {visiveis.map((p) => <Linha key={p.indice} passo={p} />)}
      </div>
      {ocultos > 0 ? <p className="nota ramo-ocultos">{t("ui.res.ocultos", { n: ocultos })}</p> : null}
      <div className="resultado">
        <span className="resultado-rotulo">{t("ui.res.resultado")}</span>
        <Mat tex={ramo.resultado} exibicao className="resultado-eq" />
        {ramo.validade.length > 0 ? (
          <span className="resultado-extra"><span className="rotulo">{t("ui.res.valido_se")}</span><Lista itens={ramo.validade} /></span>
        ) : null}
        {ramo.hipoteses.length > 0 ? (
          <span className="resultado-extra"><span className="rotulo">{t("ui.res.sob_hipoteses")}</span><Lista itens={ramo.hipoteses} /></span>
        ) : null}
      </div>
    </div>
  );
}

export function Resolucao() {
  const alvo = useEstado((s) => s.alvo);
  const analise = useEstado((s) => s.analise);
  const simbolos = useEstado((s) => s.simbolos);
  const r = useEstado((s) => s.isolamento);
  const erro = useEstado((s) => s.erroIsolar);
  const isolando = useEstado((s) => s.isolando);
  if (!alvo || !analise?.equacao) return null;

  const faltam = faltamGrandezas(analise, simbolos);
  const tipo = r?.alvo === alvo ? r.tipo : analise.tipos[alvo] ?? null;
  const n = r ? contar(r.ramos) : null;

  return (
    <section className="cartao resolucao" aria-label={t("ui.res.titulo")} aria-busy={isolando}>
      <div className="resolucao-cabeca">
        <span className="num-celula">[2]</span>
        <span className="resolucao-titulo">{t("ui.res.isolar")}</span>
        <Mat tex={alvo} />
        <span className="espaco" />
        {n && r?.estado === "com_passos" && !isolando ? (
          <span className="resolucao-contagem">
            {r.ramos.length > 1
              ? t("ui.res.resumo_ramos", { ramos: r.ramos.length, passos: n.passos, verificados: n.verificados })
              : t("ui.res.resumo", { passos: n.passos, verificados: n.verificados })}
          </span>
        ) : null}
      </div>
      {tipo ? (
        <div className="adendo-tipo"><span className="rotulo">{t("ui.res.tipo")}</span><span><Texto texto={tipo.texto} /></span></div>
      ) : null}

      {faltam.length > 0 ? (
        <p className="aviso-faixa">{t("ui.var.falta")}</p>
      ) : isolando && !r ? (
        <p className="nota resolucao-estado">{t("ui.res.calculando")}</p>
      ) : erro ? (
        <p className="erro-faixa">{erro.mensagem ? <Texto texto={erro.mensagem} /> : t(erro.chave)}</p>
      ) : r ? (
        <div className={isolando ? "esmaecido" : undefined}>
          {r.estado === "com_passos" && r.ramos.map((ramo, i) => (
            <Ramo key={i} ramo={ramo} dada={analise.latex} varios={r.ramos.length > 1} />
          ))}
          {r.estado === "sem_passos" ? (
            <div className="sem-passos">
              <p className="aviso-faixa">{t("ui.res.sem_passos")}</p>
              <div className="resultado">
                <span className="resultado-rotulo">{t("ui.res.sem_passos_titulo")}</span>
                <Lista itens={r.sem_passos} />
              </div>
            </div>
          ) : null}
          {r.estado === "recusado" ? (
            <p className="erro-faixa">
              <Texto texto={t("ui.res.recusado", { alvo })} />{" "}
              {r.motivo ? <Texto texto={r.motivo.texto} /> : null}
            </p>
          ) : null}
          {r.descartados.length > 0 ? (
            <div className="descartados">
              <span className="rotulo">{t("ui.res.descartados")}</span>
              {r.descartados.map((d, i) => <span key={i}><Texto texto={d} /></span>)}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
