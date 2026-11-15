// Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
// A folha: bloco da equação e, abaixo, a resolução do alvo escolhido.

import { useEstado } from "../estado";
import { Mat, Texto } from "../mat";
import { plano, t } from "../textos";
import { EditorEquacao } from "./EditorEquacao";
import { Resolucao } from "./Resolucao";

function BotoesIsolar() {
  const analise = useEstado((s) => s.analise);
  const alvo = useEstado((s) => s.alvo);
  const isolar = useEstado((s) => s.isolar);
  if (!analise?.equacao) return null;
  return (
    <div className="isolar" role="group" aria-label={t("ui.folha.isolar")}>
      <span className="rotulo">{t("ui.folha.isolar")}</span>
      {analise.simbolos.map((s) => {
        const tipo = analise.tipos[s];
        return (
          <span key={s} className="com-dica">
            <button type="button" className="botao-simbolo" aria-pressed={alvo === s}
              aria-label={t("ui.folha.isolar_rotulo", { simbolo: s, tipo: tipo ? plano(tipo.texto) : "" })}
              onClick={() => isolar(s)}>
              <Mat tex={s} />
            </button>
            {tipo ? <span className="dica" role="tooltip"><Texto texto={tipo.texto} /></span> : null}
          </span>
        );
      })}
    </div>
  );
}

function BlocoEquacao() {
  const analise = useEstado((s) => s.analise);
  const erro = useEstado((s) => s.erroAnalise);
  const lendo = useEstado((s) => s.lendo);
  const latex = useEstado((s) => s.latex);

  return (
    <section className="cartao bloco-equacao" aria-label={t("ui.folha.equacao")}>
      <div className="bloco-linha">
        <span className="num-celula">[1]</span>
        <EditorEquacao />
      </div>
      <div className="bloco-eco" aria-live="polite">
        {erro ? (
          <span className="mensagem-erro">{erro.mensagem ? <Texto texto={erro.mensagem} /> : t(erro.chave)}</span>
        ) : analise && latex ? (
          <>
            <span className="rotulo">{t("ui.folha.eco")}</span>
            <Mat tex={analise.latex} className={lendo ? "esmaecido" : undefined} />
            {!analise.equacao ? <span className="mensagem-aviso">{t("ui.folha.nao_e_equacao")}</span> : null}
          </>
        ) : (
          <span className="nota"><Texto texto={t("ui.folha.dica_entrada")} /></span>
        )}
      </div>
      <BotoesIsolar />
    </section>
  );
}

export function Folha() {
  const latex = useEstado((s) => s.latex);
  return (
    <main className="folha">
      <BlocoEquacao />
      {latex ? <Resolucao /> : <p className="folha-vazia">{t("ui.folha.vazia")}</p>}
    </main>
  );
}
