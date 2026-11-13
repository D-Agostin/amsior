# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Certificação de passos (camadas V1 e V5) e verificação de solução (V2).

O verificador não confia no motor: recebe ``antes``, ``depois`` e a operação
declarada, refaz a operação por conta própria e exige identidade lado a lado.
Também recalcula quais condições a operação exige e qual relação ela permite,
pela sua própria tabela (``operacoes.py``). Nada que o passo afirma sobre si
mesmo é aceito sem conferência.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sympy as sp

from amsior.expr.latex import para_latex
from amsior.expr.nos import Eq, Expr, Ge, Gt, Le, Lt, Ne, Sym
from amsior.expr.ponte_sympy import ParaSympy, de_sympy
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.units.glossario import Glossario
from amsior.units.homogeneidade import verificar_homogeneidade
from amsior.verify.identidade import ResultadoIdentidade, identicas
from amsior.verify.modelo import (
    Certificado, Condicao, EstadoCert, MetodoCert, Motivo, Passo, Relacao,
)
from amsior.verify.operacoes import OPERACOES, Exigencia, Predicado

_IMPLICA_PREDICADO: dict[Predicado, set[Predicado]] = {
    "positivo": {"positivo", "nao_negativo", "nao_nulo"},
    "nao_negativo": {"nao_negativo"},
    "nao_nulo": {"nao_nulo"},
}
_Q = {"positivo": sp.Q.positive, "nao_negativo": sp.Q.nonnegative, "nao_nulo": sp.Q.nonzero}


def _texto(x: Any, tabela: TabelaDeSimbolos | None = None) -> str:
    try:
        return para_latex(de_sympy(x, tabela))
    except Exception:
        return sp.latex(x)


def provavel(q: Any, pred: Predicado) -> bool:
    """O predicado decorre só das suposições dos símbolos?"""
    for cand in (q, _simplificar(q)):
        if cand is None:
            continue
        if pred == "positivo" and cand.is_positive is True:
            return True
        if pred == "nao_negativo" and cand.is_nonnegative is True:
            return True
        if pred == "nao_nulo" and (cand.is_nonzero is True or cand.is_positive is True
                                   or cand.is_negative is True):
            return True
    return False


def _simplificar(q: Any) -> Any:
    try:
        return sp.simplify(q)
    except Exception:
        return None


@dataclass
class _CondNorm:
    expr: Any
    predicado: Predicado
    relacao: Any  # relação SymPy, usada na amostragem


@dataclass
class _Estado:
    motivos: list[Motivo] = field(default_factory=list)
    reprovado: bool = False
    numerico: bool = False
    precisou_condicoes: bool = False
    equivalencia_perdida: bool = False

    def falha(self, chave: str, **args: str) -> None:
        self.reprovado = True
        self.motivos.append(Motivo(chave, dict(args)))


class Verificador:
    def __init__(self, tabela: TabelaDeSimbolos, glossario: Glossario) -> None:
        self.tabela = tabela
        self.glossario = glossario
        self.conv = ParaSympy(tabela)

    # ------------------------------------------------------------ condições

    def _normalizar(self, c: Condicao) -> _CondNorm | None:
        e = c.expr
        if not isinstance(e, Ne | Gt | Ge | Lt | Le):
            return None
        a, b = self.conv(e.esq), self.conv(e.dir)
        if isinstance(e, Gt):
            return _CondNorm(a - b, "positivo", sp.Gt(a, b))
        if isinstance(e, Ge):
            return _CondNorm(a - b, "nao_negativo", sp.Ge(a, b))
        if isinstance(e, Lt):
            return _CondNorm(b - a, "positivo", sp.Lt(a, b))
        if isinstance(e, Le):
            return _CondNorm(b - a, "nao_negativo", sp.Le(a, b))
        return _CondNorm(a - b, "nao_nulo", sp.Ne(a, b))

    @staticmethod
    def _implicada(q: Any, pred: Predicado, conds: list[_CondNorm]) -> bool:
        for c in conds:
            if pred not in _IMPLICA_PREDICADO[c.predicado]:
                continue
            if sp.simplify(c.expr - q) == 0:
                return True
            if pred == "nao_nulo" and sp.simplify(c.expr + q) == 0:
                return True
        if not conds:
            return False
        try:
            hipotese = sp.And(*[_Q[c.predicado](c.expr) for c in conds])
            return sp.ask(_Q[pred](q), hipotese) is True
        except Exception:
            return False

    # ------------------------------------------------------------ certificação

    def certificar(self, passo: Passo) -> Certificado:
        st = _Estado()
        if passo.tipo in ("principio", "aproximacao"):
            v5 = self._v5(passo, st)
            estado: EstadoCert = "reprovado" if st.reprovado else "pendente"
            st.motivos.append(Motivo("verif.revisao_humana_exigida"))
            passo.certificado = Certificado("revisao_humana", estado, st.motivos, "pendente", v5)
            return passo.certificado

        conds = self._conferir_condicoes(passo, st)
        if st.reprovado:
            return self._fechar(passo, st, (), "nao_executado", "nao_executado")

        op = passo.operacao
        if op.nome not in OPERACOES:
            st.falha("verif.operacao_desconhecida", operacao=op.nome)
            return self._fechar(passo, st, (), "nao_executado", "nao_executado")
        funcao, exige_arg = OPERACOES[op.nome]
        if exige_arg and op.argumento is None:
            st.falha("verif.argumento_ausente", operacao=op.nome)
            return self._fechar(passo, st, (), "nao_executado", "nao_executado")

        lados = self._lados(passo, st)
        if lados is None:
            return self._fechar(passo, st, (), "nao_executado", "nao_executado")
        L, R, Ld, Rd = lados

        if op.nome == "substituir":
            if op.simbolo is None or op.argumento is None:
                st.falha("verif.substituicao_incompleta")
                return self._fechar(passo, st, (), "nao_executado", "nao_executado")
            troca = {self.conv.valor_simbolo(op.simbolo.id): self.conv(op.argumento)}
            L = L.xreplace(troca)
            R = R.xreplace(troca) if R is not None else None
            # Na fase 1A não há biblioteca para conferir de onde veio a igualdade
            # substituída; mesmo uma "definição" declarada não é aceita como
            # equivalência sem conferência. A fase 2 liga a origem à ficha citada.
            st.precisou_condicoes = True

        arg = None if op.argumento is None or op.nome == "substituir" else self.conv(op.argumento)
        if op.nome == "reescrever" or op.nome == "substituir" or R is None:
            ef_esq, ef_dir, base, exigencias = L, R, "equivalente", []
        else:
            ef = funcao(L, R, arg)
            ef_esq, ef_dir, base, exigencias = ef.esquerdo, ef.direito, ef.relacao_base, ef.exigencias

        if op.lado == "esquerdo" and passo.depois is not None and R is not None:
            if not self._mesmo(passo, "dir"):
                st.falha("verif.lado_alterado", lado="direito")
        if op.lado == "direito" and R is not None:
            if not self._mesmo(passo, "esq"):
                st.falha("verif.lado_alterado", lado="esquerdo")

        self._comparar(ef_esq, Ld, conds, st, "esquerdo" if R is not None else "expressao")
        if R is not None:
            self._comparar(ef_dir, Rd, conds, st, "direito")
        v1 = "reprovado" if st.reprovado else "aprovado"

        self._exigencias(exigencias, conds, st)

        permitidas = self._relacoes_permitidas(base, st)
        if passo.relacao not in permitidas:
            st.falha("verif.relacao_otimista", declarada=passo.relacao,
                     permitidas=", ".join(permitidas))

        v5 = self._v5(passo, st)
        return self._fechar(passo, st, permitidas, v1, v5)

    def _fechar(self, passo: Passo, st: _Estado, permitidas: tuple[Relacao, ...],
                v1: str, v5: str) -> Certificado:
        estado: EstadoCert
        if st.reprovado:
            estado = "reprovado"
        elif v5 == "indeterminado":
            estado = "pendente"
        else:
            estado = "aprovado"
        metodo: MetodoCert = "numerico" if st.numerico else "simbolico"
        cert = Certificado(metodo, estado, st.motivos, v1, v5, permitidas)
        passo.certificado = cert
        return cert

    def _conferir_condicoes(self, passo: Passo, st: _Estado) -> list[_CondNorm]:
        conds: list[_CondNorm] = []
        for c in passo.condicoes:
            n = self._normalizar(c)
            if n is None:
                st.falha("verif.condicao_invalida", condicao=para_latex(c.expr))
                continue
            garantida = provavel(n.expr, n.predicado)
            if (c.satisfeita is True or c.origem == "suposicao") and not garantida:
                st.falha("verif.condicao_otimista", condicao=para_latex(c.expr))
            if not garantida:
                conds.append(n)
        return conds

    def _lados(self, passo: Passo, st: _Estado) -> tuple[Any, Any, Any, Any] | None:
        a, d = passo.antes, passo.depois
        if isinstance(a, Eq) and isinstance(d, Eq):
            return self.conv(a.esq), self.conv(a.dir), self.conv(d.esq), self.conv(d.dir)
        if passo.operacao.nome in ("reescrever", "substituir") and not isinstance(a, Eq) \
                and not isinstance(d, Eq):
            return self.conv(a), None, self.conv(d), None
        st.falha("verif.passo_sem_equacao")
        return None

    def _mesmo(self, passo: Passo, lado: str) -> bool:
        a, d = passo.antes, passo.depois
        assert isinstance(a, Eq) and isinstance(d, Eq)
        return bool(getattr(a, lado) == getattr(d, lado))

    def _comparar(self, esperado: Any, obtido: Any, conds: list[_CondNorm], st: _Estado,
                  lado: str) -> None:
        r: ResultadoIdentidade = identicas(esperado, obtido)
        if not r.aprovado and conds:
            r2 = identicas(esperado, obtido, [c.relacao for c in conds])
            if r2.aprovado:
                st.precisou_condicoes = True
                r = r2
        if not r.aprovado:
            st.falha("verif.lado_nao_confere", lado=lado, detalhe=r.motivo,
                     esperado=_texto(esperado, self.tabela), obtido=_texto(obtido, self.tabela))
        elif r.metodo == "numerico":
            st.numerico = True

    def _exigencias(self, exigencias: list[Exigencia], conds: list[_CondNorm],
                    st: _Estado) -> None:
        for ex in exigencias:
            if provavel(ex.expr, ex.predicado):
                continue
            if self._implicada(ex.expr, ex.predicado, conds):
                st.precisou_condicoes = True
                continue
            if ex.tipo == "dominio":
                st.falha("verif.condicao_ausente", expressao=_texto(ex.expr, self.tabela),
                         predicado=f"predicado.{ex.predicado}")
            else:
                st.equivalencia_perdida = True

    @staticmethod
    def _relacoes_permitidas(base: str, st: _Estado) -> tuple[Relacao, ...]:
        if base == "implica" or st.equivalencia_perdida:
            return ("implica",)
        if st.precisou_condicoes:
            return ("restringe", "implica")
        return ("equivalente", "restringe", "implica")

    def _v5(self, passo: Passo, st: _Estado) -> str:
        r = verificar_homogeneidade(passo.depois, self.tabela, self.glossario)
        if r.estado == "reprovado" and r.erro is not None:
            st.falha("verif.dimensional", erro=r.erro.mensagem())
        elif r.estado == "indeterminado":
            st.motivos.append(Motivo("verif.sem_grandeza",
                                     {"simbolos": ", ".join(sorted(r.sem_grandeza))}))
        return r.estado

    # ------------------------------------------------------------ V2

    def verificar_solucao(self, equacao: Expr, alvo: Sym, solucao: Expr,
                          condicoes: tuple[Condicao, ...] = ()) -> ResultadoIdentidade:
        """V2: a solução satisfaz a equação original (substituição e resíduo nulo)."""
        if not isinstance(equacao, Eq):
            return ResultadoIdentidade(False, None, "verif.passo_sem_equacao")
        troca = {self.conv.valor_simbolo(alvo.id): self.conv(solucao)}
        L = self.conv(equacao.esq).xreplace(troca)
        R = self.conv(equacao.dir).xreplace(troca)
        normas = [n for n in (self._normalizar(c) for c in condicoes) if n is not None]
        r = identicas(L, R)
        if not r.aprovado and normas:
            r = identicas(L, R, [n.relacao for n in normas])
        return r


def certificar(passo: Passo, tabela: TabelaDeSimbolos, glossario: Glossario) -> Certificado:
    return Verificador(tabela, glossario).certificar(passo)
