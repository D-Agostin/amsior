// Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
// Tabela de variáveis: para cada símbolo, a grandeza do glossário (que traz a
// unidade SI e as suposições usadas na verificação).

import { useEstado } from "../estado";
import { Mat } from "../mat";
import { t } from "../textos";

export function TabelaVariaveis() {
  const analise = useEstado((s) => s.analise);
  const simbolos = useEstado((s) => s.simbolos);
  const glossario = useEstado((s) => s.glossario);
  const definirGrandeza = useEstado((s) => s.definirGrandeza);
  const ids = analise?.simbolos ?? [];
  const porId = new Map(glossario.map((g) => [g.id, g]));
  const falta = ids.some((s) => !simbolos[s]?.grandeza);

  return (
    <aside className="variaveis" aria-label={t("ui.var.titulo")}>
      <div className="variaveis-titulo">{t("ui.var.titulo")}<span className="contagem">{ids.length}</span></div>
      {ids.length === 0 ? <p className="nota variaveis-vazio">{t("ui.var.vazio")}</p> : (
        <>
          {falta ? <p className="aviso-faixa variaveis-aviso">{t("ui.var.falta")}</p> : null}
          <table className="tabela">
            <thead>
              <tr>
                <th scope="col">{t("ui.var.col.simbolo")}</th>
                <th scope="col">{t("ui.var.col.grandeza")}</th>
                <th scope="col">{t("ui.var.col.unidade")}</th>
              </tr>
            </thead>
            <tbody>
              {ids.map((s) => {
                const sim = simbolos[s];
                const g = sim?.grandeza ? porId.get(sim.grandeza) : undefined;
                return (
                  <tr key={s} data-falta={sim?.grandeza ? undefined : "sim"}>
                    <th scope="row" className="tabela-simbolo">
                      <Mat tex={s} />
                      {sim?.papel === "constante" ? <span className="etiqueta">{t("ui.var.constante")}</span> : null}
                    </th>
                    <td>
                      <select className="seletor" aria-label={t("ui.var.grandeza_de", { simbolo: s })} title={g?.nome}
                        value={sim?.grandeza ?? ""} onChange={(e) => definirGrandeza(s, e.target.value || null)}>
                        <option value="">{t("ui.var.escolher")}</option>
                        {glossario.map((gr) => <option key={gr.id} value={gr.id}>{gr.nome}</option>)}
                      </select>
                    </td>
                    <td className="tabela-unidade">
                      {g ? (g.unidade || <span className="tabela-adimensional">{t("ui.var.adimensional")}</span>) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}
    </aside>
  );
}
