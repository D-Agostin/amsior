# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Isolar uma variável com passos (seção 4.2).

Fluxo:

1. pré-checagem: equação, alvo presente, homogeneidade dimensional;
2. alvo uma vez só: descascar, desfazendo a operação mais externa
   (``rules.isolar``), com um passo de cancelamento depois de cada operação;
3. alvo várias vezes: levar tudo para a esquerda, eliminar denominadores com
   o alvo e, se a expressão for linear no alvo, agrupar e dividir; se for do
   2º grau, escrever na forma padrão e completar o quadrado;
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
from amsior.expr.nos import Add, Div, Eq, Expr, Mul, Neg, Num, Pow, Sqrt, Sub, Sym
from amsior.expr.ponte_sympy import de_sympy
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.rules.classificar import Classificacao, classificar
from amsior.rules.simplificar import apresentar
from amsior.rules.isolar import (
    Contexto, Proposta, Ramo, Recusa, _j, descascar, passo_de_calculo, passo_de_cancelamento,
    trocar_lados,
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
            try:
                prontos.append(self._fechar(eq0, cam))
            except _Falha as f:
                estranha = self._raiz_estranha(eq0, cam, ctx) if f.motivo.chave == "isolar.v2_reprovado" else None
                if estranha is None:
                    raise
                res.descartados.append(estranha)
        if not prontos:
            raise _Falha(Motivo("isolar.so_raizes_estranhas"))
        return prontos

    def _raiz_estranha(self, eq0: Eq, cam: _Caminho, ctx: Contexto) -> Motivo | None:
        """Candidata numérica que não satisfaz a equação original (seção 4.2, item 6).

        Só vale depois de um passo que não é equivalência pura (elevar ao quadrado,
        eliminar denominador, raiz par com condição): ali podem nascer raízes que a
        equação original não tem. A candidata é substituída na equação original; se
        ela não a satisfaz (ou cai fora do domínio), o ramo é descartado com o motivo.
        Resultado literal não é descartado assim: a falha continua sendo falha.
        """
        if not any(p.relacao == "implica" or p.condicoes for p in cam.passos):
            return None
        if livres(cam.eq.dir):
            return None
        conv = self.verificador.conv
        u = conv(Sym(ctx.alvo))
        valor = conv(cam.eq.dir)
        try:
            dif = sp.simplify((conv(eq0.esq) - conv(eq0.dir)).subs(u, valor))
        except Exception:
            dif = sp.nan
        if dif == 0:
            return None  # satisfaz: a falha de V2 era outra coisa
        return Motivo("ramo.raiz_estranha", {"valor": para_latex(cam.eq.dir), "alvo": ctx.alvo})

    def _proximo(self, eq: Eq, ctx: Contexto) -> list[Ramo]:
        na_esq, na_dir = ctx.tem(eq.esq), ctx.tem(eq.dir)
        if na_dir and not na_esq:
            return [Ramo([trocar_lados(eq)])]
        if na_esq and not na_dir and _ocorrencias(eq.esq, ctx.alvo) == 1:
            r = descascar(eq, ctx)
            if isinstance(r, Recusa):
                raise _Falha(Motivo(r.chave, r.args))
            return r
        radical = self._isolar_radical(eq, ctx)
        if radical is not None:
            return [Ramo([radical])]
        return [Ramo(self._reunir(eq, ctx))]

    def _isolar_radical(self, eq: Eq, ctx: Contexto) -> Proposta | None:
        """√A = B com o alvo em A e em B: eleva os dois lados ao quadrado.

        O passo vale sob a condição B ≥ 0 (a raiz quadrada não é negativa); sem ela,
        só implica. As candidatas que violam a condição são as raízes estranhas, que
        a conferência na equação original descarta no fim de cada ramo.
        """
        for lado_r, lado_o, inverter in ((eq.esq, eq.dir, False), (eq.dir, eq.esq, True)):
            if isinstance(lado_r, Sqrt) and ctx.tem(lado_r) and ctx.tem(lado_o):
                dois = Num("2")
                depois = Eq(lado_r.a, Pow(lado_o, dois)) if not inverter else Eq(Pow(lado_o, dois), lado_r.a)
                return Proposta("elevar_os_dois_lados", depois, Operacao("elevar_ambos", dois),
                                condicoes=ctx.condicao(lado_o, "nao_negativo"),
                                justificativa=_j("regra.elevar_ao_quadrado_radical", termo=lado_o))
        return None

    def _aplicar(self, cam: _Caminho, propostas: list[Proposta]) -> None:
        for p in propostas:
            self._certificar(cam, p)
            assert isinstance(cam.eq, Eq)
            canc = passo_de_cancelamento(cam.eq)
            if canc is not None:
                self._certificar(cam, canc)
            calc = passo_de_calculo(cam.eq, self._ctx)
            if calc is not None:
                self._certificar(cam, calc)

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
        # reescrever (ou trocar o sinal) pode sumir com um denominador: o domínio da
        # equação de antes vira condição declarada
        troca_sinal = p.operacao.nome == "multiplicar_ambos" and p.operacao.argumento == Neg(Num("1"))
        extra = self._dominio_perdido(cam.eq, p.depois, self._ctx) \
            if p.operacao.nome == "reescrever" or troca_sinal else ()
        passo = Passo(antes=cam.eq, depois=p.depois, operacao=p.operacao, relacao=p.relacao,
                      tipo="algebra", indice=len(cam.passos) + 1, regra=p.regra,
                      condicoes=tuple(dict.fromkeys(p.condicoes + extra)),
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
        if not alvo_f.has(u):
            # o alvo sumiu ao simplificar: x/(x − 1) = 1/(x − 1) vira 1 = 0 no domínio
            raise _Falha(Motivo("isolar.identidade" if sp.simplify(alvo_f) == 0 else "isolar.sem_solucao"))
        try:
            a = sp.diff(alvo_f, u)
            b = alvo_f.subs(u, 0)
        except Exception:
            raise _Falha(Motivo("isolar.sem_regra_reunir")) from None
        if a.has(u) or a == 0 or sp.expand(alvo_f - (a * u + b), log=False) != 0:
            quad = self._quadratica(eq, alvo_f, u, ctx)
            if quad is not None:
                return quad
            raise _Falha(Motivo("isolar.sem_regra_reunir"))
        # coeficiente na frente e sinais à mostra: "−3x − 1", não "(−3)x + (−1)"
        agrupado: Expr = _soma([(a, Sym(ctx.alvo)), (b, None)], self.tabela)
        return [Proposta("agrupar_no_alvo", Eq(agrupado, eq.dir),
                         Operacao("reescrever", lado="esquerdo"),
                         justificativa=_j("regra.agrupar_no_alvo", alvo=Sym(ctx.alvo)))]

    def _quadratica(self, eq: Eq, f: Any, u: Any, ctx: Contexto) -> list[Proposta] | None:
        """Do 2º grau no alvo: forma padrão e completar o quadrado (seção 4.2, item 4).

        ``a u² + b u + c = 0`` é dividida por a (a ≠ 0) e vira ``(u + b/2a)² = Δ/4a²``,
        com Δ = b² − 4ac, somando aos dois lados o que falta para o quadrado perfeito.
        Daí em diante o alvo aparece uma vez só, e as regras de sempre (raiz par com os
        dois ramos, subtrair) levam à fórmula resolutiva, cada passo certificado.
        A condição Δ/4a² ≥ 0 da raiz par é a análise do discriminante; Δ numérico
        negativo é recusado antes, e Δ = 0 dá a raiz dupla.
        """
        try:
            poli = sp.Poly(f, u)
        except Exception:
            return None
        if poli.degree() != 2:
            return None
        a, b, c = poli.all_coeffs()
        if any(co.has(u) for co in (a, b, c)):
            return None
        delta = sp.expand(b**2 - 4 * a * c)
        tab = self.tabela
        if delta.is_number and delta.is_negative:
            raise _Falha(Motivo("isolar.discriminante_negativo", {"delta": para_latex(de_sympy(delta, tab))}))
        x = Sym(ctx.alvo)
        out: list[Proposta] = []
        # a numérico negativo: multiplica por −1 primeiro, para o termo em u² ficar positivo
        trocar_sinal = bool(a.is_number and a.is_negative)
        if trocar_sinal:
            a, b, c = -a, -b, -c
        padrao = _soma([(a, Pow(x, Num("2"))), (b, x), (c, None)], tab)
        if trocar_sinal:
            out.append(Proposta("forma_padrao_quadratica", Eq(padrao, Num("0")),
                                Operacao("multiplicar_ambos", Neg(Num("1"))),
                                justificativa=_j("regra.forma_padrao_quadratica_sinal", alvo=x)))
        elif eq.esq != padrao:
            out.append(Proposta("forma_padrao_quadratica", Eq(padrao, eq.dir),
                                Operacao("reescrever", lado="esquerdo"),
                                justificativa=_j("regra.forma_padrao_quadratica", alvo=x)))
        if a != 1:
            # dividir por a: o termo em u² fica com coeficiente 1 (u² + pu + q = 0)
            a_expr = de_sympy(a, tab)
            b, c = sp.simplify(b / a), sp.simplify(c / a)
            out.append(Proposta("dividir_pelo_coeficiente",
                                Eq(_soma([(sp.Integer(1), Pow(x, Num("2"))), (b, x), (c, None)], tab), Num("0")),
                                Operacao("dividir_ambos", a_expr),
                                condicoes=ctx.condicao(a_expr, "nao_nulo"),
                                justificativa=_j("regra.dividir_pelo_coeficiente", alvo=x, coeficiente=a_expr)))
        # u² + pu + q = 0  →  (u + p/2)² = p²/4 − q = Δ/4a²
        h = sp.factor(b / 2) if (b / 2).is_rational_function() else sp.simplify(b / 2)
        quadrado = Pow(_soma([(sp.Integer(1), x), (h, None)], tab), Num("2"))
        resto = sp.together(b**2 / 4 - c)
        j = _j("regra.completar_quadrado", alvo=x, delta=de_sympy(delta, tab))
        if resto == 0:
            out.append(Proposta("completar_quadrado", Eq(quadrado, Num("0")),
                                Operacao("reescrever", lado="esquerdo"), justificativa=j))
            return out
        # o que falta somar, na forma Δ/4a² quando é literal (b² − 4ac sobre 4a²)
        num, den = sp.fraction(resto)
        # negativo só se todas as parcelas são (−4ac + b² fica como b² − 4ac, somado)
        negativo = all(t.could_extract_minus_sign() for t in sp.Add.make_args(sp.expand(num)))
        if negativo:
            num = -num
        if resto.is_number:
            termo = de_sympy(-resto if negativo else resto, tab)
        else:
            numerador = _positivos_primeiro(sp.expand(num), tab)
            termo = Div(numerador, de_sympy(den, tab)) if den != 1 else numerador
        if negativo:
            out.append(Proposta("completar_quadrado", Eq(quadrado, Neg(termo)),
                                Operacao("subtrair_ambos", termo), justificativa=j))
        else:
            out.append(Proposta("completar_quadrado", Eq(quadrado, termo),
                                Operacao("somar_ambos", termo), justificativa=j))
        return out

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


def _positivos_primeiro(e: Any, tabela: TabelaDeSimbolos) -> Expr:
    """``−4ac + b²`` → ``b² − 4ac``: parcelas positivas, depois as negativas subtraídas."""
    pos = [t for t in sp.Add.make_args(e) if not t.could_extract_minus_sign()]
    neg = [-t for t in sp.Add.make_args(e) if t.could_extract_minus_sign()]
    if not pos or not neg:
        return de_sympy(e, tabela)
    return Sub(de_sympy(sp.Add(*pos), tabela), de_sympy(sp.Add(*neg), tabela))


def _soma(termos: list[tuple[Any, Expr | None]], tabela: TabelaDeSimbolos) -> Expr:
    """Σ coeficiente·monômio na ordem dada (grau decrescente), sem termos nulos e com
    subtração no lugar de "+ −"; mesma forma que ``simplificar.soma`` produz."""
    partes: list[tuple[int, Expr]] = []
    for coef, mono in termos:
        if coef == 0:
            continue
        if coef.is_rational_function():  # −(2D + 1)/(2D), não (−2D − 1)/(2D); ln fica intacto
            coef = sp.factor(coef)
        neg = bool(coef.could_extract_minus_sign())
        mag = -coef if neg else coef
        if mono is None:
            termo: Expr = de_sympy(mag, tabela)
        elif mag == 1:
            termo = mono
        else:
            termo = Mul((de_sympy(mag, tabela), mono))
        partes.append((-1 if neg else 1, termo))
    if not partes:
        return Num("0")
    s0, t0 = partes[0]
    acc: Expr = t0 if s0 > 0 else Neg(t0)
    for sinal, t in partes[1:]:
        if sinal < 0:
            acc = Sub(acc, t)
        else:
            acc = Add((*acc.termos, t)) if isinstance(acc, Add) else Add((acc, t))
    return acc


def isolar(equacao: Expr, alvo: Sym, tabela: TabelaDeSimbolos,
           glossario: Glossario) -> ResultadoIsolar:
    return Isolador(tabela, glossario).isolar(equacao, alvo)


__all__ = ["Isolador", "RamoResolvido", "ResultadoIsolar", "isolar"]
