// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Sobre o Amsior (especificação 9.1): autoria, propósito, privacidade, uso sem
// internet, licença e código-fonte (a AGPL pede que quem usa um programa pela
// rede possa obter o código) e as bibliotecas de terceiros com suas licenças.
// Popover, como as configurações: não deixa o editor inerte.

import terceiros from "../dados/terceiros.json";
import { useEstado } from "../estado";
import { t } from "../textos";
import { IconeFechar } from "./icones";

export function Sobre() {
  const instalar = useEstado((s) => s.instalar);
  return (
    <div id="sobre" popover="auto" role="dialog" className="dialogo dialogo-sobre" aria-labelledby="sobre-titulo">
      <div className="dialogo-corpo">
        <div className="dialogo-topo">
          <h2 id="sobre-titulo">{t("ui.sobre.titulo", { versao: __VERSAO__ })}</h2>
          <button type="button" className="botao-icone" aria-label={t("ui.config.fechar")}
            popoverTarget="sobre" popoverTargetAction="hide"><IconeFechar /></button>
        </div>
        <p className="sobre-ideia">{t("ui.sobre.ideia")}</p>
        <ul className="sobre-lista">
          <li>{t("ui.sobre.verificacao")}</li>
          <li>{t("ui.sobre.privacidade")}</li>
          <li>{t("ui.sobre.sem_internet")}</li>
        </ul>
        {instalar ? (
          <button type="button" className="botao-simbolo sobre-instalar" onClick={instalar}>{t("ui.sobre.instalar")}</button>
        ) : null}
        <section className="campo">
          <h3>{t("ui.sobre.licenca_titulo")}</h3>
          <p className="nota">{t("ui.sobre.licenca")}</p>
          <p className="sobre-links">
            <a href={t("ui.codigo.url")} target="_blank" rel="noreferrer">{t("ui.sobre.codigo")}</a>
            <a href={t("ui.sobre.licenca_url")} target="_blank" rel="noreferrer">{t("ui.sobre.licenca_texto")}</a>
          </p>
        </section>
        <section className="campo">
          <h3>{t("ui.sobre.terceiros_titulo")}</h3>
          <p className="nota">{t("ui.sobre.terceiros")}</p>
          <table className="tabela sobre-terceiros">
            <tbody>
              {terceiros.map((b) => (
                <tr key={b.nome}><th scope="row">{b.nome}</th><td>{b.licenca}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}
