# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Analisador do LaTeX restrito do Amsior: texto → AmsiorExpr.

Analisador descendente recursivo escrito à mão (ver docs/decisoes/0001). A
gramática formal está em docs/gramatica.md. Regras que dependem de contexto:

* Palavras (letras coladas, como ``PV``) são resolvidas pela tabela de
  símbolos; sem resolução única, o analisador não adivinha e levanta
  ``AmbiguidadeDeSimbolo``.
* ``\\mathrm{d}x`` (ou ``dx`` colado) dentro de uma integral fecha o integrando.
* ``\\frac{dy}{dt}`` só é derivada quando numerador e denominador seguem o
  padrão de diferencial; ``\\frac{d}{t}`` continua sendo uma divisão.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from amsior.erros import AmbiguidadeDeSimbolo, ErroDeAnalise
from amsior.expr.lexico import Token, tokenizar
from amsior.expr.nos import (
    Abs, Add, Cos, Deriv, Div, Eq, Exp, Expr, Func, Ge, Gt, Integral, Le, Ln, Log, Lt,
    Mul, Ne, Neg, Num, PDeriv, Pow, Root, Sin, Sqrt, Sub, Sym, Tan,
)
from amsior.expr.simbolos import TabelaDeSimbolos

ModoPalavras = Literal["perguntar", "produto"]

GREGAS = frozenset(
    "\\" + g
    for g in (
        "alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa "
        "lambda mu nu xi rho varrho sigma tau upsilon phi varphi chi psi omega "
        "Gamma Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega pi ell infty"
    ).split()
)
DECORACOES = {
    "\\dot": "\\dot", "\\ddot": "\\ddot", "\\bar": "\\bar", "\\overline": "\\bar",
    "\\hat": "\\hat", "\\tilde": "\\tilde", "\\vec": "\\vec",
}
FUNCOES = {"\\ln", "\\exp", "\\sin", "\\cos", "\\tan", "\\log"}
FRACOES = {"\\frac", "\\dfrac", "\\tfrac"}
MUL_EXPLICITA = {"\\cdot", "\\times"}
RELACOES_OP = {"=": Eq, "<": Lt, ">": Gt}
RELACOES_CMD = {
    "\\neq": Ne, "\\ne": Ne, "\\geq": Ge, "\\ge": Ge, "\\leq": Le, "\\le": Le,
    "\\gt": Gt, "\\lt": Lt, "\\geqslant": Ge, "\\leqslant": Le,
}
PARES = {"(": ")", "[": "]", "{": "}", "|": "|"}


def _mk_add(termos: list[Expr]) -> Expr:
    return termos[0] if len(termos) == 1 else Add(tuple(termos))


def _mk_mul(fatores: list[Expr]) -> Expr:
    return fatores[0] if len(fatores) == 1 else Mul(tuple(fatores))


@dataclass
class _CtxIntegral:
    prof: int
    var: Sym | None = None
    fim: bool = False


class Analisador:
    def __init__(
        self,
        tokens: list[Token],
        tabela: TabelaDeSimbolos | None = None,
        modo_palavras: ModoPalavras = "perguntar",
    ) -> None:
        self.t = tokens
        self.i = 0
        self.tabela = tabela if tabela is not None else TabelaDeSimbolos()
        self.modo = modo_palavras
        self.integrais: list[_CtxIntegral] = []
        self.prof = 0
        self.abs_prof = 0

    # ------------------------------------------------------------ utilidades

    @property
    def atual(self) -> Token:
        return self.t[self.i]

    def ver(self, k: int = 1) -> Token:
        j = min(self.i + k, len(self.t) - 1)
        return self.t[j]

    def avancar(self) -> Token:
        tok = self.t[self.i]
        if tok.tipo != "FIM":
            self.i += 1
        return tok

    def erro(self, chave: str, tok: Token | None = None, **args: object) -> ErroDeAnalise:
        tok = tok or self.atual
        if tok.tipo == "FIM" and chave == "erro.analise.token_inesperado":
            chave = "erro.analise.fim_inesperado"
        return ErroDeAnalise(chave, tok.pos, token=tok.texto, **args)

    def esperar(self, tipo: str, texto: str | None = None) -> Token:
        tok = self.atual
        if tok.tipo != tipo or (texto is not None and tok.texto != texto):
            raise self.erro("erro.analise.esperava", esperado=texto or tipo)
        return self.avancar()

    def _filho(self, tokens: list[Token]) -> Analisador:
        fim = Token("FIM", "", tokens[-1].pos + 1 if tokens else self.atual.pos)
        return Analisador(tokens + [fim], self.tabela, self.modo)

    def _parar(self) -> bool:
        return bool(self.integrais) and self.integrais[-1].fim

    # ------------------------------------------------------------ gramática

    def analisar(self) -> Expr:
        e = self.relacao()
        if self.atual.tipo != "FIM":
            raise self.erro("erro.analise.sobrou_entrada")
        return e

    def relacao(self) -> Expr:
        esq = self.expr()
        tok = self.atual
        cls = None
        if tok.tipo == "OP":
            cls = RELACOES_OP.get(tok.texto)
        elif tok.tipo == "CMD":
            cls = RELACOES_CMD.get(tok.texto)
        if cls is None:
            return esq
        self.avancar()
        dir_ = self.expr()
        return cls(esq, dir_)

    def expr(self) -> Expr:
        pendente = [self.termo_com_sinal()]
        while not self._parar():
            tok = self.atual
            if tok.eh("OP", "+"):
                self.avancar()
                pendente.append(self.termo_com_sinal())
            elif tok.eh("OP", "-"):
                self.avancar()
                acc = _mk_add(pendente)
                pendente = [Sub(acc, self.termo_com_sinal())]
            else:
                break
        return _mk_add(pendente)

    def termo_com_sinal(self) -> Expr:
        if self.atual.eh("OP", "-"):
            self.avancar()
            return Neg(self.produto())
        if self.atual.eh("OP", "+"):
            self.avancar()
        return self.produto()

    def produto(self) -> Expr:
        fatores: list[Expr] = list(self.potencia())
        while not self._parar():
            if self._tentar_diferencial():
                break
            tok = self.atual
            if (tok.tipo == "CMD" and tok.texto in MUL_EXPLICITA) or tok.eh("OP", "*"):
                self.avancar()
                fatores.extend(self.potencia())
            elif tok.eh("OP", "/"):
                self.avancar()
                den = self._unico(self.potencia())
                fatores = [Div(_mk_mul(fatores), den)]
            elif self._inicia_fator(tok):
                fatores.extend(self.potencia())
            else:
                break
        return _mk_mul(fatores)

    def _inicia_fator(self, tok: Token) -> bool:
        if tok.tipo in ("NUM", "LETRA", "LCH"):
            return True
        if tok.tipo == "ABRE":
            return True
        if tok.eh("OP", "|"):
            return self.abs_prof == 0
        if tok.tipo == "CMD":
            if tok.texto == "\\mathrm" and tok.conteudo == "d":
                return False
            return (
                tok.texto in GREGAS or tok.texto in DECORACOES or tok.texto in FUNCOES
                or tok.texto in FRACOES
                or tok.texto in ("\\Delta", "\\mathrm", "\\sqrt", "\\int", "\\Pr")
            )
        return False

    @staticmethod
    def _unico(lista: list[Expr]) -> Expr:
        return _mk_mul(lista)

    def potencia(self) -> list[Expr]:
        itens = self.atomo()
        if not self._parar() and self.atual.eh("OP", "^"):
            self.avancar()
            exp = self.grupo_ou_unidade()
            itens = itens[:-1] + [Pow(itens[-1], exp)]
        return itens

    def grupo_ou_unidade(self) -> Expr:
        tok = self.atual
        if tok.tipo == "LCH":
            self.avancar()
            prof_antes = self.prof
            self.prof += 1
            e = self.expr()
            self.prof = prof_antes
            self.esperar("RCH")
            return e
        if tok.tipo == "NUM":
            self.avancar()
            return Num(tok.texto)
        if tok.tipo == "LETRA":
            self.avancar()
            return Sym(tok.texto)
        if tok.tipo == "CMD" and tok.texto in GREGAS:
            self.avancar()
            return Sym(tok.texto)
        raise self.erro("erro.analise.expoente_invalido")

    def atomo(self) -> list[Expr]:
        tok = self.atual
        if tok.tipo == "NUM":
            self.avancar()
            return [Num(tok.texto)]
        if tok.tipo == "ABRE" and tok.texto in "([{":
            return [self._grupo_parenteses()]
        if tok.tipo == "ABRE" and tok.texto == "|":
            self.avancar()
            prof_antes = self.prof
            self.prof += 1
            e = self.expr()
            self.prof = prof_antes
            self.esperar("FECHA", "|")
            return [Abs(e)]
        if tok.eh("OP", "|"):
            self.avancar()
            prof_antes = self.prof
            self.prof += 1
            self.abs_prof += 1
            e = self.expr()
            self.abs_prof -= 1
            self.prof = prof_antes
            self.esperar("OP", "|")
            return [Abs(e)]
        if tok.tipo == "LCH":
            self.avancar()
            prof_antes = self.prof
            self.prof += 1
            e = self.expr()
            self.prof = prof_antes
            self.esperar("RCH")
            return [e]
        if tok.tipo == "CMD":
            if tok.texto in FRACOES:
                return self.fracao()
            if tok.texto == "\\sqrt":
                return [self.raiz()]
            if tok.texto in FUNCOES:
                return [self.funcao()]
            if tok.texto == "\\int":
                return [self.integral()]
            if tok.texto == "\\mathrm" and tok.conteudo == "e" and self.ver().eh("OP", "^"):
                self.avancar()
                self.avancar()
                return [Exp(self.grupo_ou_unidade())]
            if tok.texto == "\\mathrm" and tok.conteudo == "d":
                raise self.erro("erro.analise.diferencial_fora_de_integral")
            return self.simbolo_ou_palavra()
        if tok.tipo == "LETRA":
            if tok.texto == "e" and self.ver().eh("OP", "^"):
                self.avancar()
                self.avancar()
                return [Exp(self.grupo_ou_unidade())]
            return self.simbolo_ou_palavra()
        raise self.erro("erro.analise.token_inesperado")

    def _grupo_parenteses(self) -> Expr:
        abre = self.avancar()
        prof_antes = self.prof
        self.prof += 1
        e = self.expr()
        self.prof = prof_antes
        fecha = self.atual
        if fecha.tipo != "FECHA" or fecha.texto != PARES[abre.texto]:
            raise self.erro("erro.analise.esperava_fechamento", esperado=PARES[abre.texto])
        self.avancar()
        if isinstance(e, PDeriv) and self.atual.eh("OP", "_") and not e.mantidas:
            self.avancar()
            e = PDeriv(e.f, e.var, self._lista_mantidas(), e.ordem)
        return e

    def _lista_mantidas(self) -> tuple[Sym, ...]:
        toks = self._tokens_do_grupo()
        partes: list[list[Token]] = [[]]
        for tk in toks:
            if tk.eh("OP", ","):
                partes.append([])
            else:
                partes[-1].append(tk)
        resultado: list[Sym] = []
        for parte in partes:
            filho = self._filho(parte)
            resultado.append(filho.simbolo_unico())
            if filho.atual.tipo != "FIM":
                raise filho.erro("erro.analise.simbolo_esperado")
        return tuple(resultado)

    def _tokens_do_grupo(self) -> list[Token]:
        """Tokens de ``{...}`` (sem as chaves) ou de um único token."""
        tok = self.atual
        if tok.tipo != "LCH":
            self.avancar()
            return [tok]
        self.avancar()
        prof = 1
        inicio = self.i
        while True:
            tk = self.atual
            if tk.tipo == "FIM":
                raise self.erro("erro.analise.chave_sem_fechar")
            if tk.tipo == "LCH":
                prof += 1
            elif tk.tipo == "RCH":
                prof -= 1
                if prof == 0:
                    toks = self.t[inicio : self.i]
                    self.avancar()
                    return toks
            self.avancar()

    # ------------------------------------------------------------ símbolos

    def _eh_inicio_simbolo(self, tok: Token) -> bool:
        if tok.tipo == "LETRA":
            return True
        if tok.tipo == "CMD":
            if tok.texto == "\\mathrm":
                return tok.conteudo not in ("d", "e")
            return tok.texto in GREGAS or tok.texto in DECORACOES or tok.texto in (
                "\\Delta", "\\Pr")
        return False

    def _base_cmd(self) -> str:
        tok = self.avancar()
        nome = tok.texto
        if nome in GREGAS:
            return nome
        if nome == "\\Pr":
            return "\\mathrm{Pr}"
        if nome == "\\mathrm":
            conteudo = (tok.conteudo or "").replace(" ", "")
            if not conteudo.isalpha():
                raise ErroDeAnalise("erro.analise.mathrm_invalido", tok.pos, conteudo=conteudo)
            return conteudo if len(conteudo) == 1 else f"\\mathrm{{{conteudo}}}"
        if nome in DECORACOES:
            interno = self.atual
            if interno.tipo == "LCH":
                toks = self._tokens_do_grupo()
                if len(toks) != 1:
                    raise ErroDeAnalise("erro.analise.decoracao_invalida", tok.pos)
                interno = toks[0]
            else:
                self.avancar()
            if interno.tipo == "LETRA" or (interno.tipo == "CMD" and interno.texto in GREGAS):
                return f"{DECORACOES[nome]}{{{interno.texto}}}"
            raise ErroDeAnalise("erro.analise.decoracao_invalida", tok.pos)
        if nome == "\\Delta":
            prox = self.atual
            if prox.tipo == "LETRA":
                self.avancar()
                return f"\\Delta {prox.texto}"
            if prox.tipo == "CMD" and (prox.texto in GREGAS or prox.texto in DECORACOES
                                       or prox.texto == "\\mathrm"):
                return f"\\Delta {self._base_cmd()}"
            raise ErroDeAnalise("erro.analise.delta_sem_simbolo", tok.pos)
        raise ErroDeAnalise("erro.analise.comando_nao_suportado", tok.pos, comando=nome)

    def _sufixos(self) -> str:
        linhas = 0
        sub: str | None = None
        sup: str | None = None
        while True:
            tok = self.atual
            if tok.eh("OP", "'") and not tok.espaco_antes:
                self.avancar()
                linhas += 1
            elif tok.eh("OP", "_") and sub is None:
                self.avancar()
                sub = self._canon_conteudo(self._tokens_do_grupo())
            elif tok.eh("OP", "^") and sup is None and self._eh_rotulo_sobrescrito():
                self.avancar()
                sup = self._canon_rotulo(self._tokens_do_grupo())
                if sup == "\\prime":
                    linhas += 1
                    sup = None
            else:
                break
        partes = "'" * linhas
        if sub is not None:
            partes += f"_{{{sub}}}"
        if sup is not None:
            partes += f"^{{{sup}}}"
        return partes

    def _eh_rotulo_sobrescrito(self) -> bool:
        """``^{\\mathrm{sat}}``, ``^{sat}``, ``^{\\circ}``, ``^{*}`` e ``^{(0)}`` são rótulos;
        ``^{n}``, ``^{2}`` e ``^{a+b}`` são potências."""
        prox = self.ver()
        if prox.tipo != "LCH":
            return self._token_rotulo(prox)
        dentro: list[Token] = []
        k = 2
        while self.ver(k).tipo not in ("RCH", "FIM"):
            dentro.append(self.ver(k))
            k += 1
        if len(dentro) == 1:
            return self._token_rotulo(dentro[0])
        if len(dentro) >= 2 and all(tk.tipo == "LETRA" for tk in dentro) and not any(
                tk.espaco_antes for tk in dentro[1:]):
            return True
        return (len(dentro) == 3 and dentro[0].eh("ABRE", "(") and dentro[1].tipo == "NUM"
                and dentro[2].eh("FECHA", ")"))

    @staticmethod
    def _token_rotulo(tok: Token) -> bool:
        if tok.tipo == "CMD" and tok.texto in ("\\circ", "\\prime", "\\ast", "\\star"):
            return True
        if tok.tipo == "CMD" and tok.texto == "\\mathrm" and tok.conteudo not in ("d", "e"):
            return True
        return tok.eh("OP", "*")

    @staticmethod
    def _canon_rotulo(toks: list[Token]) -> str:
        if len(toks) >= 2 and all(tk.tipo == "LETRA" for tk in toks):
            return "\\mathrm{" + "".join(tk.texto for tk in toks) + "}"
        if len(toks) == 3 and toks[0].eh("ABRE", "("):
            return f"({toks[1].texto})"
        tok = toks[0]
        if tok.eh("OP", "*") or (tok.tipo == "CMD" and tok.texto in ("\\ast", "\\star")):
            return "*"
        if tok.tipo == "CMD" and tok.texto == "\\mathrm":
            return f"\\mathrm{{{(tok.conteudo or '').replace(' ', '')}}}"
        return tok.texto

    @staticmethod
    def _canon_conteudo(toks: list[Token]) -> str:
        partes: list[str] = []
        for k, tok in enumerate(toks):
            if tok.tipo == "CMD" and tok.texto == "\\mathrm":
                partes.append((tok.conteudo or "").strip())
            elif tok.tipo == "CMD":
                seguinte = toks[k + 1] if k + 1 < len(toks) else None
                sep = " " if seguinte is not None and seguinte.tipo == "LETRA" else ""
                partes.append(tok.texto + sep)
            elif tok.tipo == "LCH":
                partes.append("{")
            elif tok.tipo == "RCH":
                partes.append("}")
            else:
                partes.append(tok.texto)
        s = "".join(partes)
        if not s:
            raise ErroDeAnalise("erro.analise.indice_vazio", toks[0].pos if toks else 0)
        if s.isalpha() and len(s) > 1:
            return f"\\mathrm{{{s}}}"
        return s

    def simbolo_unico(self) -> Sym:
        tok = self.atual
        if tok.tipo == "LETRA":
            self.avancar()
            base = tok.texto
        elif self._eh_inicio_simbolo(tok):
            base = self._base_cmd()
        else:
            raise self.erro("erro.analise.simbolo_esperado")
        return Sym(base + self._sufixos())

    def simbolo_ou_palavra(self) -> list[Expr]:
        tok = self.atual
        if tok.tipo == "LETRA":
            letras = [self.avancar().texto]
            while self.atual.tipo == "LETRA" and not self.atual.espaco_antes:
                if self.integrais and self.atual.texto == "d" and self._diferencial_colado():
                    break
                if self.atual.texto == "e" and self.ver().eh("OP", "^"):
                    break  # "Ae^{x}" é A·exp(x), não o símbolo e elevado
                letras.append(self.avancar().texto)
            sufixo = self._sufixos()
            ids = self._resolver_palavra("".join(letras), sufixo, tok.pos)
        else:
            base = self._base_cmd()
            ids = [base + self._sufixos()]
        itens: list[Expr] = [Sym(x) for x in ids]
        if (self.tabela.eh_funcao(ids[-1]) and self.atual.eh("ABRE", "(")
                and not self.atual.espaco_antes):
            itens[-1] = self._aplicacao(ids[-1])
        return itens

    def _diferencial_colado(self) -> bool:
        """Há um ``d`` seguido de símbolo colado na posição atual, no corpo da integral."""
        ctx = self.integrais[-1]
        if ctx.prof != self.prof:
            return False
        prox = self.ver()
        return self._eh_inicio_simbolo(prox) and not prox.espaco_antes

    def _aplicacao(self, nome: str) -> Func:
        self.avancar()
        prof_antes = self.prof
        self.prof += 1
        args = [self.expr()]
        while self.atual.eh("OP", ";"):
            self.avancar()
            args.append(self.expr())
        self.prof = prof_antes
        self.esperar("FECHA", ")")
        return Func(nome, tuple(args))

    def _resolver_palavra(self, letras: str, sufixo: str, pos: int) -> list[str]:
        if len(letras) == 1:
            return [letras + sufixo]
        conhecidas = self.tabela.palavras_conhecidas()
        if letras in conhecidas:
            return [f"\\mathrm{{{letras}}}{sufixo}"]
        segs = self._segmentacoes(letras, conhecidas)
        if len(segs) == 1:
            pecas = segs[0]
        elif self.modo == "produto" and not segs:
            pecas = list(letras)
        else:
            opcoes = [f"\\mathrm{{{letras}}}{sufixo}", " ".join(list(letras[:-1]) + [letras[-1] + sufixo])]
            for s in segs:
                txt = " ".join(p if len(p) == 1 else f"\\mathrm{{{p}}}" for p in s)
                if txt not in opcoes:
                    opcoes.append(txt)
            raise AmbiguidadeDeSimbolo(pos, letras, opcoes)
        ids = [p if len(p) == 1 else f"\\mathrm{{{p}}}" for p in pecas]
        ids[-1] += sufixo
        return ids

    @staticmethod
    def _segmentacoes(letras: str, conhecidas: set[str], limite: int = 8) -> list[list[str]]:
        resultados: list[list[str]] = []

        def busca(i: int, atual: list[str]) -> None:
            if len(resultados) >= limite:
                return
            if i == len(letras):
                resultados.append(list(atual))
                return
            for j in range(len(letras), i, -1):
                peca = letras[i:j]
                if peca in conhecidas:
                    atual.append(peca)
                    busca(j, atual)
                    atual.pop()

        busca(0, [])
        return resultados

    # ------------------------------------------------------------ construções

    def raiz(self) -> Expr:
        self.avancar()
        indice: Expr | None = None
        if self.atual.eh("ABRE", "["):
            self.avancar()
            prof_antes = self.prof
            self.prof += 1
            indice = self.expr()
            self.prof = prof_antes
            self.esperar("FECHA", "]")
        arg = self.grupo_ou_unidade()
        return Sqrt(arg) if indice is None else Root(arg, indice)

    def funcao(self) -> Expr:
        tok = self.avancar()
        potencia: Expr | None = None
        base_log: Expr | None = None
        while True:
            if self.atual.eh("OP", "^") and potencia is None:
                self.avancar()
                potencia = self.grupo_ou_unidade()
            elif self.atual.eh("OP", "_") and tok.texto == "\\log" and base_log is None:
                self.avancar()
                base_log = self.grupo_ou_unidade()
            else:
                break
        prox = self.atual
        if prox.tipo == "ABRE" and prox.texto in "([" or prox.tipo == "LCH":
            arg = self._unico(self.atomo())
        elif prox.tipo == "FIM" or not self._inicia_fator(prox):
            raise self.erro("erro.analise.argumento_ausente", funcao=tok.texto)
        else:
            arg = self._unico(self.potencia())
        no: Expr
        if tok.texto == "\\ln":
            no = Ln(arg)
        elif tok.texto == "\\log":
            no = Log(arg, base_log if base_log is not None else Num("10"))
        elif tok.texto == "\\exp":
            no = Exp(arg)
        elif tok.texto == "\\sin":
            no = Sin(arg)
        elif tok.texto == "\\cos":
            no = Cos(arg)
        else:
            no = Tan(arg)
        return Pow(no, potencia) if potencia is not None else no

    def integral(self) -> Expr:
        tok = self.avancar()
        inferior: Expr | None = None
        superior: Expr | None = None
        for _ in range(2):
            if self.atual.eh("OP", "_") and inferior is None:
                self.avancar()
                inferior = self.grupo_ou_unidade()
            elif self.atual.eh("OP", "^") and superior is None:
                self.avancar()
                superior = self.grupo_ou_unidade()
        ctx = _CtxIntegral(prof=self.prof)
        self.integrais.append(ctx)
        try:
            corpo: Expr = Num("1") if self._tentar_diferencial() else self.expr()
        finally:
            self.integrais.pop()
        if ctx.var is None:
            raise ErroDeAnalise("erro.analise.integral_sem_diferencial", tok.pos)
        return Integral(corpo, ctx.var, inferior, superior)

    def _tentar_diferencial(self) -> bool:
        if not self.integrais:
            return False
        ctx = self.integrais[-1]
        if ctx.prof != self.prof or ctx.fim:
            return False
        tok = self.atual
        prox = self.ver()
        eh_d = (tok.tipo == "CMD" and tok.texto == "\\mathrm" and tok.conteudo == "d") or (
            tok.eh("LETRA", "d") and not prox.espaco_antes
        )
        if not eh_d or not self._eh_inicio_simbolo(prox):
            return False
        self.avancar()
        ctx.var = self.simbolo_unico()
        ctx.fim = True
        return True

    def fracao(self) -> list[Expr]:
        tok = self.avancar()
        if self.atual.tipo != "LCH":
            raise ErroDeAnalise("erro.analise.frac_sem_chaves", tok.pos)
        num_t = self._tokens_do_grupo()
        if self.atual.tipo != "LCH":
            raise ErroDeAnalise("erro.analise.frac_sem_chaves", tok.pos)
        den_t = self._tokens_do_grupo()

        deriv = self._derivada(num_t, den_t, tok)
        if deriv is not None:
            return [deriv]

        if self.integrais and self.integrais[-1].prof == self.prof and not self.integrais[-1].fim:
            marca = self._marca_diferencial(num_t)
            if marca is not None and marca[0] == "d" and marca[2]:
                filho_num = self._filho(marca[2])
                var = filho_num.simbolo_unico()
                if filho_num.atual.tipo == "FIM" and marca[1] == 1:
                    den = self._filho(den_t).analisar()
                    ctx = self.integrais[-1]
                    ctx.var = var
                    ctx.fim = True
                    return [Div(Num("1"), den)]

        if not num_t or not den_t:
            raise ErroDeAnalise("erro.analise.frac_vazia", tok.pos)
        return [Div(self._filho(num_t).analisar(), self._filho(den_t).analisar())]

    def _marca_diferencial(self, toks: list[Token]) -> tuple[str, int, list[Token]] | None:
        """Reconhece ``d``, ``\\mathrm{d}`` ou ``\\partial`` no início; devolve (tipo, ordem, resto)."""
        if not toks:
            return None
        t0 = toks[0]
        i = 1
        if t0.tipo == "CMD" and t0.texto == "\\mathrm" and t0.conteudo == "d":
            tipo = "d"
        elif t0.tipo == "CMD" and t0.texto == "\\partial":
            tipo = "p"
        elif t0.eh("LETRA", "d"):
            if len(toks) > 1 and toks[1].espaco_antes:
                return None
            if len(toks) > 1 and not (
                self._eh_inicio_simbolo(toks[1]) or toks[1].eh("OP", "^")
                or toks[1].tipo == "ABRE"
                or (toks[1].tipo == "CMD" and (toks[1].texto in FUNCOES
                                               or toks[1].texto in FRACOES))
            ):
                return None
            tipo = "d"
        else:
            return None
        ordem = 1
        if i < len(toks) and toks[i].eh("OP", "^"):
            j = i + 1
            if j < len(toks) and toks[j].tipo == "NUM" and toks[j].texto.isdigit():
                ordem = int(toks[j].texto)
                i = j + 1
            elif (j + 2 < len(toks) and toks[j].tipo == "LCH" and toks[j + 1].tipo == "NUM"
                  and toks[j + 1].texto.isdigit() and toks[j + 2].tipo == "RCH"):
                ordem = int(toks[j + 1].texto)
                i = j + 3
            else:
                return None
        return tipo, ordem, toks[i:]

    def _derivada(self, num_t: list[Token], den_t: list[Token], tok: Token) -> Expr | None:
        mn = self._marca_diferencial(num_t)
        md = self._marca_diferencial(den_t)
        if mn is None or md is None or mn[0] != md[0] or not md[2]:
            return None
        if md[1] != 1:
            return None  # a ordem fica no expoente da variável: dt^{2}
        filho = self._filho(md[2])
        try:
            var = filho.simbolo_unico()
        except ErroDeAnalise:
            return None
        ordem_den = 1
        if filho.atual.eh("OP", "^"):
            filho.avancar()
            exp = filho.grupo_ou_unidade()
            if not isinstance(exp, Num) or "." in exp.valor:
                return None
            ordem_den = int(exp.valor)
        if filho.atual.tipo != "FIM":
            return None
        if mn[1] != ordem_den:
            raise ErroDeAnalise("erro.analise.ordem_derivada_inconsistente", tok.pos)
        if mn[2]:
            f = self._filho(mn[2]).analisar()
        else:
            if self.atual.tipo == "FIM" or not self._inicia_fator(self.atual):
                raise ErroDeAnalise("erro.analise.derivada_sem_funcao", tok.pos)
            f = self._unico(self.potencia())
        if mn[0] == "p":
            return PDeriv(f, var, (), mn[1])
        return Deriv(f, var, mn[1])


def analisar(
    latex: str,
    tabela: TabelaDeSimbolos | None = None,
    modo_palavras: ModoPalavras = "perguntar",
) -> Expr:
    """Converte LaTeX restrito em AmsiorExpr."""
    return Analisador(tokenizar(latex), tabela, modo_palavras).analisar()
