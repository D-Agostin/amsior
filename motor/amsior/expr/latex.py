# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Impressão determinística AmsiorExpr → LaTeX.

A saída é canônica: ``analisar(para_latex(e)) == e`` para toda árvore válida
(com a tabela de símbolos da folha quando há funções incógnitas). Parênteses
só aparecem onde a estrutura da árvore exige.
"""

from __future__ import annotations

from amsior.expr.nos import (
    Abs, Add, Cos, Deriv, Div, Eq, Exp, Expr, Func, Ge, Gt, Integral, Le, Ln, Log, Lt,
    Mul, Ne, Neg, Num, PDeriv, Pow, Root, Sin, Sqrt, Sub, Sym, Tan,
)

_REL = {Eq: "=", Ne: "\\neq", Gt: ">", Ge: "\\geq", Lt: "<", Le: "\\leq"}
_FUNC = {Ln: "\\ln", Exp: "\\exp", Sin: "\\sin", Cos: "\\cos", Tan: "\\tan"}


def _par(s: str) -> str:
    return f"\\left({s}\\right)"


class Impressor:
    def __init__(self, idioma: str = "pt-BR") -> None:
        self.virgula = idioma == "pt-BR"

    # ------------------------------------------------------------ entrada

    def __call__(self, e: Expr) -> str:
        return self.p(e)

    def p(self, e: Expr) -> str:
        metodo = getattr(self, f"_{type(e).__name__.lower()}")
        resultado: str = metodo(e)
        return resultado

    # ------------------------------------------------------------ folhas

    def _num(self, e: Num) -> str:
        return e.valor.replace(".", "{,}") if self.virgula else e.valor

    def _sym(self, e: Sym) -> str:
        return e.id

    # ------------------------------------------------------------ aritmética

    def _add(self, e: Add) -> str:
        partes = [self._termo_esquerdo(e.termos[0])]
        for t in e.termos[1:]:
            partes.append(self._termo_direito(t))
        return " + ".join(partes)

    def _termo_esquerdo(self, t: Expr) -> str:
        """Primeiro termo de uma cadeia: só relações e Add aninhado pedem parênteses."""
        if isinstance(t, Add) or isinstance(t, tuple(_REL)):
            return _par(self.p(t))
        return self.p(t)

    def _termo_direito(self, t: Expr) -> str:
        if isinstance(t, (Add, Sub, Neg)) or isinstance(t, tuple(_REL)):
            return _par(self.p(t))
        return self.p(t)

    def _sub(self, e: Sub) -> str:
        esq = self.p(e.a)
        if isinstance(e.a, tuple(_REL)):
            esq = _par(esq)
        return f"{esq} - {self._termo_direito(e.b)}"

    def _neg(self, e: Neg) -> str:
        return "-" + self._termo_direito(e.a)

    def _mul(self, e: Mul) -> str:
        textos: list[str] = []
        for k, f in enumerate(e.fatores):
            ultimo = k == len(e.fatores) - 1
            precisa = isinstance(f, (Add, Sub, Neg, Mul)) or isinstance(f, tuple(_REL))
            if isinstance(f, Integral) and not ultimo:
                precisa = True
            if isinstance(f, Deriv | PDeriv) and not self._deriv_compacta(f) and not ultimo:
                precisa = True
            txt = self.p(f)
            textos.append(_par(txt) if precisa else txt)
        saida = textos[0]
        for anterior, txt in zip(textos, textos[1:]):
            if txt[0].isdigit() or (anterior[-1].isdigit() and txt[0].isdigit()):
                saida += " \\cdot " + txt
            else:
                saida += " " + txt
        return saida

    def _div(self, e: Div) -> str:
        return f"\\frac{{{self.p(e.num)}}}{{{self.p(e.den)}}}"

    def _base_potencia(self, b: Expr) -> str:
        if isinstance(b, Sym):
            if "^" in b.id or b.id == "e":
                return _par(b.id)
            return b.id
        if isinstance(b, Num | Abs | Sqrt | Root | Func | Div):
            return self.p(b) if not isinstance(b, Div) else _par(self.p(b))
        return _par(self.p(b))

    def _pow(self, e: Pow) -> str:
        b = e.base
        if isinstance(b, Sin | Cos | Tan) and isinstance(e.exp, Num):
            # forma usual: \sin^{2} x
            return f"{_FUNC[type(b)]}^{{{self.p(e.exp)}}}" + self._arg_funcao(b.a)
        expoente = self.p(e.exp)
        if isinstance(e.exp, Sym) and e.exp.id.startswith("\\mathrm"):
            # ^{\mathrm{Re}} sozinho seria lido como rótulo (P^{\mathrm{sat}})
            expoente = _par(expoente)
        return f"{self._base_potencia(b)}^{{{expoente}}}"

    def _sqrt(self, e: Sqrt) -> str:
        return f"\\sqrt{{{self.p(e.a)}}}"

    def _root(self, e: Root) -> str:
        return f"\\sqrt[{self.p(e.n)}]{{{self.p(e.a)}}}"

    # ------------------------------------------------------------ funções

    def _arg_funcao(self, a: Expr) -> str:
        if isinstance(a, Sym | Num):
            return " " + self.p(a)
        if isinstance(a, Div):
            return self.p(a)
        return _par(self.p(a))

    def _exp(self, e: Exp) -> str:
        return f"e^{{{self.p(e.a)}}}"

    def _ln(self, e: Ln) -> str:
        return "\\ln" + self._arg_funcao(e.a)

    def _log(self, e: Log) -> str:
        if isinstance(e.base, Num) and e.base.valor == "10":
            return "\\log" + self._arg_funcao(e.a)
        return f"\\log_{{{self.p(e.base)}}}" + self._arg_funcao(e.a)

    def _sin(self, e: Sin) -> str:
        return "\\sin" + self._arg_funcao(e.a)

    def _cos(self, e: Cos) -> str:
        return "\\cos" + self._arg_funcao(e.a)

    def _tan(self, e: Tan) -> str:
        return "\\tan" + self._arg_funcao(e.a)

    def _abs(self, e: Abs) -> str:
        return f"\\left|{self.p(e.a)}\\right|"

    def _func(self, e: Func) -> str:
        return e.nome + _par("; ".join(self.p(a) for a in e.args))

    # ------------------------------------------------------------ cálculo

    @staticmethod
    def _deriv_compacta(e: Deriv | PDeriv) -> bool:
        return isinstance(e.f, Sym | Func)

    def _var_den(self, marca: str, var: Sym, ordem: int) -> str:
        return f"{marca}{var.id}" + (f"^{{{ordem}}}" if ordem > 1 else "")

    def _deriv(self, e: Deriv) -> str:
        marca = "\\mathrm{d}"
        ordem_num = f"^{{{e.ordem}}}" if e.ordem > 1 else ""
        den = self._var_den(marca, e.var, e.ordem)
        if self._deriv_compacta(e):
            return f"\\frac{{{marca}{ordem_num}{self.p(e.f)}}}{{{den}}}"
        return f"\\frac{{{marca}{ordem_num}}}{{{den}}}" + _par(self.p(e.f))

    def _pderiv(self, e: PDeriv) -> str:
        marca = "\\partial "
        ordem_num = f"^{{{e.ordem}}}" if e.ordem > 1 else ""
        den = self._var_den(marca, e.var, e.ordem)
        if self._deriv_compacta(e):
            nucleo = f"\\frac{{{marca.strip()}{ordem_num} {self.p(e.f)}}}{{{den}}}"
        else:
            nucleo = f"\\frac{{{marca.strip()}{ordem_num}}}{{{den}}}" + _par(self.p(e.f))
        if e.mantidas:
            return _par(nucleo) + "_{" + ", ".join(s.id for s in e.mantidas) + "}"
        return nucleo

    def _integral(self, e: Integral) -> str:
        cab = "\\int"
        if e.inferior is not None:
            cab += f"_{{{self.p(e.inferior)}}}"
        if e.superior is not None:
            cab += f"^{{{self.p(e.superior)}}}"
        d = "\\mathrm{d}" + e.var.id
        f = e.f
        if isinstance(f, Num) and f.valor == "1":
            return f"{cab} {d}"
        if isinstance(f, Div) and isinstance(f.num, Num) and f.num.valor == "1":
            return f"{cab} \\frac{{{d}}}{{{self.p(f.den)}}}"
        if isinstance(f, Mul):
            ult = f.fatores[-1]
            if isinstance(ult, Div) and isinstance(ult.num, Num) and ult.num.valor == "1":
                resto = Mul(f.fatores[:-1]) if len(f.fatores) > 2 else f.fatores[0]
                return f"{cab} {self._integrando(resto)} \\frac{{{d}}}{{{self.p(ult.den)}}}"
        return f"{cab} {self._integrando(f)} \\,{d}"

    def _integrando(self, f: Expr) -> str:
        if isinstance(f, (Add, Sub, Neg)) or isinstance(f, tuple(_REL)):
            return _par(self.p(f))
        if isinstance(f, Mul):
            # o último fator não pode ser lido como parte do diferencial
            return self.p(f)
        return self.p(f)

    # ------------------------------------------------------------ relações

    def _rel(self, e: Eq | Ne | Gt | Ge | Lt | Le) -> str:
        return f"{self.p(e.esq)} {_REL[type(e)]} {self.p(e.dir)}"

    _eq = _ne = _gt = _ge = _lt = _le = _rel


def para_latex(e: Expr, idioma: str = "pt-BR") -> str:
    """LaTeX canônico da expressão. Em pt-BR, decimais usam ``{,}``."""
    return Impressor(idioma)(e)
