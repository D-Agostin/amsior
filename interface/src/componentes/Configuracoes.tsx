// Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
// Configurações de aparência (especificação 9.4): sistema visual D ou H e o modo.
// É um popover, não um diálogo modal: fecha com Esc ou clicando fora, e não
// deixa o resto da tela inerte (o editor MathLive para de receber teclas se a
// aparência muda enquanto a página está inerte).
import { useEstado } from "../estado";
import { modoEfetivo } from "../preferencias";
import type { Aparencia, Modo } from "../preferencias";
import { t } from "../textos";
import { Mat } from "../mat";
import { IconeFechar } from "./icones";

export function Configuracoes() {
  const prefs = useEstado((s) => s.prefs);
  const modo = useEstado((s) => modoEfetivo(s.prefs.modo, s.sistemaEscuro));
  const definirPrefs = useEstado((s) => s.definirPrefs);

  return (
    <div id="configuracoes" popover="auto" role="dialog" className="dialogo" aria-labelledby="config-titulo">
      <div className="dialogo-corpo">
        <div className="dialogo-topo">
          <h2 id="config-titulo">{t("ui.config.titulo")}</h2>
          <button type="button" className="botao-icone" aria-label={t("ui.config.fechar")}
            popoverTarget="configuracoes" popoverTargetAction="hide"><IconeFechar /></button>
        </div>

        <fieldset className="campo">
          <legend>{t("ui.config.aparencia")}</legend>
          <div className="opcoes-aparencia">
            {(["d", "h"] as Aparencia[]).map((a) => (
              <label key={a} className="opcao-aparencia">
                <input type="radio" name="aparencia" value={a} checked={prefs.aparencia === a}
                  onChange={() => definirPrefs({ aparencia: a })} />
                <span className="opcao-amostra" aria-hidden="true" data-aparencia={a} data-modo={modo}>
                  <span className="amostra-texto">{t("ui.config.amostra_texto")}</span>
                  <span className="amostra-numero">{t("ui.config.amostra_numero")}</span>
                  <Mat tex="\frac{nRT}{p}" />
                </span>
                <span className="opcao-nome">{t(`ui.config.aparencia.${a}`)}</span>
                <span className="opcao-dica">{t(`ui.config.aparencia.${a}.dica`)}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="campo">
          <legend>{t("ui.config.modo")}</legend>
          <div className="segmentado segmentado-largo" role="radiogroup">
            {(["claro", "escuro", "sistema"] as Modo[]).map((m) => (
              <label key={m} className="segmento">
                <input type="radio" name="modo" value={m} checked={prefs.modo === m} onChange={() => definirPrefs({ modo: m })} />
                <span>{t(`ui.config.modo.${m}`)}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <p className="nota">{t("ui.config.nota")}</p>
      </div>
    </div>
  );
}
