# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Serviços da API local (seção 9.2), sem servidor: dicionários de entrada e de saída.

Cada função recebe o JSON do pedido já decodificado e devolve o JSON da
resposta. Nenhum texto fica aqui: tudo vem do catálogo (``i18n``). As
fórmulas vão em LaTeX canônico, gerado da árvore, e os textos com matemática
trazem os trechos entre ``\\(`` e ``\\)`` para a interface desenhar com KaTeX.
"""

from __future__ import annotations

import re
from functools import cache
from collections.abc import Callable
from typing import Any, Literal, cast

from amsior.erros import AmbiguidadeDeSimbolo, ErroAmsior
from amsior.expr import Simbolo, Sym, TabelaDeSimbolos, analisar, para_latex
from amsior.expr.nos import Eq, Expr
from amsior.i18n import IDIOMA_PADRAO, t
from amsior.rules.classificar import classificar
from amsior.steps import isolar as _isolar
from amsior.units import Glossario, carregar_glossario
from amsior.verify.arvore import livres
from amsior.verify.modelo import Motivo, Passo


class ErroDePedido(Exception):
    """Erro no formato único da API: código, chave de mensagem e detalhe."""

    def __init__(self, codigo: str, chave: str, detalhe: Any = None, **args: object) -> None:
        super().__init__(codigo)
        self.codigo = codigo
        self.chave = chave
        self.detalhe = detalhe
        self.args_msg = args

    def para_json(self) -> dict[str, Any]:
        return {"codigo": self.codigo, "mensagem": t(self.chave, IDIOMA_PADRAO, **self.args_msg),
                "chave": self.chave, "detalhe": self.detalhe}


@cache
def glossario() -> Glossario:
    return carregar_glossario()


# ---------------------------------------------------------------- unidades


_SOBRESCRITO = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def unidade_legivel(u: str) -> str:
    """Unidade do pint para exibição: ``J/(mol*K)`` → ``J/(mol·K)``, ``m**3`` → ``m³``."""
    if u in ("1", ""):
        return ""
    u = re.sub(r"\*\*(-?\d+)", lambda m: m.group(1).translate(_SOBRESCRITO), u)
    nomes = {"kelvin": "K", "pascal": "Pa", "meter": "m", "second": "s", "kilogram": "kg",
             "mole": "mol", "joule": "J", "watt": "W", "newton": "N", "hertz": "Hz"}
    u = re.sub(r"[a-z]+", lambda m: nomes.get(m.group(0), m.group(0)), u)
    return u.replace(" * ", "·").replace("*", "·").replace(" / ", "/")


def rota_glossario(_dados: dict[str, Any] | None = None) -> dict[str, Any]:
    g = glossario()
    itens = [{"id": gr.id, "nome": gr.nome, "unidade": unidade_legivel(gr.unidade_si),
              "suposicoes": sorted(gr.suposicoes)} for gr in g]
    itens.sort(key=lambda i: str(i["nome"]).lower())
    return {"grandezas": itens}


# ---------------------------------------------------------------- tabela de símbolos


def _tabela(simbolos: list[dict[str, Any]]) -> TabelaDeSimbolos:
    g = glossario()
    out: list[Simbolo] = []
    for s in simbolos:
        sid = str(s.get("id", ""))
        grandeza = s.get("grandeza")
        papel_txt = s.get("papel") or "variavel"
        if papel_txt not in ("variavel", "parametro", "constante"):
            raise ErroDePedido("pedido_invalido", "api.papel_invalido", papel_txt)
        papel = cast(Literal["variavel", "parametro", "constante"], papel_txt)
        if grandeza:
            if grandeza not in g:
                raise ErroDePedido("pedido_invalido", "api.grandeza_desconhecida", grandeza)
            out.append(g.simbolo(sid, grandeza, papel=papel))
        else:
            out.append(Simbolo(sid, papel=papel))
    return TabelaDeSimbolos.de(out)


def _analisar(latex: str, tabela: TabelaDeSimbolos) -> Expr:
    if not isinstance(latex, str) or not latex.strip():
        raise ErroDePedido("pedido_invalido", "api.latex_vazio")
    if len(latex) > 4000:
        raise ErroDePedido("pedido_invalido", "api.latex_longo")
    try:
        return analisar(latex, tabela, modo_palavras="produto")
    except AmbiguidadeDeSimbolo as e:  # pragma: no cover - modo produto não pergunta
        raise ErroDePedido("ambiguidade", e.chave, e.args_msg) from None
    except ErroAmsior as e:
        raise ErroDePedido("analise", e.chave, {"posicao": getattr(e, "posicao", None)},
                           **e.args_msg) from None


def _ordem(e: Expr) -> list[str]:
    """Símbolos na ordem em que aparecem, sem repetir."""
    from amsior.verify.arvore import percorrer
    vistos: list[str] = []
    for n in percorrer(e):
        if isinstance(n, Sym) and n.id in livres(e) and n.id not in vistos:
            vistos.append(n.id)
    return vistos


def rota_analisar(dados: dict[str, Any]) -> dict[str, Any]:
    tabela = _tabela(list(dados.get("simbolos") or []))
    e = _analisar(dados.get("latex", ""), tabela)
    simbolos = _ordem(e)
    conhecidos = {s.id for s in tabela}
    tipos = {}
    if isinstance(e, Eq):
        for s in simbolos:
            c = classificar(e, s, tabela)
            if c is not None:
                tipos[s] = {"chave": c.chave, "texto": t(c.chave, **c.args())}
    return {"latex": para_latex(e), "equacao": isinstance(e, Eq), "simbolos": simbolos,
            "novos": [s for s in simbolos if s not in conhecidos], "tipos": tipos}


# ---------------------------------------------------------------- isolar


def _texto(m: Motivo) -> str:
    return m.texto()


def _passo(p: Passo) -> dict[str, Any]:
    j = p.justificativa or {}
    cert = p.certificado
    return {
        "indice": p.indice,
        "regra": p.regra,
        "latex": para_latex(p.depois),
        "justificativa": t(j["chave"], **j.get("args", {})) if "chave" in j else "",
        "fundivel": bool(j.get("fundivel")),
        "condicoes": [para_latex(c.expr) for c in p.condicoes],
        "selo": None if cert is None else {
            "estado": cert.estado, "metodo": cert.metodo, "sob_hipotese": cert.sob_hipotese,
            "hipoteses": [_texto(h) for h in cert.hipoteses]},
    }


def rota_isolar(dados: dict[str, Any]) -> dict[str, Any]:
    tabela = _tabela(list(dados.get("simbolos") or []))
    e = _analisar(dados.get("latex", ""), tabela)
    alvo = str(dados.get("alvo", ""))
    if not isinstance(e, Eq):
        raise ErroDePedido("pedido_invalido", "isolar.nao_e_equacao")
    def sem_grandeza(s: str) -> bool:
        simb = tabela.obter(s)
        return simb is None or simb.grandeza is None
    faltam = [s for s in _ordem(e) if sem_grandeza(s)]
    if faltam:
        raise ErroDePedido("grandeza_ausente", "api.grandeza_ausente", faltam,
                           simbolos=", ".join(faltam))
    r = _isolar(e, Sym(alvo), tabela, glossario())
    return {
        "estado": r.estado,
        "alvo": alvo,
        "tipo": None if r.tipo is None else {"chave": r.tipo.chave,
                                             "texto": t(r.tipo.chave, **r.tipo.args())},
        "ramos": [{
            "rotulo": ramo.rotulo and t(ramo.rotulo),
            "passos": [_passo(p) for p in ramo.passos],
            "resultado": para_latex(ramo.resultado),
            "hipoteses": [_texto(h) for h in ramo.cadeia.hipoteses],
            "validade": [para_latex(c.expr) for c in ramo.validade],
        } for ramo in r.ramos],
        "descartados": [t(d.chave, ramo=t(d.args.get("ramo", ""))) if d.args.get("ramo")
                        else d.texto() for d in r.descartados],
        "sem_passos": [para_latex(s) for s in r.sem_passos],
        "motivo": None if r.motivo is None else {"chave": r.motivo.chave,
                                                 "texto": r.motivo.texto()},
    }


def rota_textos(_dados: dict[str, Any] | None = None) -> dict[str, str]:
    """Textos da interface (chaves ``ui.*``), crus: a interface faz a substituição."""
    from amsior.i18n import catalogo
    return {k: v for k, v in catalogo(IDIOMA_PADRAO).items() if k.startswith("ui.")}


ROTAS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "textos": rota_textos, "glossario": rota_glossario, "analisar": rota_analisar,
    "isolar": rota_isolar}


def executar(rota: str, dados: dict[str, Any]) -> dict[str, Any]:
    """Ponto de entrada do processo de cálculo: nunca levanta, devolve ``ok`` ou ``erro``."""
    try:
        return {"ok": ROTAS[rota](dados)}
    except ErroDePedido as e:
        return {"erro": e.para_json()}
    except Exception as e:  # o processo de cálculo nunca cai por um pedido ruim
        return {"erro": ErroDePedido("interno", "api.erro_interno", type(e).__name__).para_json()}


__all__ = ["ErroDePedido", "executar", "rota_analisar", "rota_glossario", "rota_isolar",
           "rota_textos", "unidade_legivel", "Glossario"]
