# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Biblioteca para a interface: só o que o aluno pode ver, pronto para desenhar.

Roda na montagem do site (ferramentas/web/montar_motor.py), com o Python nativo,
e vai para ``dados.json``. Fica de fora tudo o que é rascunho (seção 8.5): as
fichas, as ligações para elas em ``relacionadas`` e os tipos de equação que
elas explicariam. As figuras vão embutidas (SVG próprio do repositório), as
fontes vão resolvidas e cada exemplo leva a tabela de símbolos completa, para
abrir na folha sem pedir grandeza ao aluno.
"""

from __future__ import annotations

import datetime as _dt
import json
from typing import Any

from amsior.biblioteca.esquema import AREAS, Biblioteca, Ficha
from amsior.biblioteca.exemplos import GRANDEZA_PADRAO, simbolo_canonico, simbolos_declarados


def para_interface(b: Biblioteca) -> dict[str, Any]:
    if b.problemas:
        raise ValueError("biblioteca com problemas: " + "; ".join(map(str, b.problemas[:5])))
    visiveis = {fid: f for fid, f in b.fichas.items() if f.visivel}
    fichas = {fid: _ficha(b, f, visiveis) for fid, f in visiveis.items()}
    areas = [{"id": a, "fichas": [f.id for f in b.da_area(a) if f.visivel]} for a in AREAS]
    tipos = {t: f.id for f in visiveis.values() for t in f.dados.get("tipos") or ()}
    return json.loads(json.dumps({
        "areas": [a for a in areas if a["fichas"]],
        "fichas": fichas,
        "tipos": tipos,
    }, default=_json, ensure_ascii=False))


def _json(v: Any) -> Any:
    if isinstance(v, _dt.date):
        return v.isoformat()
    raise TypeError(type(v).__name__)


def _ficha(b: Biblioteca, f: Ficha, visiveis: dict[str, Ficha]) -> dict[str, Any]:
    d = f.dados
    return {
        "id": f.id,
        "area": f.area,
        "estado": f.estado,
        "versao": d.get("versao"),
        "grupo": d.get("grupo"),
        "titulo": d.get("titulo"),
        "tipos": list(d.get("tipos") or ()),
        "resumo": _blocos(b, d.get("resumo") or []),
        "variaveis": list(d.get("variaveis") or ()),
        "secoes": [{"titulo": s["titulo"], "blocos": _blocos(b, s["blocos"])} for s in d.get("secoes") or ()],
        "exemplos": [_exemplo(e) for e in d.get("exemplos") or () if "equacao" in e],
        "referencias": [_referencia(b, r) for r in d.get("referencias") or ()],
        "relacionadas": [r for r in d.get("relacionadas") or () if r in visiveis],
    }


def _blocos(b: Biblioteca, blocos: list[Any]) -> list[Any]:
    out = []
    for bl in blocos:
        bl = dict(bl)
        if "figura" in bl and b.raiz is not None:
            svg = (b.raiz / "figuras" / bl["figura"]).read_text(encoding="utf-8")
            bl["svg"] = _sem_comentarios(svg)
        if "blocos" in bl:
            bl["blocos"] = _blocos(b, bl["blocos"])
        if "passos" in bl:
            bl["passos"] = [{"titulo": p["titulo"], "blocos": _blocos(b, p["blocos"])} for p in bl["passos"]]
        out.append(bl)
    return out


def _sem_comentarios(svg: str) -> str:
    import re
    return re.sub(r"<!--.*?-->", "", svg, flags=re.S).strip()


def _exemplo(e: dict[str, Any]) -> dict[str, Any]:
    from amsior.api.servico import executar

    declarados = simbolos_declarados(e)
    lido = executar("analisar", {"latex": e["equacao"], "simbolos": [
        {"id": k, "grandeza": g} for k, g in declarados.items()]})["ok"]
    return {
        "enunciado": e["enunciado"],
        "equacao": e["equacao"],
        "pede": simbolo_canonico(e["pede"]),
        "simbolos": [{"id": s, "grandeza": declarados.get(s, GRANDEZA_PADRAO)} for s in lido["simbolos"]],
        "passos": e.get("passos", True),
        "tipo": e.get("tipo"),
        "tem_resultado": e.get("esperado") is not None,
    }


def _referencia(b: Biblioteca, r: dict[str, Any]) -> dict[str, Any]:
    fonte = b.fontes[r["fonte"]]
    conferido = bool((r.get("conferido") or {}).get("por"))
    return {
        "titulo": fonte.titulo,
        "autores": list(fonte.dados.get("autores") or ()),
        "edicao": fonte.dados.get("edicao"),
        "ano": fonte.dados.get("ano"),
        "licenca": fonte.licenca,
        "url": fonte.dados.get("url"),
        "uso": r.get("uso", "citacao"),
        "adaptacao": r.get("adaptacao"),
        "capitulo": r.get("capitulo"),
        "secao": r.get("secao"),
        # D-05: número de equação e página só aparecem depois da conferência
        "equacao": r.get("equacao") if conferido else None,
        "pagina": r.get("pagina") if conferido else None,
        "conferido": conferido,
    }
