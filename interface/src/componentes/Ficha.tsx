// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Ficha de conceito e de equação (especificação 3.4, 3.5 e 8.6): resumo em caixa,
// seções numeradas, equações em linha própria e numeradas, "onde:", dedução em
// passos, caixas de destaque, atenção e hipóteses. Abre no centro, no lugar da folha.
// A ficha de equação traz ainda as hipóteses, a demonstração com o selo do
// verificador em cada passo, o exemplo calculado e "Usar na folha".

import { Fragment, useEffect, useMemo, useRef } from "react";
import type { ReactNode } from "react";
import type { Bloco, EquacaoDaFicha, ExemploEquacao, FichaApi, PassoDemonstracao, ReferenciaFicha, TextoML } from "../api";
import { useEstado } from "../estado";
import { Mat, Texto } from "../mat";
import { t } from "../textos";
import { IconeFechar } from "./icones";

/** Texto da ficha: **negrito** e matemática em linha \( \). */
export function Rico({ texto }: { texto: TextoML | string }) {
  const s = typeof texto === "string" ? texto : texto.pt;
  const partes = s.split(/\*\*(.+?)\*\*/g);
  return (
    <>
      {partes.map((p, i) => (i % 2 === 1 ? <strong key={i}><Texto texto={p} /></strong> : <Texto key={i} texto={p} />))}
    </>
  );
}

/** Número de cada equação na ordem de leitura (resumo, depois as seções). */
export function numerarEquacoes(f: FichaApi): Map<Bloco, number> {
  const mapa = new Map<Bloco, number>();
  const visitar = (bs: Bloco[]) => {
    for (const b of bs) {
      if ("equacao" in b) mapa.set(b, mapa.size + 1);
      if ("blocos" in b) visitar(b.blocos);
      if ("passos" in b) for (const p of b.passos) visitar(p.blocos);
    }
  };
  visitar(f.resumo);
  for (const s of f.secoes) visitar(s.blocos);
  return mapa;
}

function Blocos({ blocos, nums }: { blocos: Bloco[]; nums: Map<Bloco, number> }) {
  return <>{blocos.map((b, i) => <UmBloco key={i} b={b} nums={nums} />)}</>;
}

function UmBloco({ b, nums }: { b: Bloco; nums: Map<Bloco, number> }) {
  if ("texto" in b) return <p className="ficha-texto"><Rico texto={b.texto} /></p>;
  if ("equacao" in b) {
    return (
      <>
        <div className={b.destaque ? "ficha-eq ficha-eq-destaque" : "ficha-eq"}>
          <span className="ficha-eq-corpo"><Mat tex={b.equacao} exibicao /></span>
          <span className="ficha-eq-num">({nums.get(b)})</span>
        </div>
        {b.nota ? <p className="ficha-eq-nota"><Rico texto={b.nota} /></p> : null}
        {b.onde ? (
          <div className="ficha-onde">
            <span className="rotulo">{t("ui.ficha.onde")}</span>
            <ul>
              {b.onde.map((o, i) => <li key={i}><Mat tex={o.simbolo} /> — <Rico texto={o.texto} /></li>)}
            </ul>
          </div>
        ) : null}
      </>
    );
  }
  if ("lista" in b) return <ul className="ficha-lista">{b.lista.map((it, i) => <li key={i}><Rico texto={it} /></li>)}</ul>;
  if ("caixa" in b) {
    return (
      <aside className={`ficha-caixa ficha-caixa-${b.caixa}`}>
        <div className="ficha-caixa-titulo">{b.titulo ? <Rico texto={b.titulo} /> : t(`ui.ficha.caixa.${b.caixa}`)}</div>
        <div className="ficha-caixa-corpo"><Blocos blocos={b.blocos} nums={nums} /></div>
      </aside>
    );
  }
  if ("passos" in b) {
    return (
      <ol className="ficha-passos">
        {b.passos.map((p, i) => (
          <li key={i} className="ficha-passo">
            <div className="ficha-passo-titulo">{t("ui.ficha.passo", { n: i + 1 })} — <Rico texto={p.titulo} /></div>
            <div className="ficha-passo-corpo"><Blocos blocos={p.blocos} nums={nums} /></div>
          </li>
        ))}
      </ol>
    );
  }
  if ("tabela" in b) {
    return (
      <table className="tabela ficha-tabela">
        <thead><tr>{b.tabela.colunas.map((c, i) => <th key={i} scope="col"><Rico texto={c} /></th>)}</tr></thead>
        <tbody>{b.tabela.linhas.map((l, i) => <tr key={i}>{l.map((c, j) => <td key={j}><Rico texto={c} /></td>)}</tr>)}</tbody>
      </table>
    );
  }
  // figura: SVG do próprio repositório, desenhado com a cor do texto (currentColor)
  return (
    <figure className="ficha-figura">
      {b.svg ? <div className="ficha-figura-svg" dangerouslySetInnerHTML={{ __html: b.svg }} /> : null}
      {b.legenda ? <figcaption><Rico texto={b.legenda} /></figcaption> : null}
    </figure>
  );
}

function Variaveis({ f }: { f: FichaApi }) {
  const glossario = useEstado((s) => s.glossario);
  return (
    <table className="tabela ficha-tabela ficha-variaveis">
      <thead>
        <tr>
          <th scope="col">{t("ui.ficha.col.simbolo")}</th>
          <th scope="col">{t("ui.ficha.col.nome")}</th>
          <th scope="col">{t("ui.ficha.col.unidade")}</th>
        </tr>
      </thead>
      <tbody>
        {f.variaveis.map((v) => {
          const g = glossario.find((x) => x.id === v.grandeza);
          return (
            <tr key={v.simbolo}>
              <td className="ficha-simbolo"><Mat tex={v.simbolo} /></td>
              <td>
                {v.nome ? <Rico texto={v.nome} /> : g?.nome}
                {v.nota ? <div className="nota"><Rico texto={v.nota} /></div> : null}
              </td>
              <td className="tabela-unidade">{g ? (g.unidade || t("ui.var.adimensional")) : null}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Referencia({ r }: { r: ReferenciaFicha }) {
  const onde = [
    r.capitulo ? t("ui.ficha.cap", { capitulo: r.capitulo }) : null,
    r.secao ? t("ui.ficha.secao", { secao: r.secao }) : null,
    r.equacao ? t("ui.ficha.eq", { equacao: r.equacao }) : null,
    r.pagina ? t("ui.ficha.pagina", { pagina: r.pagina }) : null,
  ].filter(Boolean).join(", ");
  return (
    <li>
      <cite>{r.titulo}</cite>
      {r.autores.length ? ` — ${r.autores.join(", ")}` : ""}
      {r.edicao ? `, ${t("ui.ficha.edicao", { edicao: r.edicao })}` : ""}
      {r.ano ? `, ${r.ano}` : ""}
      {onde ? `; ${onde}` : ""}.
      {r.licenca ? ` ${t("ui.ficha.licenca", { licenca: r.licenca })}` : ""}
      {r.url ? <> <a href={r.url} target="_blank" rel="noreferrer">{r.url}</a></> : null}
      {r.uso === "adaptacao" && r.adaptacao ? (
        <div className="nota"><strong>{t("ui.ficha.adaptado")}</strong> <Rico texto={r.adaptacao} /></div>
      ) : null}
      {!r.conferido ? <div className="nota">{t("ui.ficha.citacao_pendente")}</div> : null}
    </li>
  );
}

/** Número no estilo do português (vírgula decimal), pronto para o KaTeX. */
export function numeroTex(v: number, digitos = 4): string {
  return v.toLocaleString("pt-BR", { maximumSignificantDigits: digitos, useGrouping: false }).replace(",", "{,}");
}

function porcento(v: number): string {
  return `${(100 * v).toLocaleString("pt-BR", { maximumSignificantDigits: 2 })} %`;
}

function unidadeTex(u: string): string {
  return u ? `\\ \\mathrm{${u.replace(/\^(\d)/g, "^{$1}")}}` : "";
}

function UsarNaFolha({ f, eq }: { f: FichaApi; eq: EquacaoDaFicha }) {
  const carregar = useEstado((s) => s.carregarExemplo);
  return (
    <aside className="ficha-usar" aria-label={t("ui.ficha.usar")}>
      <div className="ficha-usar-titulo">{t("ui.ficha.usar")}</div>
      <p className="nota">{t("ui.ficha.usar_nota")}</p>
      <div className="ficha-usar-botoes">
        {eq.isolaveis.map((v) => (
          <button key={v} type="button" className="botao-simbolo"
            aria-label={t("ui.ficha.isolar_aria", { variavel: v })}
            onClick={() => carregar({ id: `${f.id}@${v}`, area: f.area, latex: eq.latex, alvo: v, simbolos: eq.simbolos })}>
            <Mat tex={v} />
          </button>
        ))}
      </div>
      {eq.nao_isolaveis.length ? (
        <p className="nota">
          {t("ui.ficha.usar_sem_passos")}{" "}
          {eq.nao_isolaveis.map((v, i) => <Fragment key={v}>{i ? ", " : ""}<Mat tex={v} /></Fragment>)}.
        </p>
      ) : null}
    </aside>
  );
}

function Passo({ p, n }: { p: PassoDemonstracao; n: number }) {
  const ok = p.estado === "aprovado";
  return (
    <li className="ficha-passo">
      <div className="ficha-passo-titulo ficha-passo-titulo-selo">
        <span>{t("ui.ficha.passo", { n })}{p.titulo ? <> — <Rico texto={p.titulo} /></> : null}</span>
        <span className={`selo ${ok ? "selo-ok" : "selo-aviso"}`}
          title={ok ? t("ui.ficha.passo_dica") : t("ui.ficha.passo_pendente_dica")}>
          {ok ? t("ui.ficha.passo_ok") : t("ui.ficha.passo_pendente")}
        </span>
      </div>
      <div className="ficha-passo-corpo">
        {p.texto ? <p className="ficha-texto"><Rico texto={p.texto} /></p> : null}
        {p.usa ? <p className="ficha-passo-usa"><strong>{t("ui.ficha.usa_hipotese")}</strong> <Rico texto={p.usa.enunciado} /></p> : null}
        <div className="ficha-eq ficha-eq-passo">
          {p.relacao === "implica" ? <span className="ficha-eq-rel" title={t("ui.ficha.implica_dica")}>⇒</span> : null}
          <span className="ficha-eq-corpo"><Mat tex={p.depois} exibicao /></span>
        </div>
        {p.condicoes.length ? (
          <p className="ficha-eq-nota">
            {t("ui.ficha.condicao")}{" "}
            {p.condicoes.map((c, i) => <Fragment key={i}>{i ? "; " : ""}<Mat tex={c} /></Fragment>)}
          </p>
        ) : null}
      </div>
    </li>
  );
}

function Demonstracao({ dem }: { dem: NonNullable<EquacaoDaFicha["demonstracao"]> }) {
  const ini = dem.inicio;
  return (
    <>
      <p className="nota">{t("ui.ficha.demonstracao_nota")}</p>
      <aside className="ficha-caixa ficha-caixa-destaque">
        <div className="ficha-caixa-titulo">
          {t("ui.ficha.ponto_de_partida")}{ini.titulo ? <> — <Rico texto={ini.titulo} /></> : null}
          <span className="selo selo-neutro">{t(`ui.ficha.inicio.${ini.tipo}`)}</span>
        </div>
        <div className="ficha-caixa-corpo">
          {ini.texto ? <p className="ficha-texto"><Rico texto={ini.texto} /></p> : null}
          <div className="ficha-eq ficha-eq-passo"><span className="ficha-eq-corpo"><Mat tex={ini.equacao} exibicao /></span></div>
        </div>
      </aside>
      <ol className="ficha-passos ficha-demonstracao">
        {dem.passos.map((p, i) => <Passo key={i} p={p} n={i + 1} />)}
      </ol>
    </>
  );
}

function ExemploDeEquacao({ f, eq, ex }: { f: FichaApi; eq: EquacaoDaFicha; ex: ExemploEquacao }) {
  const carregar = useEstado((s) => s.carregarExemplo);
  const resultado = `${ex.pede} = ${numeroTex(ex.valor)}${unidadeTex(ex.unidade)}`;
  return (
    <div className="ficha-exemplo-equacao">
      <p className="ficha-texto"><Rico texto={ex.enunciado} /></p>
      <table className="tabela ficha-tabela ficha-dados">
        <caption>{t("ui.ficha.dados")}</caption>
        <thead><tr><th scope="col">{t("ui.ficha.col.simbolo")}</th><th scope="col">{t("ui.ficha.col.valor")}</th></tr></thead>
        <tbody>
          {ex.dados.map((d) => (
            <tr key={d.simbolo}><td className="ficha-simbolo"><Mat tex={d.simbolo} /></td><td className="tabela-unidade">{d.valor}</td></tr>
          ))}
        </tbody>
      </table>
      {ex.funcoes.map((fn) => (
        <div key={fn.simbolo} className="ficha-eq ficha-eq-passo">
          <span className="ficha-eq-corpo"><Mat tex={`${fn.simbolo}(${fn.de.join(", ")}) = ${fn.expressao.replace(/(\d)\.(\d)/g, "$1{,}$2")}`} exibicao /></span>
        </div>
      ))}
      {ex.origem_dos_dados ? <p className="nota"><Rico texto={ex.origem_dos_dados} /></p> : null}
      <div className="ficha-passo-titulo">{t("ui.ficha.resultado")}</div>
      <div className="ficha-eq ficha-eq-passo"><span className="ficha-eq-corpo"><Mat tex={ex.resultado} exibicao /></span></div>
      <div className="ficha-eq ficha-eq-destaque ficha-eq-passo"><span className="ficha-eq-corpo"><Mat tex={resultado} exibicao /></span></div>
      {ex.comparacao ? (
        <p className="nota">
          {t("ui.ficha.comparacao", { fonte: ex.comparacao.fonte, desvio: porcento(ex.comparacao.desvio_rel) })}{" "}
          <Mat tex={`${numeroTex(ex.comparacao.valor)}${unidadeTex(ex.unidade)}`} />.
        </p>
      ) : null}
      {eq.isolaveis.includes(ex.pede) ? (
        <button type="button" className="botao-simbolo"
          onClick={() => carregar({ id: `${f.id}@${ex.pede}`, area: f.area, latex: eq.latex, alvo: ex.pede, simbolos: eq.simbolos })}>
          {t("ui.ficha.abrir_na_folha")}
        </button>
      ) : null}
    </div>
  );
}

export function Ficha({ id }: { id: string }) {
  const f = useEstado((s) => s.biblioteca.fichas[id]);
  const fichas = useEstado((s) => s.biblioteca.fichas);
  const abrir = useEstado((s) => s.abrirFicha);
  const carregar = useEstado((s) => s.carregarExemplo);
  const nums = useMemo(() => (f ? numerarEquacoes(f) : new Map<Bloco, number>()), [f]);
  // outra ficha aberta (pelo painel ou por "Veja também"): volta ao topo
  const rolagem = useRef<HTMLElement>(null);
  useEffect(() => { rolagem.current?.scrollTo?.({ top: 0 }); }, [id]);
  if (!f) return null;
  const eq = f.equacao ?? null;

  // numeração das seções na ordem em que aparecem (chamada aqui, não num componente filho)
  let secao = 0;
  const titulo = (conteudo: ReactNode) => (
    <h2 className="ficha-secao-titulo"><span className="ficha-secao-num">{++secao}</span>{conteudo}</h2>
  );

  return (
    <article ref={rolagem} className="folha ficha" aria-labelledby="ficha-titulo">
      <div className="ficha-barra">
        <button type="button" className="botao-simbolo" onClick={() => abrir(null)}>
          <IconeFechar /> {t("ui.ficha.voltar")}
        </button>
      </div>
      <div className="ficha-papel">
        <header className="ficha-cabeca">
          <div className="ficha-cabeca-topo">
            <span>{t(`ui.area.${f.area}`)}{f.grupo ? ` · ${f.grupo.pt}` : ""}</span>
            <span className={`selo ${f.estado === "verificada" ? "selo-ok" : "selo-aviso"}`}
              title={t(`ui.ficha.dica.${f.estado}`)}>{t(`ui.ficha.estado.${f.estado}`)}</span>
          </div>
          <h1 id="ficha-titulo">{f.titulo.pt}</h1>
        </header>

        <aside className="ficha-caixa ficha-caixa-resumo">
          <div className="ficha-caixa-titulo">{t("ui.ficha.caixa.resumo")}</div>
          <div className="ficha-caixa-corpo"><Blocos blocos={f.resumo} nums={nums} /></div>
        </aside>

        {eq ? <UsarNaFolha f={f} eq={eq} /> : null}

        {f.variaveis.length ? (
          <section>{titulo(t("ui.ficha.variaveis"))}<Variaveis f={f} /></section>
        ) : null}

        {eq && (eq.hipoteses.length || eq.validade) ? (
          <section>
            {titulo(t("ui.ficha.hipoteses"))}
            {eq.hipoteses.length ? (
              <aside className="ficha-caixa ficha-caixa-hipoteses">
                <div className="ficha-caixa-titulo">{t("ui.ficha.caixa.hipoteses")}</div>
                <div className="ficha-caixa-corpo">
                  <ul className="ficha-lista">{eq.hipoteses.map((h) => <li key={h.id}><Rico texto={h.enunciado} /></li>)}</ul>
                </div>
              </aside>
            ) : null}
            {eq.validade ? (
              <aside className="ficha-caixa ficha-caixa-atencao">
                <div className="ficha-caixa-titulo">{t("ui.ficha.validade")}</div>
                <div className="ficha-caixa-corpo"><p className="ficha-texto"><Rico texto={eq.validade} /></p></div>
              </aside>
            ) : null}
          </section>
        ) : null}

        {f.secoes.map((s, i) => (
          <section key={i}>
            {titulo(<Rico texto={s.titulo} />)}
            <Blocos blocos={s.blocos} nums={nums} />
          </section>
        ))}

        {eq?.demonstracao ? (
          <section>{titulo(t("ui.ficha.demonstracao"))}<Demonstracao dem={eq.demonstracao} /></section>
        ) : null}

        {eq?.exemplo ? (
          <section>{titulo(t("ui.ficha.exemplo"))}<ExemploDeEquacao f={f} eq={eq} ex={eq.exemplo} /></section>
        ) : null}

        {f.exemplos.length ? (
          <section>
            {titulo(t("ui.ficha.exemplos"))}
            <p className="nota">{t("ui.ficha.exemplos_nota")}</p>
            <ol className="ficha-exemplos">
              {f.exemplos.map((ex, i) => (
                <li key={i} className="ficha-exemplo">
                  <div className="ficha-exemplo-texto">
                    <Rico texto={ex.enunciado} />
                    {!ex.passos ? <div className="nota">{t("ui.ficha.sem_passos")}</div> : null}
                  </div>
                  <span className="ficha-exemplo-eq"><Mat tex={ex.equacao} exibicao /></span>
                  <button type="button" className="botao-simbolo"
                    onClick={() => carregar({ id: `${f.id}#${i + 1}`, area: f.area, latex: ex.equacao, alvo: ex.pede,
                      simbolos: ex.simbolos })}>
                    {t("ui.ficha.abrir_na_folha")}
                  </button>
                </li>
              ))}
            </ol>
          </section>
        ) : null}

        {f.relacionadas.length ? (
          <section>
            {titulo(t("ui.ficha.relacionadas"))}
            <ul className="ficha-relacionadas">
              {f.relacionadas.map((r) => (
                <li key={r}><button type="button" className="ficha-link" onClick={() => abrir(r)}>{fichas[r].titulo.pt}</button></li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="ficha-referencias">
          {titulo(t("ui.ficha.referencias"))}
          <ul>{f.referencias.map((r, i) => <Fragment key={i}><Referencia r={r} /></Fragment>)}</ul>
          <p className="nota">{t("ui.ficha.licenca_conteudo")}</p>
        </section>
      </div>
    </article>
  );
}
