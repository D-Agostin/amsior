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
        "tipo": f.tipo,
        "equacao": _equacao(b, f) if f.tipo == "equacao" else None,
    }


def _equacao(b: Biblioteca, f: Ficha) -> dict[str, Any]:
    """Ficha de equação já verificada: passos com o certificado de cada um, o que o motor
    isola com passos e o exemplo com o valor calculado na montagem (seção 8.4)."""
    import importlib.util

    from amsior.biblioteca.equacoes import (
        _simbolos_para_api,
        tabela_da_ficha,
        verificar_ficha_equacao,
    )

    referencia = importlib.util.find_spec("CoolProp") is not None
    r = verificar_ficha_equacao(b, f, referencia=referencia)
    if r.problemas:
        raise ValueError(f"ficha {f.id} não passa na verificação: "
                         + "; ".join(map(str, r.problemas[:5])))
    d = f.dados
    tab = tabela_da_ficha(b, f)
    dem = d.get("demonstracao")
    return {
        "latex": d["equacao"],
        "simbolos": _simbolos_para_api(d["equacao"], tab),
        "hipoteses": [{"id": h, "enunciado": b.hipoteses[h].enunciado}
                      for h in d.get("hipoteses") or ()],
        "validade": (d.get("validade") or {}).get("texto"),
        "isolaveis": [s for s, e in r.corpus.items() if e == "com_passos"],
        "nao_isolaveis": [s for s, e in r.corpus.items() if e == "nao_isolavel"],
        "demonstracao": None if not dem else {
            "inicio": dem["inicio"],
            # a equação de cada passo vai como o autor escreveu (\,\mathrm{d}T e afins)
            "passos": [_passo(b, p, str(escrito["depois"]))
                       for p, escrito in zip(r.passos, dem.get("passos") or (), strict=True)],
        },
        "exemplo": _exemplo_de_equacao(b, d.get("exemplo"), r.exemplo,
                                       {s.id: s.depende_de for s in tab if s.depende_de}),
    }


def _passo(b: Biblioteca, p: Any, depois: str) -> dict[str, Any]:
    cert = p.certificado
    usa = p.usa if isinstance(p.usa, str) else None
    hip = b.hipoteses.get(usa.removeprefix("hipotese.")) if usa and usa.startswith("hipotese.") else None
    return {
        "titulo": p.titulo, "texto": p.texto, "tipo": p.tipo, "relacao": p.relacao,
        "depois": depois, "condicoes": p.condicoes,
        "usa": None if hip is None else {"id": hip.id, "enunciado": hip.enunciado},
        "usa_ficha": usa if usa and not usa.startswith("hipotese.") and usa != "definicao" else None,
        "estado": cert["estado"], "metodo": cert["metodo"],
    }


def _exemplo_de_equacao(b: Biblioteca, ex: dict[str, Any] | None, res: dict[str, Any] | None,
                        dependencias: dict[str, tuple[str, ...]]) -> dict[str, Any] | None:
    if not ex or not res:
        return None
    comp = ex.get("comparacao_independente") or {}
    fonte = b.fontes.get(str(comp.get("fonte"))) if comp else None
    return {
        "enunciado": ex["enunciado"],
        "dados": [{"simbolo": k, "valor": str(v)} for k, v in (ex.get("dados") or {}).items()],
        "funcoes": [{"simbolo": k, "de": list(dependencias.get(k, ())), "expressao": str(v)}
                    for k, v in (ex.get("funcoes") or {}).items()],
        "origem_dos_dados": ex.get("origem_dos_dados"),
        "pede": res["pede"],
        "resultado": res["resultado"],
        "valor": res["valor"],
        "unidade": res["unidade"],
        "comparacao": None if "referencia" not in res or fonte is None else {
            "fonte": fonte.titulo, "valor": res["referencia"], "desvio_rel": res["desvio_rel"]},
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
