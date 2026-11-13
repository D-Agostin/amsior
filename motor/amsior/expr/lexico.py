# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Analisador léxico do LaTeX restrito do Amsior.

Produz uma lista de tokens. Cada token registra se havia espaço antes dele,
porque espaços separam palavras: ``P V`` são dois símbolos, ``PV`` é uma
palavra que precisa ser resolvida pela tabela de símbolos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from amsior.erros import ErroDeAnalise

TipoToken = Literal["NUM", "LETRA", "CMD", "OP", "ABRE", "FECHA", "LCH", "RCH", "FIM"]

# comandos cujo argumento entre chaves é lido como texto cru
COMANDOS_TEXTO = frozenset(
    {"\\mathrm", "\\text", "\\textrm", "\\operatorname", "\\mathit", "\\textit"}
)
ESPACAMENTO = frozenset(
    {"\\,", "\\;", "\\:", "\\!", "\\ ", "\\quad", "\\qquad", "\\thinspace", "\\enspace"}
)
TAMANHOS = frozenset(
    {"\\big", "\\Big", "\\bigg", "\\Bigg", "\\bigl", "\\bigr", "\\Bigl", "\\Bigr",
     "\\biggl", "\\biggr", "\\Biggl", "\\Biggr"}
)

UNICODE = {
    "−": "-", "–": "-", "·": "\\cdot", "⋅": "\\cdot", "×": "\\times", "≠": "\\neq",
    "≥": "\\geq", "≤": "\\leq", "∫": "\\int", "∂": "\\partial", "°": "\\circ",
    "′": "'", "π": "\\pi", "Δ": "\\Delta", "α": "\\alpha", "β": "\\beta",
    "γ": "\\gamma", "δ": "\\delta", "ε": "\\varepsilon", "η": "\\eta", "θ": "\\theta",
    "κ": "\\kappa", "λ": "\\lambda", "μ": "\\mu", "ν": "\\nu", "ξ": "\\xi",
    "ρ": "\\rho", "σ": "\\sigma", "τ": "\\tau", "φ": "\\phi", "χ": "\\chi",
    "ψ": "\\psi", "ω": "\\omega", "Γ": "\\Gamma", "Θ": "\\Theta", "Λ": "\\Lambda",
    "Π": "\\Pi", "Σ": "\\Sigma", "Φ": "\\Phi", "Ψ": "\\Psi", "Ω": "\\Omega",
}


@dataclass
class Token:
    tipo: TipoToken
    texto: str
    pos: int
    espaco_antes: bool = False
    conteudo: str | None = None  # texto cru de \mathrm{...} e afins
    extra: dict[str, str] = field(default_factory=dict)

    def eh(self, tipo: TipoToken, texto: str | None = None) -> bool:
        return self.tipo == tipo and (texto is None or self.texto == texto)


def _ler_chaves_cruas(fonte: str, i: int) -> tuple[str, int]:
    """Lê ``{...}`` a partir de ``fonte[i]`` e devolve (conteúdo, índice após)."""
    while i < len(fonte) and fonte[i] == " ":
        i += 1
    if i >= len(fonte) or fonte[i] != "{":
        raise ErroDeAnalise("erro.analise.esperava_chave", i)
    prof = 0
    inicio = i + 1
    while i < len(fonte):
        c = fonte[i]
        if c == "\\" and i + 1 < len(fonte):
            i += 2
            continue
        if c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if prof == 0:
                return fonte[inicio:i], i + 1
        i += 1
    raise ErroDeAnalise("erro.analise.chave_sem_fechar", inicio - 1)


def tokenizar(fonte: str) -> list[Token]:
    for de, para in UNICODE.items():
        if de in fonte:
            fonte = fonte.replace(de, para if not para.startswith("\\") else para + " ")
    tokens: list[Token] = []
    i = 0
    espaco = False
    n = len(fonte)

    def emitir(tipo: TipoToken, texto: str, pos: int, **kw: str | None) -> None:
        nonlocal espaco
        conteudo = kw.pop("conteudo", None)
        tokens.append(Token(tipo, texto, pos, espaco, conteudo))
        espaco = False

    def apos_script() -> bool:
        return bool(tokens) and tokens[-1].tipo == "OP" and tokens[-1].texto in ("^", "_")

    while i < n:
        c = fonte[i]
        if c.isspace():
            espaco = True
            i += 1
            continue
        if c == "\\":
            j = i + 1
            if j < n and fonte[j].isalpha():
                while j < n and fonte[j].isalpha():
                    j += 1
                nome = fonte[i:j]
            else:
                nome = fonte[i : j + 1]
                j += 1
            if nome in ESPACAMENTO:
                espaco = True
                i = j
                continue
            if nome in ("\\left", "\\right") or nome in TAMANHOS:
                k = j
                while k < n and fonte[k] == " ":
                    k += 1
                if k >= n:
                    raise ErroDeAnalise("erro.analise.delimitador_ausente", i)
                abre = nome == "\\left" or nome.endswith("l")
                if nome in TAMANHOS and nome[-1] not in "lr":
                    abre = fonte[k] in "([{" or fonte[k : k + 2] == "\\{"
                if fonte[k] == ".":
                    i = k + 1
                    continue
                if fonte[k] == "\\":
                    m = k + 1
                    while m < n and fonte[m].isalpha():
                        m += 1
                    if m == k + 1:
                        m += 1
                    delim = fonte[k:m]
                    k_fim = m
                else:
                    delim = fonte[k]
                    k_fim = k + 1
                mapa = {"\\{": "{", "\\}": "}", "\\lvert": "|", "\\rvert": "|",
                        "\\vert": "|", "\\|": "|", "\\langle": "(", "\\rangle": ")"}
                delim = mapa.get(delim, delim)
                if delim == "|":
                    emitir("ABRE" if abre else "FECHA", "|", i)
                elif delim in "([{":
                    emitir("ABRE", delim, i)
                elif delim in ")]}":
                    emitir("FECHA", delim, i)
                else:
                    raise ErroDeAnalise("erro.analise.delimitador_invalido", i, delim=delim)
                i = k_fim
                continue
            if nome in ("\\{", "\\lbrace"):
                emitir("ABRE", "{", i)
                i = j
                continue
            if nome in ("\\}", "\\rbrace"):
                emitir("FECHA", "}", i)
                i = j
                continue
            if nome == "\\lvert":
                emitir("ABRE", "|", i)
                i = j
                continue
            if nome == "\\rvert":
                emitir("FECHA", "|", i)
                i = j
                continue
            if nome in COMANDOS_TEXTO:
                conteudo, j = _ler_chaves_cruas(fonte, j)
                emitir("CMD", "\\mathrm", i, conteudo=conteudo.strip())
                i = j
                continue
            if nome == "\\\\" or nome == "\\&":
                raise ErroDeAnalise("erro.analise.comando_nao_suportado", i, comando=nome)
            emitir("CMD", nome, i)
            i = j
            continue
        if c.isdigit():
            if apos_script():
                emitir("NUM", c, i)
                i += 1
                continue
            j = i
            while j < n and fonte[j].isdigit():
                j += 1
            texto = fonte[i:j]
            if j < n and fonte[j] in ",." and j + 1 < n and fonte[j + 1].isdigit():
                k = j + 1
                while k < n and fonte[k].isdigit():
                    k += 1
                texto = texto + "." + fonte[j + 1 : k]
                j = k
            elif fonte.startswith("{,}", j) and j + 3 < n and fonte[j + 3].isdigit():
                k = j + 3
                while k < n and fonte[k].isdigit():
                    k += 1
                texto = texto + "." + fonte[j + 3 : k]
                j = k
            emitir("NUM", texto, i)
            i = j
            continue
        if c.isalpha():
            emitir("LETRA", c, i)
            i += 1
            continue
        if c in "([":
            emitir("ABRE", c, i)
        elif c in ")]":
            emitir("FECHA", c, i)
        elif c == "{":
            emitir("LCH", c, i)
        elif c == "}":
            emitir("RCH", c, i)
        elif c in "+-*/=<>^_',;|!":
            emitir("OP", c, i)
        else:
            raise ErroDeAnalise("erro.analise.caractere_invalido", i, caractere=c)
        i += 1
    tokens.append(Token("FIM", "", n, espaco))
    return tokens
