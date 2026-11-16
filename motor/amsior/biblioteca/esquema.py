# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Esquema das fichas e ligações entre os arquivos da biblioteca.

Seções 3.4 (ficha de equação), 3.5 (ficha de conceito), 8.3 (hipóteses), 8.4
(citações) e 8.5 (estados) da especificação. A validação é escrita à mão, sem
biblioteca de esquema, porque o mesmo código roda no navegador (Pyodide).

Cada problema diz o arquivo e o campo. ``validar`` não para no primeiro: devolve
todos, para que uma ficha nova seja corrigida de uma vez.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from amsior.units.glossario import Glossario, carregar_glossario, ler_dados, pasta_biblioteca

ESTADOS: tuple[str, ...] = ("rascunho", "auto_verificada", "verificada")
AREAS: tuple[str, ...] = (
    "matematica", "termodinamica", "balancos", "reatores", "mecanica_dos_fluidos",
    "transferencia_de_calor", "transferencia_de_massa", "operacoes_unitarias",
)
_AREAS_DE_FONTE = (*AREAS, "geral")
_USOS = ("citacao", "adaptacao")
_PAPEIS = ("base", "apoio")
#: Licenças que permitem adaptar com crédito e redistribuir sob CC BY-SA 4.0 (seção 8.6).
LICENCAS_ADAPTAVEIS = frozenset({"CC-BY-SA-4.0", "CC-BY-4.0"})
_ID = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_ID_SIMPLES = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class Problema:
    arquivo: str
    campo: str
    mensagem: str

    def __str__(self) -> str:
        return f"{self.arquivo}: {self.campo}: {self.mensagem}" if self.campo else f"{self.arquivo}: {self.mensagem}"


@dataclass(frozen=True)
class Fonte:
    id: str
    papel: str
    area: str
    uso: str
    titulo: str
    licenca: str | None
    dados: dict[str, Any]


@dataclass(frozen=True)
class Hipotese:
    id: str
    enunciado: dict[str, str]
    consequencia: str | None
    areas: tuple[str, ...]


@dataclass(frozen=True)
class Ficha:
    id: str
    tipo: str  # "equacao" | "conceito"
    estado: str
    area: str
    arquivo: str
    dados: dict[str, Any]

    @property
    def visivel(self) -> bool:
        """Só ``rascunho`` fica fora do alcance do aluno (seção 8.5)."""
        return self.estado != "rascunho"

    def texto(self, campo: str, idioma: str = "pt") -> str | None:
        v = self.dados.get(campo)
        return v.get(idioma) if isinstance(v, dict) else None


@dataclass
class Biblioteca:
    fontes: dict[str, Fonte] = field(default_factory=dict)
    hipoteses: dict[str, Hipotese] = field(default_factory=dict)
    fichas: dict[str, Ficha] = field(default_factory=dict)
    problemas: list[Problema] = field(default_factory=list)  # da leitura e do esquema
    glossario: Glossario | None = None
    raiz: Path | None = None  # pasta lida; as figuras ficam em <raiz>/figuras

    def da_area(self, area: str) -> list[Ficha]:
        """Fichas de uma área na ordem da lista da seção 8.7 (``ordem``), depois por id."""
        fs = [f for f in self.fichas.values() if f.area == area]
        return sorted(fs, key=lambda f: (f.dados.get("ordem") or 10_000, f.id))

    def ficha_do_tipo(self, chave: str) -> Ficha | None:
        """Ficha de Matemática que explica um tipo de equação (D-12)."""
        for f in self.fichas.values():
            if chave in (f.dados.get("tipos") or ()):
                return f
        return None


# ------------------------------------------------------------------ leitura


def carregar_biblioteca(pasta: str | Path | None = None, glossario: Glossario | None = None) -> Biblioteca:
    """Lê fontes, hipóteses e fichas (``<area>/<nome>.yaml``) e valida tudo."""
    raiz = Path(pasta) if pasta is not None else pasta_biblioteca()
    b = Biblioteca(glossario=glossario if glossario is not None else carregar_glossario(), raiz=raiz)
    _ler_fontes(b, raiz)
    _ler_hipoteses(b, raiz)
    for arq in sorted(raiz.glob("*/*.yaml")) + sorted(raiz.glob("*/*.json")):
        if arq.name.startswith("_"):
            continue
        rel = arq.relative_to(raiz).as_posix()
        try:
            dados = ler_dados(arq)
        except Exception as e:  # noqa: BLE001 - qualquer erro de leitura vira problema da ficha
            b.problemas.append(Problema(rel, "", f"não foi possível ler: {e}"))
            continue
        _registrar_ficha(b, rel, dados)
    b.problemas.extend(validar(b))
    return b


def _ler_vocabulario(b: Biblioteca, raiz: Path, nome: str, chave: str) -> dict[str, Any]:
    for ext in (".yaml", ".json"):
        arq = raiz / f"{nome}{ext}"
        if arq.exists():
            dados = ler_dados(arq)
            if not isinstance(dados, dict) or dados.get("formato") != 1:
                b.problemas.append(Problema(arq.name, "formato", "formato desconhecido (esperado 1)"))
                return {}
            itens = dados.get(chave)
            if not isinstance(itens, dict):
                b.problemas.append(Problema(arq.name, chave, "esperado um mapa de id para item"))
                return {}
            return itens
    b.problemas.append(Problema(f"{nome}.yaml", "", "arquivo ausente"))
    return {}


def _ler_fontes(b: Biblioteca, raiz: Path) -> None:
    arq = "_fontes.yaml"
    for fid, f in _ler_vocabulario(b, raiz, "_fontes", "fontes").items():
        v = _Validador(arq, f"fontes.{fid}", b.problemas)
        if not _ID_SIMPLES.match(str(fid)):
            v.erro("", "id inválido (minúsculas, algarismos e _)")
        if not isinstance(f, dict):
            v.erro("", "esperado um mapa")
            continue
        v.chaves(f, {"papel", "area", "uso", "titulo", "autores", "editora", "idioma", "licenca",
                     "url", "codigo_fonte", "versao", "edicao", "ano", "isbn", "nota", "conferido"})
        v.escolha(f, "papel", _PAPEIS)
        v.escolha(f, "area", _AREAS_DE_FONTE)
        v.escolha(f, "uso", _USOS)
        v.texto_simples(f, "titulo")
        licenca = f.get("licenca")
        if f.get("uso") == "adaptacao" and licenca not in LICENCAS_ADAPTAVEIS:
            v.erro("licenca", f"uso 'adaptacao' só com licença aberta compatível: {sorted(LICENCAS_ADAPTAVEIS)}")
        v.conferido(f.get("conferido"), "conferido")
        b.fontes[str(fid)] = Fonte(str(fid), str(f.get("papel")), str(f.get("area")), str(f.get("uso")),
                                   str(f.get("titulo")), licenca, f)


def _ler_hipoteses(b: Biblioteca, raiz: Path) -> None:
    arq = "_hipoteses.yaml"
    for hid, h in _ler_vocabulario(b, raiz, "_hipoteses", "hipoteses").items():
        v = _Validador(arq, f"hipoteses.{hid}", b.problemas)
        if not _ID_SIMPLES.match(str(hid)):
            v.erro("", "id inválido (minúsculas, algarismos e _)")
        if not isinstance(h, dict):
            v.erro("", "esperado um mapa")
            continue
        v.chaves(h, {"enunciado", "consequencia", "areas"})
        v.multilingue(h, "enunciado", obrigatorio=True)
        for a in h.get("areas") or ():
            if a not in AREAS:
                v.erro("areas", f"área desconhecida: {a}")
        cons = h.get("consequencia")
        b.hipoteses[str(hid)] = Hipotese(
            str(hid), dict(h.get("enunciado") or {}), None if cons is None else str(cons),
            tuple(h.get("areas") or ()))


def _registrar_ficha(b: Biblioteca, rel: str, dados: Any) -> None:
    if not isinstance(dados, dict):
        b.problemas.append(Problema(rel, "", "a ficha tem de ser um mapa"))
        return
    fid = str(dados.get("id", ""))
    tipo = "conceito" if dados.get("tipo") == "conceito" else "equacao"
    if fid in b.fichas:
        b.problemas.append(Problema(rel, "id", f"repetido (já usado em {b.fichas[fid].arquivo})"))
        return
    b.fichas[fid] = Ficha(fid, tipo, str(dados.get("estado", "")), str(dados.get("area", "")), rel, dados)


# ------------------------------------------------------------------ validação


class _Validador:
    """Acumula problemas de um arquivo, com o caminho do campo."""

    def __init__(self, arquivo: str, prefixo: str, saida: list[Problema]) -> None:
        self.arquivo = arquivo
        self.prefixo = prefixo
        self.saida = saida

    def erro(self, campo: str, msg: str) -> None:
        caminho = ".".join(p for p in (self.prefixo, campo) if p)
        self.saida.append(Problema(self.arquivo, caminho, msg))

    def chaves(self, d: dict[str, Any], permitidas: set[str], campo: str = "") -> None:
        for k in d:
            if k not in permitidas:
                self.erro(campo, f"campo desconhecido: {k}")

    def escolha(self, d: dict[str, Any], k: str, opcoes: Iterable[str], obrigatorio: bool = True) -> None:
        opcoes = tuple(opcoes)
        if k not in d or d[k] is None:
            if obrigatorio:
                self.erro(k, "obrigatório")
            return
        if d[k] not in opcoes:
            self.erro(k, f"valor {d[k]!r} fora de {list(opcoes)}")

    def texto_simples(self, d: dict[str, Any], k: str, obrigatorio: bool = True) -> None:
        v = d.get(k)
        if v is None:
            if obrigatorio:
                self.erro(k, "obrigatório")
        elif not isinstance(v, str) or not v.strip():
            self.erro(k, "esperado texto não vazio")

    def multilingue(self, d: dict[str, Any], k: str, obrigatorio: bool = False) -> bool:
        """Texto por idioma, ``{pt: "..."}``; o português é obrigatório. Devolve se está preenchido."""
        v = d.get(k)
        if v is None:
            if obrigatorio:
                self.erro(k, "obrigatório")
            return False
        if not isinstance(v, dict):
            self.erro(k, "esperado {pt: \"...\"}")
            return False
        for idioma, texto in v.items():
            if idioma not in ("pt", "en"):
                self.erro(k, f"idioma desconhecido: {idioma}")
            elif not isinstance(texto, str):
                self.erro(f"{k}.{idioma}", "esperado texto")
        pt = v.get("pt")
        if not isinstance(pt, str) or not pt.strip() or pt.strip() == "...":
            if obrigatorio:
                self.erro(f"{k}.pt", "obrigatório")
            return False
        return True

    def lista(self, d: dict[str, Any], k: str) -> list[Any]:
        v = d.get(k)
        if v is None:
            return []
        if not isinstance(v, list):
            self.erro(k, "esperada uma lista")
            return []
        return v

    def conferido(self, c: Any, campo: str) -> bool:
        """``{por, em}``: ambos nulos (não conferido) ou ambos preenchidos. Devolve se conferido."""
        if c is None:
            return False
        if not isinstance(c, dict):
            self.erro(campo, "esperado {por, em}")
            return False
        self.chaves(c, {"por", "em"}, campo)
        por, em = c.get("por"), c.get("em")
        if por is None and em is None:
            return False
        if not isinstance(por, str) or not por.strip():
            self.erro(f"{campo}.por", "nome de quem conferiu")
        if not _data_valida(em):
            self.erro(f"{campo}.em", "data AAAA-MM-DD")
        return True


def _data_valida(v: Any) -> bool:
    if isinstance(v, _dt.date):
        return True
    if isinstance(v, str):
        try:
            _dt.date.fromisoformat(v)
            return True
        except ValueError:
            return False
    return False


_COMUNS = {"id", "tipo", "versao", "estado", "area", "titulo", "referencias", "relacionadas",
           "animacao", "revisao"}
_CONCEITO = _COMUNS | {"resumo", "secoes", "variaveis", "equacoes", "exemplos", "tipos", "grupo", "ordem"}
_EQUACAO = _COMUNS | {"equacao", "variaveis", "hipoteses", "validade", "demonstracao", "exemplo"}


def validar(b: Biblioteca) -> list[Problema]:
    """Problemas de esquema de cada ficha e de ligação entre arquivos."""
    out: list[Problema] = []
    for f in b.fichas.values():
        _validar_ficha(b, f, out)
    _validar_tipos(b, out)
    return out


def _validar_ficha(b: Biblioteca, f: Ficha, out: list[Problema]) -> None:
    d = f.dados
    v = _Validador(f.arquivo, "", out)
    conceito = f.tipo == "conceito"
    v.chaves(d, _CONCEITO if conceito else _EQUACAO)
    if d.get("tipo") not in (None, "conceito", "equacao"):
        v.erro("tipo", "esperado 'conceito' ou ausente (ficha de equação)")

    # identidade e lugar do arquivo
    if not _ID.match(f.id):
        v.erro("id", "esperado <area>.<nome> em minúsculas, algarismos e _")
    v.escolha(d, "area", AREAS)
    area, _, nome = f.id.partition(".")
    if d.get("area") in AREAS and area != d.get("area"):
        v.erro("id", f"o prefixo tem de ser a área ({d.get('area')})")
    pasta, _, arquivo = f.arquivo.rpartition("/")
    if pasta != area or Path(arquivo).stem != nome:
        v.erro("id", f"o arquivo tem de ser {area}/{nome}.yaml")
    versao = d.get("versao")
    if not isinstance(versao, int) or isinstance(versao, bool) or versao < 1:
        v.erro("versao", "inteiro a partir de 1")
    v.escolha(d, "estado", ESTADOS)
    v.multilingue(d, "titulo", obrigatorio=True)

    pronta = f.estado in ("auto_verificada", "verificada")
    verificada = f.estado == "verificada"

    refs = _validar_referencias(b, f, v, pronta, verificada)
    if pronta and not refs:
        v.erro("referencias", "pelo menos uma referência fora de rascunho")

    for i, r in enumerate(v.lista(d, "relacionadas")):
        if r not in b.fichas:
            v.erro(f"relacionadas[{i}]", f"ficha inexistente: {r}")

    if conceito:
        _validar_conceito(b, f, v, pronta)
    else:
        _validar_equacao(b, f, v, pronta, verificada)

    rev = d.get("revisao")
    if rev is not None and not isinstance(rev, dict):
        v.erro("revisao", "esperado um mapa")
        rev = None
    rev = rev or {}
    v.chaves(rev, {"automatica", "humana", "externo"}, "revisao")
    humana = v.conferido(rev.get("humana"), "revisao.humana")
    if verificada and not humana:
        v.erro("revisao.humana", "obrigatória no estado verificada (quem conferiu e quando)")
    externo = rev.get("externo")
    if externo is not None and (not isinstance(externo, str) or not externo.strip()):
        v.erro("revisao.externo", "nome do professor revisor, ou nulo")


def _validar_referencias(b: Biblioteca, f: Ficha, v: _Validador, pronta: bool, verificada: bool) -> int:
    n = 0
    for i, r in enumerate(v.lista(f.dados, "referencias")):
        campo = f"referencias[{i}]"
        if not isinstance(r, dict):
            v.erro(campo, "esperado um mapa")
            continue
        n += 1
        v.chaves(r, {"fonte", "uso", "volume", "capitulo", "secao", "equacao", "pagina",
                     "adaptacao", "conferido"}, campo)
        fonte = b.fontes.get(str(r.get("fonte")))
        if fonte is None:
            v.erro(f"{campo}.fonte", f"fonte fora de _fontes.yaml: {r.get('fonte')}")
        uso = r.get("uso", "citacao")
        if uso not in _USOS:
            v.erro(f"{campo}.uso", f"valor {uso!r} fora de {list(_USOS)}")
        if uso == "adaptacao":
            if fonte is not None and fonte.licenca not in LICENCAS_ADAPTAVEIS:
                v.erro(f"{campo}.uso", f"a fonte {fonte.id} não tem licença que permita adaptar")
            tem = v.multilingue(r, "adaptacao")
            if pronta and not tem:
                v.erro(f"{campo}.adaptacao", "diga o que veio da obra e o que foi mudado (seção 8.6)")
        elif r.get("adaptacao") is not None:
            v.erro(f"{campo}.adaptacao", "só com uso: adaptacao")
        conferido = v.conferido(r.get("conferido"), f"{campo}.conferido")
        if verificada and not conferido:
            v.erro(f"{campo}.conferido", "obrigatório no estado verificada (D-05)")
        # D-05: número de equação ou de página só depois da conferência
        for k in ("equacao", "pagina"):
            if r.get(k) is not None and not conferido:
                v.erro(f"{campo}.{k}", "só preenchido junto com a conferência (D-05)")
    return n


def _validar_conceito(b: Biblioteca, f: Ficha, v: _Validador, pronta: bool) -> None:
    from amsior.biblioteca.blocos import validar_blocos, verificar_texto_corrido

    d = f.dados
    # o resumo é a resposta em poucas linhas, em caixa no topo: também é uma lista de blocos
    if d.get("resumo") is not None:
        validar_blocos(d["resumo"], "resumo", v.erro, b.raiz, profundidade=1)
    elif pronta:
        v.erro("resumo", "obrigatório fora de rascunho")
    secoes = v.lista(d, "secoes")
    if pronta and not secoes:
        v.erro("secoes", "pelo menos uma seção fora de rascunho")
    for i, s in enumerate(secoes):
        campo = f"secoes[{i}]"
        if not isinstance(s, dict):
            v.erro(campo, "esperado um mapa")
            continue
        v.chaves(s, {"titulo", "blocos"}, campo)
        _Validador(f.arquivo, campo, v.saida).multilingue(s, "titulo", obrigatorio=True)
        validar_blocos(s.get("blocos"), f"{campo}.blocos", v.erro, b.raiz)
    # tabela de variáveis: símbolo e grandeza; nome e unidade vêm do glossário
    for i, var in enumerate(v.lista(d, "variaveis")):
        campo = f"variaveis[{i}]"
        if not isinstance(var, dict) or not isinstance(var.get("simbolo"), str):
            v.erro(campo, "esperado {simbolo, grandeza}")
            continue
        v.chaves(var, {"simbolo", "grandeza", "nome", "nota"}, campo)
        if b.glossario is not None and var.get("grandeza") not in b.glossario:
            v.erro(f"{campo}.grandeza", f"grandeza fora do glossário: {var.get('grandeza')}")
        for chave in ("nome", "nota"):
            if chave in var:
                _Validador(f.arquivo, campo, v.saida).multilingue(var, chave, obrigatorio=True)
                if isinstance(var[chave], dict) and isinstance(var[chave].get("pt"), str):
                    verificar_texto_corrido(var[chave]["pt"], f"{campo}.{chave}", v.erro)
    for i, e in enumerate(v.lista(d, "equacoes")):
        _ligacao(b, f, v, f"equacoes[{i}]", e, "equacao")
    for i, ex in enumerate(v.lista(d, "exemplos")):
        campo = f"exemplos[{i}]"
        if not isinstance(ex, dict):
            v.erro(campo, "esperado um mapa")
            continue
        v.chaves(ex, {"enunciado", "usa", "equacao", "simbolos", "dados", "pede", "esperado",
                      "passos", "tolerancia_rel"}, campo)
        _Validador(f.arquivo, campo, v.saida).multilingue(ex, "enunciado", obrigatorio=True)
        if isinstance(ex.get("enunciado"), dict) and isinstance(ex["enunciado"].get("pt"), str):
            verificar_texto_corrido(ex["enunciado"]["pt"], f"{campo}.enunciado", v.erro)
        # a conta vem de uma ficha de equação (usa) ou é uma equação escrita na própria ficha
        if ("usa" in ex) == ("equacao" in ex):
            v.erro(campo, "exatamente um de usa (ficha de equação) ou equacao (LaTeX)")
        elif "usa" in ex:
            _ligacao(b, f, v, f"{campo}.usa", ex.get("usa"), "equacao")
        elif not isinstance(ex.get("equacao"), str) or not ex["equacao"].strip():
            v.erro(f"{campo}.equacao", "LaTeX da equação")
        for k, s_ in enumerate(v.lista(ex, "simbolos")):
            if not isinstance(s_, dict) or not isinstance(s_.get("simbolo"), str):
                v.erro(f"{campo}.simbolos[{k}]", "esperado {simbolo, grandeza}")
            elif b.glossario is not None and s_.get("grandeza") not in b.glossario:
                v.erro(f"{campo}.simbolos[{k}].grandeza", f"grandeza fora do glossário: {s_.get('grandeza')}")
        if not isinstance(ex.get("pede"), str):
            v.erro(f"{campo}.pede", "símbolo pedido")
        esp = ex.get("esperado")
        if esp is not None and (not isinstance(esp, list) or not all(isinstance(e, str) for e in esp)):
            v.erro(f"{campo}.esperado", "lista de resultados em LaTeX, como o motor os escreve")
        if pronta and "equacao" in ex and esp is None:
            v.erro(f"{campo}.esperado", "obrigatório fora de rascunho: é o que o motor confere")
        if "passos" in ex and not isinstance(ex["passos"], bool):
            v.erro(f"{campo}.passos", "verdadeiro (com passos) ou falso (resultado sem passos)")
    tipos = v.lista(d, "tipos")
    if tipos and f.area != "matematica":
        v.erro("tipos", "só fichas de Matemática explicam tipos de equação (D-12)")
    from amsior.rules.classificar import CHAVES

    for i, t in enumerate(tipos):
        if t not in CHAVES:
            v.erro(f"tipos[{i}]", f"tipo desconhecido: {t}")
    ordem = d.get("ordem")
    if ordem is not None and (not isinstance(ordem, int) or isinstance(ordem, bool) or ordem < 1):
        v.erro("ordem", "inteiro a partir de 1")
    grupo = d.get("grupo")
    if grupo is not None and not isinstance(grupo, dict):
        v.erro("grupo", "esperado {pt: \"...\"}")
    _validar_animacao(v, d.get("animacao"))


def _validar_equacao(b: Biblioteca, f: Ficha, v: _Validador, pronta: bool, verificada: bool) -> None:
    d = f.dados
    latex = d.get("equacao")
    variaveis = v.lista(d, "variaveis")
    hipoteses = v.lista(d, "hipoteses")
    if pronta:
        if not isinstance(latex, str) or not latex.strip():
            v.erro("equacao", "obrigatória fora de rascunho")
        if not variaveis:
            v.erro("variaveis", "obrigatórias fora de rascunho")
        if not hipoteses:
            v.erro("hipoteses", "pelo menos uma hipótese do vocabulário fora de rascunho")
    for i, h in enumerate(hipoteses):
        if h not in b.hipoteses:
            v.erro(f"hipoteses[{i}]", f"hipótese fora de _hipoteses.yaml: {h}")
    for i, var in enumerate(variaveis):
        campo = f"variaveis[{i}]"
        if not isinstance(var, dict):
            v.erro(campo, "esperado um mapa")
            continue
        v.chaves(var, {"simbolo", "grandeza", "unidade_si", "faixa", "constante", "nome"}, campo)
        if not isinstance(var.get("simbolo"), str) or not var["simbolo"].strip():
            v.erro(f"{campo}.simbolo", "obrigatório")
        g = str(var.get("grandeza"))
        if b.glossario is not None and g not in b.glossario:
            v.erro(f"{campo}.grandeza", f"grandeza fora do glossário: {g}")
        elif b.glossario is not None and var.get("unidade_si") is not None \
                and str(var["unidade_si"]) != b.glossario[g].unidade_si:
            v.erro(f"{campo}.unidade_si", f"o glossário dá {b.glossario[g].unidade_si} para {g}")
    if isinstance(latex, str) and latex.strip() and variaveis:
        _conferir_equacao(b, v, latex, variaveis)
    dem = d.get("demonstracao")
    if isinstance(dem, dict):
        v.chaves(dem, {"parte_de", "passos"}, "demonstracao")
        for i, p in enumerate(v.lista(dem, "parte_de")):
            _ligacao(b, f, v, f"demonstracao.parte_de[{i}]", p, None)
    elif dem is not None:
        v.erro("demonstracao", "esperado um mapa")
    ex = d.get("exemplo")
    if isinstance(ex, dict):
        v.chaves(ex, {"dados", "origem_dos_dados", "pede", "esperado", "tolerancia_rel",
                      "comparacao_independente"}, "exemplo")
        if pronta and not isinstance(ex.get("pede"), str):
            v.erro("exemplo.pede", "símbolo pedido")
        if verificada and ex.get("esperado") is None:
            v.erro("exemplo.esperado", "congelado na revisão humana (seção 8.5)")
    elif ex is not None:
        v.erro("exemplo", "esperado um mapa")
    elif pronta:
        v.erro("exemplo", "obrigatório fora de rascunho")
    val = d.get("validade")
    if isinstance(val, dict):
        v.chaves(val, {"texto", "limites"}, "validade")
        v.multilingue(val, "texto")
    elif val is not None:
        v.erro("validade", "esperado um mapa")
    _validar_animacao(v, d.get("animacao"))


def _conferir_equacao(b: Biblioteca, v: _Validador, latex: str, variaveis: list[Any]) -> None:
    """A equação se lê sem ambiguidade e usa exatamente os símbolos declarados."""
    from amsior.erros import ErroAmsior
    from amsior.expr.analisador import analisar
    from amsior.expr.nos import Sym
    from amsior.expr.simbolos import Simbolo, TabelaDeSimbolos
    from amsior.verify.arvore import livres

    declarados: list[Simbolo] = []
    for var in variaveis:
        if not isinstance(var, dict) or not isinstance(var.get("simbolo"), str):
            return
        try:
            lido = analisar(var["simbolo"])
        except ErroAmsior as erro_simbolo:
            v.erro("variaveis", f"símbolo ilegível {var['simbolo']!r}: {erro_simbolo}")
            return
        if not isinstance(lido, Sym):
            v.erro("variaveis", f"{var['simbolo']!r} não é um símbolo só")
            return
        g = str(var.get("grandeza"))
        if b.glossario is not None and g in b.glossario:
            papel: Literal["variavel", "constante"] = "constante" if var.get("constante") else "variavel"
            declarados.append(b.glossario.simbolo(lido.id, g, papel=papel))
        else:
            declarados.append(Simbolo(lido.id))
    try:
        arvore = analisar(latex, TabelaDeSimbolos.de(declarados))
    except ErroAmsior as erro:
        v.erro("equacao", f"não se lê sem ambiguidade: {erro}")
        return
    usados = set(livres(arvore))
    ids = {s.id for s in declarados}
    for sid in sorted(usados - ids):
        v.erro("equacao", f"símbolo sem declaração em variaveis: {sid}")
    for sid in sorted(ids - usados):
        v.erro("variaveis", f"declarado e ausente da equação: {sid}")


def _ligacao(b: Biblioteca, f: Ficha, v: _Validador, campo: str, alvo: Any, tipo: str | None) -> None:
    """Uma ficha visível só aponta para fichas que existem e que o aluno também vê."""
    if not isinstance(alvo, str):
        v.erro(campo, "id de uma ficha")
        return
    destino = b.fichas.get(alvo)
    if destino is None:
        v.erro(campo, f"ficha inexistente: {alvo}")
        return
    if tipo is not None and destino.tipo != tipo:
        v.erro(campo, f"{alvo} é ficha de {destino.tipo}, esperada de {tipo}")
    if f.visivel and not destino.visivel:
        v.erro(campo, f"{alvo} ainda é rascunho; uma ficha visível não pode depender dela")


def _validar_animacao(v: _Validador, a: Any) -> None:
    if a is None:
        return
    if not isinstance(a, dict):
        v.erro("animacao", "esperado {cena, interativa}")
        return
    v.chaves(a, {"cena", "interativa"}, "animacao")


def _validar_tipos(b: Biblioteca, out: list[Problema]) -> None:
    """Cada tipo de equação (D-12) é explicado por no máximo uma ficha."""
    dono: dict[str, str] = {}
    for f in b.fichas.values():
        for t in f.dados.get("tipos") or ():
            if t in dono:
                out.append(Problema(f.arquivo, "tipos", f"{t} já é explicado por {dono[t]}"))
            else:
                dono[t] = f.id


def tipos_sem_ficha(b: Biblioteca) -> list[str]:
    """Tipos de equação que ainda não levam a nenhuma ficha (critério da fase 2)."""
    from amsior.rules.classificar import CHAVES

    return [c for c in CHAVES if b.ficha_do_tipo(c) is None]


def iterar_textos(f: Ficha) -> Iterator[tuple[str, str]]:
    """Todos os textos em português da ficha, com o campo; para revisão e busca."""
    def rec(x: Any, caminho: str) -> Iterator[tuple[str, str]]:
        if isinstance(x, dict):
            if "pt" in x and isinstance(x["pt"], str):
                yield caminho, x["pt"]
            for k, y in x.items():
                if k not in ("pt", "en"):
                    yield from rec(y, f"{caminho}.{k}" if caminho else str(k))
        elif isinstance(x, list):
            for i, y in enumerate(x):
                yield from rec(y, f"{caminho}[{i}]")
    yield from rec(f.dados, "")
