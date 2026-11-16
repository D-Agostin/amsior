# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Regras de isolamento (seção 4.2): desfazer a operação mais externa em volta do alvo.

Cada regra recebe a equação atual, com o alvo só no lado esquerdo, e propõe
um ou mais ramos; cada ramo é uma lista de passos propostos. A regra declara
a operação que o verificador refaz, as condições que não decorrem das
suposições e a justificativa (chave no catálogo de textos). Nenhuma regra
decide se o passo é válido: isso é do verificador.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Literal

from amsior.expr.latex import para_latex
from amsior.expr.nos import (
    Abs, Add, Cos, Deriv, Div, Eq, Exp, Expr, Func, Ge, Gt, Integral, Le, Ln, Log, Mul, Ne,
    Neg, Num, PDeriv, Pow, Root, Sin, Sqrt, Sub, Tan,
)
from amsior.expr.ponte_sympy import ParaSympy
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.expr.ponte_sympy import de_sympy
from amsior.rules.simplificar import apresentar, cancelar, sem_sinal_duplo
from amsior.verify.logica import normalizar
from sympy import Add as sp_Add, log as sp_log
from amsior.verify.arvore import fracao_exata, livres
from amsior.verify.logica import por_suposicao
from amsior.verify.modelo import Condicao, Operacao, Relacao

Pred = Literal["nao_nulo", "positivo", "nao_negativo"]
_ZERO = Num("0")


@dataclass
class Proposta:
    regra: str
    depois: Expr
    operacao: Operacao
    relacao: Relacao = "equivalente"
    condicoes: tuple[Condicao, ...] = ()
    justificativa: dict[str, Any] = field(default_factory=dict)
    fundivel: bool = False


@dataclass
class Ramo:
    propostas: list[Proposta]
    rotulo: str = ""  # chave do catálogo: "ramo.positivo", "ramo.negativo"
    descartado: str | None = None  # motivo, quando as suposições excluem o ramo


@dataclass
class Recusa:
    chave: str
    args: dict[str, str] = field(default_factory=dict)


@dataclass
class Contexto:
    tabela: TabelaDeSimbolos
    alvo: str
    conv: ParaSympy = field(init=False)

    def __post_init__(self) -> None:
        self.conv = ParaSympy(self.tabela)

    def garantido(self, e: Expr, pred: Pred) -> bool:
        try:
            return por_suposicao(self.conv(e), pred)
        except Exception:
            return False

    def condicao(self, e: Expr, pred: Pred, comparar_com: Expr = _ZERO) -> tuple[Condicao, ...]:
        """A condição ``e ≠ / > / ≥ comparar_com``, se as suposições não a garantem."""
        alvo_expr = e if comparar_com == _ZERO else Sub(e, comparar_com)
        if self.garantido(alvo_expr, pred):
            return ()
        rel = {"nao_nulo": Ne, "positivo": Gt, "nao_negativo": Ge}[pred]
        if comparar_com == _ZERO:
            # só o essencial: 128μLQ/(πΔP) ≥ 0 vira ΔP ≥ 0
            try:
                comps = normalizar(self.conv(e), pred)
            except Exception:
                comps = None
            if comps and all(not isinstance(q, sp_Add) and not q.has(sp_log) for q, _ in comps):
                out = []
                for q, p in comps:
                    if not por_suposicao(q, p):
                        out.append(Condicao({"nao_nulo": Ne, "positivo": Gt, "nao_negativo": Ge}[p](
                            apresentar(de_sympy(q, self.tabela)), _ZERO)))
                return tuple(out)
        return (Condicao(rel(apresentar(e), comparar_com)),)

    def tem(self, e: Expr) -> bool:
        return self.alvo in livres(e)


def _j(chave: str, **args: Expr | str) -> dict[str, Any]:
    return {"chave": chave,
            "args": {k: (para_latex(v) if isinstance(v, Expr) else v) for k, v in args.items()}}


def passo_de_cancelamento(eq: Eq) -> Proposta | None:
    """Passo de acabamento: cancelar o que a operação anterior deixou à mostra."""
    e = apresentar(sem_sinal_duplo(cancelar(eq.esq)))
    d = apresentar(sem_sinal_duplo(cancelar(eq.dir)))
    if e == eq.esq and d == eq.dir:
        return None
    lado: Literal["esquerdo", "direito"] | None = (
        "esquerdo" if d == eq.dir else "direito" if e == eq.esq else None)
    return Proposta("simplificar", Eq(e, d), Operacao("reescrever", lado=lado),
                    justificativa=_j("regra.simplificar"), fundivel=True)


# ---------------------------------------------------------------- regras por forma


def _soma(eq: Eq, c: Contexto) -> list[Ramo]:
    termos = eq.esq.termos if isinstance(eq.esq, Add) else ()
    com = [t for t in termos if c.tem(t)]
    sem = [t for t in termos if not c.tem(t)]
    resto: Expr = sem[0] if len(sem) == 1 else Add(tuple(sem))
    depois = Eq(Sub(eq.esq, resto), Sub(eq.dir, resto))
    assert len(com) == 1
    return [Ramo([Proposta("subtrair_ambos_lados", depois,
                           Operacao("subtrair_ambos", resto),
                           justificativa=_j("regra.subtrair_ambos_lados", termo=resto))])]


def _subtracao(eq: Eq, c: Contexto) -> list[Ramo]:
    assert isinstance(eq.esq, Sub)
    a, b = eq.esq.a, eq.esq.b
    if c.tem(a):  # u − B = C  →  u − B + B = C + B
        return [Ramo([Proposta("somar_ambos_lados", Eq(Add((eq.esq, b)), Add((eq.dir, b))),
                               Operacao("somar_ambos", b),
                               justificativa=_j("regra.somar_ambos_lados", termo=b))])]
    # A − u = C  →  A − u − A = C − A
    return [Ramo([Proposta("subtrair_ambos_lados", Eq(Sub(eq.esq, a), Sub(eq.dir, a)),
                           Operacao("subtrair_ambos", a),
                           justificativa=_j("regra.subtrair_ambos_lados", termo=a))])]


def _oposto(eq: Eq, c: Contexto) -> list[Ramo]:
    assert isinstance(eq.esq, Neg)
    menos_um = Neg(Num("1"))
    depois = Eq(eq.esq.a, sem_sinal_duplo(Neg(eq.dir)))
    return [Ramo([Proposta("multiplicar_por_menos_um", depois,
                           Operacao("multiplicar_ambos", menos_um),
                           justificativa=_j("regra.multiplicar_por_menos_um"))])]


def _produto(eq: Eq, c: Contexto) -> list[Ramo]:
    assert isinstance(eq.esq, Mul)
    sem = [f for f in eq.esq.fatores if not c.tem(f)]
    divisor = sem[0] if len(sem) == 1 else Mul(tuple(sem))
    if isinstance(divisor, Div) and divisor.num == Num("1"):  # (1/k)·u = B  →  multiplicar por k
        k = divisor.den
        return [Ramo([Proposta("multiplicar_ambos_lados", Eq(Mul((eq.esq, k)), Mul((eq.dir, k))),
                               Operacao("multiplicar_ambos", k),
                               condicoes=c.condicao(k, "nao_nulo"),
                               justificativa=_j("regra.multiplicar_ambos_lados", fator=k))])]
    depois = Eq(Div(eq.esq, divisor), Div(eq.dir, divisor))
    return [Ramo([Proposta("dividir_ambos_lados", depois, Operacao("dividir_ambos", divisor),
                           condicoes=c.condicao(divisor, "nao_nulo"),
                           justificativa=_j("regra.dividir_ambos_lados", divisor=divisor))])]


def _quociente(eq: Eq, c: Contexto) -> list[Ramo]:
    assert isinstance(eq.esq, Div)
    n, d = eq.esq.num, eq.esq.den
    if c.tem(n) and not c.tem(d):  # u/A = B  →  (u/A)·A = B·A
        depois = Eq(Mul((eq.esq, d)), Mul((eq.dir, d)))
        return [Ramo([Proposta("multiplicar_ambos_lados", depois,
                               Operacao("multiplicar_ambos", d),
                               justificativa=_j("regra.multiplicar_ambos_lados", fator=d))])]
    if n == Num("1"):  # 1/u = B  →  u = 1/B
        return [Ramo([Proposta("reciproco_dos_dois_lados", Eq(d, Div(Num("1"), eq.dir)),
                               Operacao("reciproco_ambos"),
                               condicoes=c.condicao(eq.dir, "nao_nulo"),
                               justificativa=_j("regra.reciproco_dos_dois_lados"))])]
    # A/u = B  →  (A/u)·u = B·u ; depois o motor troca os lados e divide por B
    depois = Eq(Mul((eq.esq, d)), Mul((eq.dir, d)))
    return [Ramo([Proposta("multiplicar_ambos_lados", depois, Operacao("multiplicar_ambos", d),
                           justificativa=_j("regra.multiplicar_pelo_denominador", fator=d))])]


def _potencia(eq: Eq, c: Contexto) -> list[Ramo] | Recusa:
    assert isinstance(eq.esq, Pow)
    base, k = eq.esq.base, eq.esq.exp
    if c.tem(k):
        if c.tem(base):
            return Recusa("isolar.alvo_na_base_e_no_expoente")
        return _expoente(eq, c)
    q = fracao_exata(k)
    if q is not None and q.denominator == 1 and q > 0:
        return _raiz_inteira(eq, int(q), c)
    # expoente não inteiro ou simbólico: elevar a 1/k (exige base > 0)
    inv = Div(Num("1"), k) if q is None else _num_fracao(1 / q)
    depois = Eq(base, Pow(eq.dir, inv))
    return [Ramo([Proposta("elevar_ao_inverso", depois, Operacao("elevar_ambos", inv),
                           condicoes=c.condicao(base, "positivo") + c.condicao(eq.dir, "positivo"),
                           justificativa=_j("regra.elevar_ao_inverso", expoente=inv))])]


def _num_fracao(q: Fraction) -> Expr:
    num = Num(str(abs(q.numerator)))
    e: Expr = num if q.denominator == 1 else Div(num, Num(str(q.denominator)))
    return Neg(e) if q < 0 else e


def _raiz_inteira(eq: Eq, n: int, c: Contexto) -> list[Ramo] | Recusa:
    base = eq.esq.base if isinstance(eq.esq, Pow) else eq.esq
    indice = Num(str(n))
    raiz: Expr = Sqrt(eq.dir) if n == 2 else Root(eq.dir, indice)
    if n % 2 == 1:
        return [Ramo([Proposta("raiz_impar", Eq(base, raiz), Operacao("raiz_ambos", indice),
                               justificativa=_j("regra.raiz_impar", indice=str(n)))])]
    valor = _valor_numerico(eq.dir, c)
    if valor is not None and n % 2 == 0 and valor.is_negative:
        return Recusa("isolar.potencia_par_negativa", {"indice": str(n)})
    if n % 2 == 0 and (eq.dir == _ZERO or valor is not None and valor.is_zero):
        # u^n = 0: os dois ramos da raiz dão a mesma raiz, u = 0 (raiz dupla do 2º grau
        # com Δ = 0). Um ramo só; a condição u ≥ 0 da raiz positiva vale na raiz.
        return [Ramo([Proposta("raiz_de_zero", Eq(base, _ZERO), Operacao("raiz_ambos", indice),
                               condicoes=c.condicao(base, "nao_negativo"),
                               justificativa=_j("regra.raiz_de_zero", indice=str(n)))])]
    cond_b = c.condicao(eq.dir, "nao_negativo")
    pos = Ramo([Proposta("raiz_par", Eq(base, raiz), Operacao("raiz_ambos", indice),
                         condicoes=cond_b + c.condicao(base, "nao_negativo"),
                         justificativa=_j("regra.raiz_par_positiva", indice=str(n)))],
               "ramo.positivo")
    neg = Ramo([Proposta("raiz_par", Eq(sem_sinal_duplo(Neg(base)), raiz),
                         Operacao("raiz_ambos", indice),
                         condicoes=cond_b + (Condicao(Le(base, _ZERO)),),
                         justificativa=_j("regra.raiz_par_negativa", indice=str(n)))],
               "ramo.negativo")
    if c.garantido(base, "positivo"):
        neg.descartado = "ramo.descartado_pelas_suposicoes"
    return [pos, neg]


def _valor_numerico(e: Expr, c: Contexto) -> Any | None:
    """Valor exato de uma expressão sem símbolos (``√9 + 1`` → 4), ou None."""
    if livres(e):
        return None
    try:
        v = c.conv(e)
    except Exception:
        return None
    return v if v.is_number and v.is_real else None


def passo_de_calculo(eq: Eq, c: Contexto) -> Proposta | None:
    """Acabamento: o lado direito só com números é calculado na forma exata, se fica mais curto."""
    v = _valor_numerico(eq.dir, c)
    if v is None:
        return None
    try:
        novo = apresentar(de_sympy(v, c.tabela))
    except Exception:
        return None
    if novo == eq.dir or _tamanho(novo) >= _tamanho(eq.dir):
        return None
    return Proposta("calcular", Eq(eq.esq, novo), Operacao("reescrever", lado="direito"),
                    justificativa=_j("regra.calcular"), fundivel=True)


def _tamanho(e: Expr) -> int:
    from amsior.verify.arvore import percorrer
    return sum(1 for _ in percorrer(e))


def _expoente(eq: Eq, c: Contexto) -> list[Ramo]:
    """A^u = B  →  ln(A^u) = ln B ; o passo seguinte reescreve como u·ln A."""
    assert isinstance(eq.esq, Pow)
    base, k = eq.esq.base, eq.esq.exp
    p1 = Proposta("logaritmo_dos_dois_lados", Eq(Ln(eq.esq), Ln(eq.dir)), Operacao("ln_ambos"),
                  condicoes=c.condicao(eq.dir, "positivo"),
                  justificativa=_j("regra.logaritmo_dos_dois_lados"))
    p2 = Proposta("logaritmo_da_potencia", Eq(Mul((k, Ln(base))), Ln(eq.dir)),
                  Operacao("reescrever", lado="esquerdo"),
                  justificativa=_j("regra.logaritmo_da_potencia"))
    return [Ramo([p1, p2])]


def _exponencial(eq: Eq, c: Contexto) -> list[Ramo]:
    assert isinstance(eq.esq, Exp)
    return [Ramo([Proposta("logaritmo_dos_dois_lados", Eq(eq.esq.a, Ln(eq.dir)),
                           Operacao("ln_ambos"), condicoes=c.condicao(eq.dir, "positivo"),
                           justificativa=_j("regra.logaritmo_natural"))])]


def _logaritmo(eq: Eq, c: Contexto) -> list[Ramo]:
    if isinstance(eq.esq, Ln):
        p = [Proposta("exponencial_dos_dois_lados", Eq(eq.esq.a, Exp(eq.dir)),
                      Operacao("exp_ambos"), justificativa=_j("regra.exponencial_dos_dois_lados"))]
        # e^{X·ln b} vem de um log na base b: volta a ser b^X
        d = eq.dir
        if isinstance(d, Mul) and isinstance(d.fatores[-1], Ln) and not c.tem(d.fatores[-1]):
            b = d.fatores[-1].a
            x: Expr = d.fatores[0] if len(d.fatores) == 2 else Mul(d.fatores[:-1])
            p.append(Proposta("potencia_da_base", Eq(eq.esq.a, Pow(b, x)),
                              Operacao("reescrever", lado="direito"),
                              justificativa=_j("regra.potencia_da_base", base=b), fundivel=True))
        return [Ramo(p)]
    assert isinstance(eq.esq, Log)
    b = eq.esq.base
    if c.tem(b):
        return []
    return [Ramo([Proposta("mudanca_de_base", Eq(Div(Ln(eq.esq.a), Ln(b)), eq.dir),
                           Operacao("reescrever", lado="esquerdo"),
                           justificativa=_j("regra.mudanca_de_base", base=b))])]


def _radical(eq: Eq, c: Contexto) -> list[Ramo]:
    if isinstance(eq.esq, Sqrt):
        n, dentro = 2, eq.esq.a
    else:
        assert isinstance(eq.esq, Root)
        q = fracao_exata(eq.esq.n)
        if q is None or q.denominator != 1 or q < 2:
            return []
        n, dentro = int(q), eq.esq.a
    cond = c.condicao(eq.dir, "nao_negativo") if n % 2 == 0 else ()
    depois = Eq(dentro, Pow(eq.dir, Num(str(n))))
    return [Ramo([Proposta("elevar_os_dois_lados", depois, Operacao("elevar_ambos", Num(str(n))),
                           condicoes=cond,
                           justificativa=_j("regra.elevar_os_dois_lados", expoente=str(n)))])]


def _modulo(eq: Eq, c: Contexto) -> list[Ramo]:
    assert isinstance(eq.esq, Abs)
    u = eq.esq.a
    pos = Ramo([Proposta("modulo_positivo", Eq(u, eq.dir), Operacao("reescrever"),
                         condicoes=c.condicao(u, "nao_negativo"),
                         justificativa=_j("regra.modulo_positivo", expressao=u))],
               "ramo.positivo")
    neg = Ramo([Proposta("modulo_negativo", Eq(sem_sinal_duplo(Neg(u)), eq.dir),
                         Operacao("reescrever"), condicoes=(Condicao(Le(u, _ZERO)),),
                         justificativa=_j("regra.modulo_negativo", expressao=u))],
               "ramo.negativo")
    if c.garantido(u, "positivo"):
        neg.descartado = "ramo.descartado_pelas_suposicoes"
    return [pos, neg]


# ---------------------------------------------------------------- despacho


_TABELA: list[tuple[type | tuple[type, ...], Callable[[Eq, Contexto], Any]]] = [
    (Add, _soma), (Sub, _subtracao), (Neg, _oposto), (Mul, _produto), (Div, _quociente),
    (Pow, _potencia), (Exp, _exponencial), ((Ln, Log), _logaritmo), ((Sqrt, Root), _radical),
    (Abs, _modulo),
]


def descascar(eq: Eq, c: Contexto) -> list[Ramo] | Recusa:
    """Próximo passo para uma equação com o alvo uma vez só, no lado esquerdo."""
    e = eq.esq
    if isinstance(e, Sin | Cos | Tan):
        return Recusa("isolar.trigonometrica")
    if isinstance(e, Func | Deriv | PDeriv | Integral):
        return Recusa("isolar.alvo_em_operador")
    if isinstance(e, Add) and sum(1 for t in e.termos if c.tem(t)) != 1:
        return Recusa("isolar.varias_ocorrencias")
    for tipos, regra in _TABELA:
        if isinstance(e, tipos):
            r = regra(eq, c)
            return r if r else Recusa("isolar.sem_regra", {"forma": type(e).__name__})
    return Recusa("isolar.sem_regra", {"forma": type(e).__name__})


def trocar_lados(eq: Eq) -> Proposta:
    return Proposta("trocar_lados", Eq(eq.dir, eq.esq), Operacao("trocar_lados"),
                    justificativa=_j("regra.trocar_lados"), fundivel=True)


__all__ = ["Contexto", "Proposta", "Ramo", "Recusa", "descascar", "passo_de_calculo",
           "passo_de_cancelamento", "trocar_lados"]
