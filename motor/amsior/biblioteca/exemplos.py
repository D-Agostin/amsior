# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Conferência dos exemplos das fichas de conceito pelo motor (seção 3.5).

Afirmações quantitativas do texto entram como exemplos, e o motor as refaz: a
equação é isolada na variável pedida, todo passo exibido tem de ter certificado
aprovado, e os resultados têm de ser exatamente os declarados em ``esperado``.
Um exemplo com ``passos: false`` declara que o motor dá o resultado conferido
em V2, mas sem passos (como a raiz estranha que só aparece num polinômio de
grau 3); se um dia o motor passar a ter passos para ele, o exemplo avisa.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from amsior.biblioteca.esquema import Biblioteca, Ficha, Problema

#: grandeza dos símbolos que o exemplo não declara (exemplos de Matemática)
GRANDEZA_PADRAO = "adimensional"


def simbolo_canonico(latex: str) -> str:
    """``v_0`` e ``v_{0}`` são o mesmo símbolo: vale a forma que o analisador produz."""
    from amsior.expr.analisador import analisar
    from amsior.expr.nos import Sym

    e = analisar(latex)
    return e.id if isinstance(e, Sym) else latex


def simbolos_declarados(ex: dict[str, Any]) -> dict[str, str]:
    return {simbolo_canonico(str(s["simbolo"])): str(s["grandeza"]) for s in ex.get("simbolos") or ()}


def conferir_exemplos(b: Biblioteca, fichas: list[Ficha] | None = None) -> list[Problema]:
    from amsior.api.servico import executar

    out: list[Problema] = []
    for f in fichas if fichas is not None else list(b.fichas.values()):
        if f.tipo != "conceito":
            continue
        for i, ex in enumerate(f.dados.get("exemplos") or ()):
            if not isinstance(ex, dict) or "equacao" not in ex:
                continue  # exemplos com "usa" são conferidos com a ficha de equação
            out += _conferir(f, i, ex, executar)
    return out


Executar = Callable[[str, dict[str, Any]], dict[str, Any]]


def _conferir(f: Ficha, i: int, ex: dict[str, Any], executar: Executar) -> list[Problema]:
    campo = f"exemplos[{i}]"

    def erro(msg: str) -> list[Problema]:
        return [Problema(f.arquivo, campo, msg)]

    latex = ex["equacao"]
    declarados = simbolos_declarados(ex)
    lido = executar("analisar", {"latex": latex, "simbolos": [
        {"id": k, "grandeza": g} for k, g in declarados.items()]})
    if "erro" in lido:
        return erro(f"a equação não se lê: {lido['erro']['mensagem']}")
    simbolos = [{"id": s, "grandeza": declarados.get(s, GRANDEZA_PADRAO)} for s in lido["ok"]["simbolos"]]
    r = executar("isolar", {"latex": latex, "alvo": simbolo_canonico(ex["pede"]), "simbolos": simbolos})
    if "erro" in r:
        return erro(f"o motor recusou o pedido: {r['erro']['mensagem']}")
    ok = r["ok"]
    com_passos = ex.get("passos", True)
    if com_passos:
        if ok["estado"] != "com_passos":
            motivo = (ok.get("motivo") or {}).get("texto", "")
            return erro(f"esperado com passos, o motor deu {ok['estado']}: {motivo}")
        for ramo in ok["ramos"]:
            for p in ramo["passos"]:
                if not p["selo"] or p["selo"]["estado"] != "aprovado":
                    return erro(f"passo {p['indice']} ({p['regra']}) sem certificado aprovado")
        obtidos = sorted(ramo["resultado"] for ramo in ok["ramos"])
    else:
        if ok["estado"] == "com_passos":
            return erro("o motor agora tem passos para este exemplo: troque passos para verdadeiro")
        obtidos = sorted(ok["sem_passos"])
    esperado = sorted(ex.get("esperado") or ())
    if obtidos != esperado:
        return erro(f"resultados {obtidos}, esperados {esperado}")
    return []
