// Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
// Editor de equação: MathLive, carregado sob demanda, com vírgula decimal e
// fontes servidas pelo próprio aplicativo (sem internet).

import { useEffect, useRef } from "react";
import type { MathfieldElement } from "mathlive";
import { useEstado } from "../estado";
import { t } from "../textos";

let carregamento: Promise<typeof MathfieldElement> | null = null;

function carregarMathLive(): Promise<typeof MathfieldElement> {
  carregamento ??= import("mathlive").then(({ MathfieldElement: MF }) => {
    MF.fontsDirectory = "./mathlive/fonts";
    MF.soundsDirectory = null;
    MF.decimalSeparator = ",";
    MF.locale = "pt-BR";
    return MF;
  });
  return carregamento;
}

export function EditorEquacao() {
  const hospedeiro = useRef<HTMLDivElement>(null);
  const campo = useRef<MathfieldElement | null>(null);
  const latex = useEstado((s) => s.latex);
  const definirLatex = useEstado((s) => s.definirLatex);

  useEffect(() => {
    let vivo = true;
    void carregarMathLive().then((MF) => {
      if (!vivo || !hospedeiro.current || campo.current) return;
      const mf = new MF();
      mf.className = "editor-campo";
      mf.setAttribute("aria-label", t("ui.folha.digite"));
      mf.smartFence = true;
      mf.popoverPolicy = "off";
      mf.mathVirtualKeyboardPolicy = "manual";
      mf.value = useEstado.getState().latex;
      mf.addEventListener("input", () => definirLatex(mf.value));
      hospedeiro.current.appendChild(mf);
      campo.current = mf;
      if (!mf.value && document.activeElement === document.body) mf.focus();
    });
    return () => {
      vivo = false;
      campo.current?.remove();
      campo.current = null;
    };
  }, [definirLatex]);

  // Exemplo carregado de fora: o editor passa a mostrar a nova equação.
  useEffect(() => {
    const mf = campo.current;
    if (mf && mf.value !== latex) mf.setValue(latex, { silenceNotifications: true });
  }, [latex]);

  return <div ref={hospedeiro} className="editor" data-vazio={latex ? undefined : "sim"} data-dica={t("ui.folha.digite")} />;
}
