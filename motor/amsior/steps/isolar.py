# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Isolar uma variável com passos (seção 4.2).

Fluxo:

1. pré-checagem: equação, alvo presente, homogeneidade dimensional;
2. alvo uma vez só: descascar, desfazendo a operação mais externa
   (``rules.isolar``), com um passo de cancelamento depois de cada operação;
3. alvo várias vezes: levar tudo para a esquerda, eliminar denominadores com
   o alvo e, se a expressão for linear no alvo, agrupar e dividir;
4. ramos (raiz par, módulo): cada um segue sozinho; um ramo excluído pelas
   suposições (pressão positiva descarta a raiz negativa) é descartado com
   motivo;
5. cada passo é certificado na hora; no fim, a cadeia é certificada e cada
   resultado passa em V2 (substituição na equação original, com as
   hipóteses do ramo).

Qualquer passo reprovado descarta a resolução inteira (seção 5.2): sobra o
resultado do oráculo, rotulado "sem passos", se passar em V2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import sympy as sp

from amsior.expr.latex import para_latex
from amsior.expr.nos import Add, Div, Eq, Expr, Mul, Num, Sub, Sym
from amsior.expr.ponte_sympy import de_sympy
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.rules.classificar import Classificacao, classificar
from amsior.rules.isolar import (
    Contexto, Proposta, Ramo, Recusa, _j, descascar, passo_de_cancelamento, trocar_lados,
)
from amsior.units.glossario import Glossario
from amsior.units.homogeneidade import verificar_homogeneidade
from amsior.verify.arvore import livres, percorrer
from amsior.verify.dominio import Obrigacao, obrigacoes
from amsior.verify.certificador import CertificadoCadeia, Verificador
from amsior.verify.modelo import Condicao, Motivo, Operacao, Passo

LIMITE_PASSOS = 40
Estado = Literal["com_passos", "sem_passos", "recusado"]


@dataclass
class RamoResolvido:
    rotulo: str
    passos: list[Passo]
    resultado: Eq
    cadeia: CertificadoCadeia
    validade: tuple[Condicao, ...] = ()  # condições em que o resultado vale (V2)


@dataclass
class ResultadoIsolar:
    estado: Estado
    alvo: Sym
    ramos: list[RamoResolvido] = field(default_factory=list)
    descartados: list[Motivo] = field(default_factory=list)
    sem_passos: list[Eq] = field(default_factory=list)
    motivo: Motivo | None = None
    rejeitados: list[dict[str, Any]] = field(default_factory=list)  # para o registro de regressão
    tipo: Classificacao | None = None  # tipo da equação no alvo (D-12)


class _Falha(Exception):
    def __init__(self, motivo: Motivo, rejeitado: dict[str, Any] | None = None) -> None:
        super().__init__(motivo.chave)
        self.motivo = motivo
        self.rejeitado = rejeitado


def _ocorrencias(e: Expr, alvo: str) -> int:
    return sum(1 for n in percorrer(e) if isinstance(n, Sym) and n.id == alvo)


def _resolvida(eq: Eq, alvo: str) -> bool:
    return eq.esq == Sym(alvo) and alvo not in livres(eq.dir)


@dataclass
class _Caminho:
    eq: Eq
    passos: list[Passo]
    rotulo: str = ""


class Isolador:
    def __init__(self, tabela: TabelaDeSimbolos, glossario: Glossario) -> None:
        self.tabela = tabela
        self.glossario = glossario
        self.verificador = Verificador(tabela, glossario)

    # ------------------------------------------------------------ API

    def isolar(self, equacao: Expr, alvo: Sym) -> ResultadoIsolar:
        res = ResultadoIsolar("recusado", alvo)
        if not isinstance(equacao, Eq):
            res.motivo = Motivo("isolar.nao_e_equacao")
            return res
        if alvo.id not in livres(equacao):
            res.motivo = Motivo("isolar.alvo_ausente", {"alvo": alvo.id})
            return res
        dim = verificar_homogeneidade(equacao, self.tabela, self.glossario)
        if dim.estado == "reprovado" and dim.erro is not None:
            res.motivo = Motivo("isolar.nao_homogenea", {"erro": dim.erro.mensagem()})
            return res
        res.tipo = classificar(equacao, alvo.id, self.tabela)
        ctx = Contexto(self.tabela, alvo.id)
        self._ctx = ctx
        try:
            ramos = self._resolver(equacao, ctx, res)
        except _Falha as f:
            if f.rejeitado:
                res.rejeitados.append(f.rejeitado)
            res.motivo = f.motivo
            return self._sem_passos(equacao, alvo, res)
        res.ramos = ramos
        res.estado = "com_passos"
        return res

    # ------------------------------------------------------------ resolução

    def _resolver(self, eq0: Eq, ctx: Contexto, res: ResultadoIsolar) -> list[RamoResolvido]:
        abertos = [_Caminho(eq0, [])]
        prontos: list[RamoResolvido] = []
        while abertos:
            cam = abertos.pop(0)
            while not _resolvida(cam.eq, ctx.alvo):
                if len(cam.passos) >= LIMITE_PASSOS:
                    raise _Falha(Motivo("isolar.passos_demais"))
                ramos = self._proximo(cam.eq, ctx)
                vivos = []
                for r in ramos:
                    if r.descartado:
                        res.descartados.append(Motivo(r.descartado, {"ramo": r.rotulo}))
                    else:
                        vivos.append(r)
                if not vivos:
                    raise _Falha(Motivo("isolar.sem_ramo"))
                for r in vivos[1:]:
                    novo = _Caminho(cam.eq, list(cam.passos), r.rotulo)
                    self._aplicar(novo, r.propostas)
                    abertos.append(novo)
                if vivos[0].rotulo:
                    cam.rotulo = vivos[0].rotulo
                self._aplicar(cam, vivos[0].propostas)
            prontos.append(self._fechar(eq0, cam))
        return prontos

    def _proximo(self, eq: Eq, ctx: Contexto) -> list[Ramo]:
        na_esq, na_dir = ctx.tem(eq.esq), ctx.tem(eq.dir)
        if na_dir and not na_esq:
            return [Ramo([trocar_lados(eq)])]
        if na_esq and not na_dir and _ocorrencias(eq.esq, ctx.alvo) == 1:
            r = descascar(eq, ctx)
            if isinstance(r, Recusa):
                raise _Falha(Motivo(r.chave, r.args))
            return r
        return [Ramo(self._reunir(eq, ctx))]

    def _aplicar(self, cam: _Caminho, propostas: list[Proposta]) -> None:
        for p in propostas:
            self._certificar(cam, p)
            assert isinstance(cam.eq, Eq)
            canc = passo_de_cancelamento(cam.eq)
            if canc is not None:
                self._certificar(cam, canc)

    def _dominio_perdido(self, antes: Expr, depois: Expr, ctx: Contexto) -> tuple[Condicao, ...]:
        """Obrigações de "antes" que somem em "depois" (``a/x · x → a``): o motor
        as declara como condição, lembrando o domínio da equação original."""
        o_d = obrigacoes(depois)
        out: list[Condicao] = []
        for o in obrigacoes(antes):
            if isinstance(o, Obrigacao) and o not in o_d and not ctx.garantido(o.expr, o.predicado):
                out += ctx.condicao(o.expr, o.predicado)
        return tuple(out)

    def _certificar(self, cam: _Caminho, p: Proposta) -> None:
        extra = self._dominio_perdido(cam.eq, p.depois, self._ctx) \
            if p.operacao.nome == "reescrever" else ()
        passo = Passo(antes=cam.eq, depois=p.depois, operacao=p.operacao, relacao=p.relacao,
                      tipo="algebra", indice=len(cam.passos) + 1, regra=p.regra,
                      condicoes=p.condicoes + tuple(c for c in extra if c not in p.condicoes),
                      justificativa={**p.justificativa, "fundivel": p.fundivel})
        cert = self.verificador.certificar(passo)
        if cert.estado != "aprovado":
            raise _Falha(Motivo("isolar.passo_reprovado", {"regra": p.regra}), {
                "regra": p.regra, "antes": para_latex(cam.eq), "depois": para_latex(p.depois),
                "motivos": [m.chave for m in cert.motivos]})
        assert isinstance(p.depois, Eq)
        cam.passos.append(passo)
        cam.eq = p.depois

    def _fechar(self, eq0: Eq, cam: _Caminho) -> RamoResolvido:
        cadeia = self.verificador.certificar_cadeia(cam.passos)
        if cadeia.estado != "aprovado":
            raise _Falha(Motivo("isolar.cadeia_reprovada"))
        conds = tuple(c for p in cam.passos for c in p.condicoes)
        alvo = cam.eq.esq
        assert isinstance(alvo, Sym)
        v2 = self.verificador.verificar_solucao(eq0, alvo, cam.eq.dir, conds)
        validade: tuple[Condicao, ...] = ()
        if not v2.aprovado and v2.faltam:
            # o resultado vale com condições a mais (L = μv/τ exige v ≠ 0): elas viram
            # hipóteses exibidas, e V2 roda de novo com elas
            validade = tuple(c for c in v2.faltam if c not in conds)
            v2 = self.verificador.verificar_solucao(eq0, alvo, cam.eq.dir, conds + validade)
        if not v2.aprovado:
            raise _Falha(Motivo("isolar.v2_reprovado", {"detalhe": v2.motivo}))
        return RamoResolvido(cam.rotulo, cam.passos, cam.eq, cadeia, validade)

    # ------------------------------------------------------------ várias ocorrências

    def _reunir(self, eq: Eq, ctx: Contexto) -> list[Proposta]:
        """Alvo em vários lugares: tudo à esquerda, sem denominador com o alvo, e
        agrupado se a expressão for linear no alvo."""
        u = ctx.conv.valor_simbolo(ctx.alvo)
        if eq.dir != Num("0"):
            return [Proposta("levar_para_a_esquerda", Eq(Sub(eq.esq, eq.dir), Sub(eq.dir, eq.dir)),
                             Operacao("subtrair_ambos", eq.dir),
                             justificativa=_j("regra.levar_para_a_esquerda", termo=eq.dir))]
        f = ctx.conv(eq.esq)
        num, den = sp.fraction(sp.together(f))
        if den.has(u):
            d = self._denominador_como_escrito(eq.esq, den, ctx) or de_sympy(den, self.tabela)
            # 0·d = 0: o lado direito continua 0, sem um "0(1 + kτ)" para carregar adiante
            return [Proposta("eliminar_denominador", Eq(Mul((eq.esq, d)), eq.dir),
                             Operacao("multiplicar_ambos", d),
                             justificativa=_j("regra.eliminar_denominador", fator=d))]
        # linear em u: f = a·u + b, com a = ∂f/∂u e b = f(u = 0); nada é expandido,
        # e logaritmos como ln(T₂/T₁) ficam inteiros
        alvo_f = num if den == 1 else f
        try:
            a = sp.diff(alvo_f, u)
            b = alvo_f.subs(u, 0)
        except Exception:
            raise _Falha(Motivo("isolar.sem_forma_fechada")) from None
        if a.has(u) or a == 0 or sp.expand(alvo_f - (a * u + b), log=False) != 0:
            raise _Falha(Motivo("isolar.sem_forma_fechada"))
        termo_u = Mul((de_sympy(a, self.tabela), Sym(ctx.alvo))) if a != 1 else Sym(ctx.alvo)
        if b == 0:
            agrupado: Expr = termo_u
        else:
            agrupado = Add((termo_u, de_sympy(b, self.tabela)))
        return [Proposta("agrupar_no_alvo", Eq(agrupado, eq.dir),
                         Operacao("reescrever", lado="esquerdo"),
                         justificativa=_j("regra.agrupar_no_alvo", alvo=Sym(ctx.alvo)))]

    @staticmethod
    def _denominador_como_escrito(e: Expr, den: Any, ctx: Contexto) -> Expr | None:
        """O denominador na forma em que aparece na equação (``1 + kτ``), não na do SymPy (``τk + 1``)."""
        for n in percorrer(e):
            if isinstance(n, Div) and n.den.__class__ is not Num:
                try:
                    if sp.expand(ctx.conv(n.den) - den) == 0:
                        return n.den
                except Exception:
                    continue
        return None

    # ------------------------------------------------------------ oráculo

    def _sem_passos(self, eq: Eq, alvo: Sym, res: ResultadoIsolar) -> ResultadoIsolar:
        """Resultado do oráculo, só se passar em V2 (seção 5.2)."""
        conv = self.verificador.conv
        try:
            sols = sp.solve(sp.Eq(conv(eq.esq), conv(eq.dir)), conv(alvo), dict=False)
        except Exception:
            sols = []
        for s in sols if isinstance(sols, list) else []:
            try:
                e = de_sympy(s, self.tabela)
            except Exception:
                continue
            if self.verificador.verificar_solucao(eq, alvo, e).aprovado:
                res.sem_passos.append(Eq(alvo, e))
        res.estado = "sem_passos" if res.sem_passos else "recusado"
        return res


def isolar(equacao: Expr, alvo: Sym, tabela: TabelaDeSimbolos,
           glossario: Glossario) -> ResultadoIsolar:
    return Isolador(tabela, glossario).isolar(equacao, alvo)


__all__ = ["Isolador", "RamoResolvido", "ResultadoIsolar", "isolar"]
