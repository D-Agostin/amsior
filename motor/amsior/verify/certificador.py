# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Certificação de passos (V1, V5), de cadeias de passos e de soluções (V2).

O verificador não confia no motor: recebe ``antes``, ``depois`` e a operação
declarada, refaz a operação pela sua própria tabela (``operacoes.py``) e
exige identidade lado a lado. Também calcula, na árvore, o domínio dos dois
lados (``dominio.py``) e decide sozinho:

* se o passo **restringiu** o domínio (obrigação nova em "depois"): só vale se
  a condição estiver declarada, e então o passo fica *sob hipótese*;
* se o passo **alargou** o domínio (obrigação de "antes" que some em
  "depois"): a relação máxima é ``implica``;
* se alguma obrigação é falsa com certeza (``ln(−u)`` com ``u > 0``): reprova.

Nada que o passo afirma sobre si mesmo é aceito sem conferência, e qualquer
falha interna vira reprovação (``verif.erro_interno``), nunca exceção.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata
from typing import Any

import mpmath
import sympy as sp

from amsior.expr.latex import para_latex
from amsior.expr.nos import Eq, Expr, Ge, Gt, Integral, Le, Lt, Ne, Sym
from amsior.expr.ponte_sympy import ParaSympy
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.units.glossario import Glossario
from amsior.units.homogeneidade import verificar_homogeneidade
from amsior.verify.amostragem import satisfaziveis
from amsior.verify.arvore import (
    chave, livres, percorrer, sem_dependencia, substituir, tem_funcao_de, variaveis_ligadas,
)
from amsior.verify.avaliador import _semente
from amsior.verify.dominio import (
    Exigido, Obrigacao, ObrigacaoIntegral, Predicado, obrigacoes, opacificar,
)
from amsior.verify.identidade import Comparador, ResultadoIdentidade
from amsior.verify.logica import BaseDeFatos, base, por_suposicao, refutado_por_suposicao
from amsior.verify.modelo import (
    RELACOES, Certificado, Condicao, Contexto, EstadoCert, MetodoCert, Motivo, Operacao, Passo,
    Relacao,
)
from amsior.verify.operacoes import OPERACOES, OPERACOES_DE_CALCULO, EfeitoOperacao, Exigencia

provavel = por_suposicao  # nome antigo, mantido para quem importa do pacote
_DESIGUALDADES = (Ne, Gt, Ge, Lt, Le)


def _versoes() -> dict[str, str]:
    try:
        amsior_v = metadata.version("amsior")
    except metadata.PackageNotFoundError:  # pragma: no cover - rodando sem instalar
        amsior_v = "desconhecida"
    return {"amsior": amsior_v, "sympy": sp.__version__, "mpmath": mpmath.__version__}


@dataclass
class _CondNorm:
    origem: Condicao
    expr: Expr
    q: Any
    predicado: Predicado
    rotulo: str


@dataclass
class _Estado:
    motivos: list[Motivo] = field(default_factory=list)
    reprovado: bool = False
    numerico: bool = False
    usados: set[str] = field(default_factory=set)
    equivalencia_perdida: bool = False
    hipoteses: list[Motivo] = field(default_factory=list)
    exigencias: list[dict[str, str]] = field(default_factory=list)
    amostragem: list[dict[str, Any]] = field(default_factory=list)

    def falha(self, chave_: str, **args: str) -> None:
        self.reprovado = True
        m = Motivo(chave_, dict(args))
        if m not in self.motivos:
            self.motivos.append(m)

    def hipotese(self, m: Motivo) -> None:
        if m not in self.hipoteses:
            self.hipoteses.append(m)


@dataclass
class CertificadoCadeia:
    estado: EstadoCert
    relacao: Relacao
    sob_hipotese: bool
    hipoteses: list[Motivo]
    motivos: list[Motivo]
    certificados: list[Certificado]


class Verificador:
    def __init__(self, tabela: TabelaDeSimbolos, glossario: Glossario) -> None:
        self.tabela = tabela
        self.glossario = glossario
        self.conv = ParaSympy(tabela)

    # ------------------------------------------------------------ certificação

    def certificar(self, passo: Passo, contexto: Contexto = "motor") -> Certificado:
        """Certifica um passo. ``contexto="ficha"`` só para demonstrações curadas."""
        try:
            return self._certificar(passo, contexto)
        except Exception as exc:  # o verificador nunca deixa escapar exceção
            cert = Certificado("simbolico", "reprovado",
                               [Motivo("verif.erro_interno", {"erro": type(exc).__name__})],
                               "nao_executado", "nao_executado", versoes=_versoes())
            passo.certificado = cert
            return cert

    def _certificar(self, passo: Passo, contexto: Contexto) -> Certificado:  # noqa: C901
        st = _Estado()
        if passo.tipo in ("principio", "aproximacao"):
            if contexto != "ficha":
                st.falha("verif.principio_fora_de_ficha", tipo=passo.tipo)
                return self._fechar(passo, st, (), "nao_executado", "nao_executado")
            v5 = self._v5(passo, st)
            estado: EstadoCert = "reprovado" if st.reprovado else "pendente"
            st.motivos.append(Motivo("verif.revisao_humana_exigida"))
            cert = Certificado("revisao_humana", estado, st.motivos, "pendente", v5,
                               versoes=_versoes())
            passo.certificado = cert
            return cert

        if passo.relacao not in RELACOES:
            st.falha("verif.relacao_invalida", relacao=str(passo.relacao))
        op = passo.operacao
        if op.nome not in OPERACOES:
            st.falha("verif.operacao_desconhecida", operacao=op.nome)
            return self._fechar(passo, st, (), "nao_executado", "nao_executado")
        funcao, exige_arg = OPERACOES[op.nome]
        if exige_arg and op.argumento is None:
            st.falha("verif.argumento_ausente", operacao=op.nome)
            return self._fechar(passo, st, (), "nao_executado", "nao_executado")
        if any(isinstance(e, _DESIGUALDADES) for e in (passo.antes, passo.depois)):
            st.falha("verif.desigualdade_nao_suportada")
            return self._fechar(passo, st, (), "nao_executado", "nao_executado")
        lados = self._lados(passo, st)
        if lados is None:
            return self._fechar(passo, st, (), "nao_executado", "nao_executado")
        L, R, Ld, Rd = lados

        comp = Comparador(self.tabela, _semente(chave(passo.antes), chave(passo.depois), op.nome))
        conds = self._conferir_condicoes(passo, st, comp)
        if st.reprovado:
            return self._fechar(passo, st, (), "nao_executado", "nao_executado")

        # substituição: feita na árvore, sempre como hipótese exibida
        if op.nome == "substituir":
            assert op.argumento is not None
            if op.simbolo is None:
                st.falha("verif.substituicao_incompleta")
                return self._fechar(passo, st, (), "nao_executado", "nao_executado")
            sid = op.simbolo.id
            if sid in livres(op.argumento):
                st.falha("verif.substituicao_recursiva", simbolo=sid)
            if sid in variaveis_ligadas(passo.antes) or any(
                    sid in s.depende_de for n in percorrer(passo.antes) if isinstance(n, Sym)
                    for s in [self.tabela.obter(n.id)] if s is not None):
                st.falha("verif.substituicao_variavel_ligada", simbolo=sid)
            if st.reprovado:
                return self._fechar(passo, st, (), "nao_executado", "nao_executado")
            L = substituir(L, sid, op.argumento)
            R = substituir(R, sid, op.argumento) if R is not None else None
            st.hipotese(Motivo("hipotese.substituicao", {
                "simbolo": sid, "expressao": para_latex(op.argumento),
                "origem": f"origem.{op.origem or 'hipotese'}"}))

        if op.nome in ("reescrever", "substituir") or R is None:
            ef = EfeitoOperacao(L, R if R is not None else L)
        else:
            ef = funcao(L, R, op.argumento)
            if ef.erro:
                st.falha(ef.erro, operacao=op.nome,
                         argumento="" if op.argumento is None else para_latex(op.argumento))
                return self._fechar(passo, st, (), "nao_executado", "nao_executado")

        if op.nome in OPERACOES_DE_CALCULO and R is not None:
            self._exigir_identidade(passo, L, R, comp, st)

        if op.lado == "esquerdo" and R is not None and not self._mesmo(passo, "dir"):
            st.falha("verif.lado_alterado", lado="direito")
        if op.lado == "direito" and R is not None and not self._mesmo(passo, "esq"):
            st.falha("verif.lado_alterado", lado="esquerdo")

        pares = [(ef.esquerdo, Ld, "esquerdo" if R is not None else "expressao")]
        if R is not None:
            assert Rd is not None
            pares.append((ef.direito, Rd, "direito"))
        for esperado, obtido, lado in pares:
            self._comparar(esperado, obtido, lado, conds, comp, st)
        v1 = "reprovado" if st.reprovado else "aprovado"

        esperados = [ef.esquerdo] + ([ef.direito] if R is not None else [])
        self._dominio(passo, esperados, ef.exigencias, conds, st)

        permitidas: tuple[Relacao, ...] = ("implica",) if (
            ef.relacao_base == "implica" or st.equivalencia_perdida) else ("equivalente", "implica")
        if passo.relacao in RELACOES and passo.relacao not in permitidas:
            st.falha("verif.relacao_otimista", declarada=passo.relacao,
                     permitidas=", ".join(permitidas))

        for c in conds:
            if c.rotulo in st.usados:
                st.hipotese(Motivo("hipotese.condicao", {"condicao": para_latex(c.expr)}))
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
        cert = Certificado(metodo, estado, st.motivos, v1, v5, permitidas,
                           sob_hipotese=bool(st.hipoteses), hipoteses=st.hipoteses,
                           exigencias=st.exigencias, amostragem=st.amostragem,
                           versoes=_versoes())
        passo.certificado = cert
        return cert

    # ------------------------------------------------------------ partes

    def _lados(self, passo: Passo, st: _Estado) -> tuple[Expr, Expr | None, Expr, Expr | None] | None:
        a, d = passo.antes, passo.depois
        if isinstance(a, Eq) and isinstance(d, Eq):
            return a.esq, a.dir, d.esq, d.dir
        if passo.operacao.nome in ("reescrever", "substituir") and not isinstance(a, Eq) \
                and not isinstance(d, Eq):
            return a, None, d, None
        st.falha("verif.passo_sem_equacao")
        return None

    def _mesmo(self, passo: Passo, lado: str) -> bool:
        a, d = passo.antes, passo.depois
        assert isinstance(a, Eq) and isinstance(d, Eq)
        return bool(getattr(a, lado) == getattr(d, lado))

    def _conferir_condicoes(self, passo: Passo, st: _Estado, comp: Comparador) -> list[_CondNorm]:
        conds: list[_CondNorm] = []
        for i, c in enumerate(passo.condicoes):
            e = c.expr
            if not isinstance(e, _DESIGUALDADES):
                st.falha("verif.condicao_invalida", condicao=para_latex(e))
                continue
            a, b = self.conv(e.esq), self.conv(e.dir)
            formas: dict[type, tuple[Any, Predicado]] = {
                Gt: (a - b, "positivo"), Ge: (a - b, "nao_negativo"),
                Lt: (b - a, "positivo"), Le: (b - a, "nao_negativo"), Ne: (a - b, "nao_nulo")}
            q, pred = formas[type(e)]
            if refutado_por_suposicao(q, pred):
                st.falha("verif.condicoes_insatisfativeis", condicao=para_latex(e))
                continue
            garantida = por_suposicao(q, pred)
            if (c.satisfeita is True or c.origem == "suposicao") and not garantida:
                st.falha("verif.condicao_otimista", condicao=para_latex(e))
            if not garantida:
                conds.append(_CondNorm(c, e, q, pred, f"cond:{i}"))
        if conds and not st.reprovado and not satisfaziveis(
                [c.expr for c in conds], self.tabela, comp.avaliador):
            st.falha("verif.condicoes_insatisfativeis",
                     condicao=", ".join(para_latex(c.expr) for c in conds))
        return conds

    def _exigir_identidade(self, passo: Passo, L: Expr, R: Expr, comp: Comparador,
                           st: _Estado) -> None:
        """Derivar ou integrar os dois lados só vale para equação que vale em todo ``v``."""
        v = passo.operacao.argumento
        assert isinstance(v, Sym)
        if tem_funcao_de(passo.antes, v.id, self.tabela):
            return  # relação entre funções de v (y(x) = x², dC/dt = −kC)
        if comp.comparar(L, R).aprovado:
            return  # identidade provada
        if passo.operacao.identidade:
            st.hipotese(Motivo("hipotese.identidade", {"variavel": v.id}))
            return
        st.falha("verif.equacao_nao_e_identidade", variavel=v.id)

    def _comparar(self, esperado: Expr, obtido: Expr, lado: str, conds: list[_CondNorm],
                  comp: Comparador, st: _Estado) -> None:
        r: ResultadoIdentidade = comp.comparar(esperado, obtido)
        if not r.aprovado and conds:
            r2 = comp.comparar(esperado, obtido, [c.expr for c in conds])
            if r2.aprovado:
                st.usados |= {c.rotulo for c in conds}
                r = r2
        if r.numerico is not None:
            st.amostragem.append({"lado": lado, **r.numerico.auditoria()})
        if not r.aprovado:
            st.falha("verif.lado_nao_confere", lado=lado, detalhe=r.motivo,
                     esperado=para_latex(esperado), obtido=para_latex(obtido))
            self._opacos_alterados(esperado, obtido, st)
            return
        if r.metodo == "numerico":
            st.numerico = True
        self._integrais_calculadas(esperado, obtido, st)

    def _opacos_alterados(self, esperado: Expr, obtido: Expr, st: _Estado) -> None:
        """Explica a falha quando o passo "calculou" um objeto opaco."""
        a = opacificar(esperado, self.tabela).opacos
        b = opacificar(obtido, self.tabela).opacos
        for k in sorted(set(a) ^ set(b)):
            o = a.get(k) or b[k]
            if o.tipo == "derivada_sem_dependencia":
                st.falha("verif.dependencia_nao_declarada", derivada=k,
                         simbolos=", ".join(o.simbolos), variavel=o.variavel)
            elif o.tipo == "primitiva":
                st.falha("verif.integral_indefinida", integral=k)

    def _integrais_calculadas(self, esperado: Expr, obtido: Expr, st: _Estado) -> None:
        """Integral definida calculada: variáveis sem dependência declarada foram
        tratadas como constantes, e isso vira hipótese exibida (ex.: T constante
        no trabalho isotérmico)."""
        def definidas(e: Expr) -> dict[str, Integral]:
            return {chave(n): n for n in percorrer(e)
                    if isinstance(n, Integral) and n.inferior is not None}
        a, b = definidas(esperado), definidas(obtido)
        for k in sorted(set(a) ^ set(b)):
            n = a.get(k) or b[k]
            faltam = sem_dependencia(n.f, n.var.id, self.tabela)
            if faltam:
                st.hipotese(Motivo("hipotese.independe", {
                    "simbolos": ", ".join(faltam), "variavel": n.var.id}))

    # ------------------------------------------------------------ domínio

    def _fatos(self, obr: list[Exigido], rotulo: str) -> list[tuple[Any, Predicado, str]]:
        out: list[tuple[Any, Predicado, str]] = []
        for o in obr:
            if isinstance(o, Obrigacao):
                out.append((self.conv(o.expr), o.predicado, rotulo))
            else:  # o integrando existe também nas extremidades
                for i in o.internas:
                    for ponta in (o.inferior, o.superior):
                        out.append((self.conv(substituir(i.expr, o.var.id, ponta)),
                                    i.predicado, rotulo))
        return out

    @staticmethod
    def _assinatura(o: ObrigacaoIntegral) -> tuple[str, str, str, frozenset[tuple[str, str]]]:
        return (o.var.id, chave(o.inferior), chave(o.superior),
                frozenset((chave(i.expr), i.predicado) for i in o.internas))

    def _provar(self, o: Exigido, fatos: BaseDeFatos, integrais: list[ObrigacaoIntegral],
                rotulo: str) -> set[str] | None:
        if isinstance(o, Obrigacao):
            return fatos.provar(self.conv(o.expr), o.predicado)
        if any(self._assinatura(o) == self._assinatura(i) for i in integrais):
            return {rotulo}
        lo, hi = self.conv(o.inferior), self.conv(o.superior)
        usados: set[str] = set()
        sup: dict[str, bool] = {"real": True}
        for pred, chave_sp, sinal in (("positivo", "positive", 1), ("positivo", "negative", -1),
                                      ("nao_negativo", "nonnegative", 1)):
            r1, r2 = fatos.provar(sinal * lo, pred), fatos.provar(sinal * hi, pred)  # type: ignore[arg-type]
            if r1 is not None and r2 is not None:
                sup = {chave_sp: True}
                usados |= r1 | r2
                break
        w = sp.Dummy("w", **sup)
        var = self.conv(o.var)
        for i in o.internas:
            q = self.conv(i.expr).xreplace({var: w})
            r = fatos.provar(q, i.predicado)
            if r is None:
                return None
            usados |= r
        return usados

    def _dominio(self, passo: Passo, esperados: list[Expr], exigencias: list[Exigencia],
                 conds: list[_CondNorm], st: _Estado) -> None:
        o_a, o_d = obrigacoes(passo.antes), obrigacoes(passo.depois)
        o_e: list[Exigido] = []
        for e in esperados:
            o_e += [o for o in obrigacoes(e) if o not in o_e]

        for o in (*o_a, *o_d, *o_e):
            if isinstance(o, Obrigacao) and refutado_por_suposicao(self.conv(o.expr), o.predicado):
                st.falha("verif.dominio_vazio", expressao=para_latex(o.expr),
                         predicado=f"predicado.{o.predicado}")
                return

        f_cond: list[tuple[Any, Predicado, str]] = [(c.q, c.predicado, c.rotulo) for c in conds]
        com_antes = base([*f_cond, *self._fatos(o_a, "antes")])
        com_depois = base([*f_cond, *self._fatos(o_d, "depois")])
        int_a = [o for o in o_a if isinstance(o, ObrigacaoIntegral)]
        int_d = [o for o in o_d if isinstance(o, ObrigacaoIntegral)]

        def registrar(o: Exigido, tipo: str, r: set[str] | None) -> None:
            if r is None:
                quem = "nao_atendida"
            elif not r:
                quem = "suposicao"
            elif any(x.startswith("cond:") for x in r):
                quem = "condicao"
                st.usados |= {x for x in r if x.startswith("cond:")}
            else:
                quem = "antes" if "antes" in r else "depois"
            texto = para_latex(o.expr) if isinstance(o, Obrigacao) else para_latex(o.origem)
            pred = o.predicado if isinstance(o, Obrigacao) else "intervalo"
            item = {"tipo": tipo, "expressao": texto, "predicado": pred, "atendida_por": quem}
            if item not in st.exigencias:
                st.exigencias.append(item)

        # 1. o que "depois" e a operação exigem tem de valer onde "antes" vale
        vistos: list[Exigido] = []
        for o in (*o_e, *o_d):
            if o in vistos:
                continue
            vistos.append(o)
            r = self._provar(o, com_antes, int_a, "antes")
            registrar(o, "dominio", r)
            if r is not None:
                continue
            if isinstance(o, Obrigacao):
                st.falha("verif.condicao_ausente", expressao=para_latex(o.expr),
                         predicado=f"predicado.{o.predicado}")
            else:
                st.falha("verif.condicao_ausente_intervalo", integrando=para_latex(o.origem.f),
                         variavel=o.var.id, inferior=para_latex(o.inferior),
                         superior=para_latex(o.superior))
        # 2. exigências de equivalência da operação
        for ex in exigencias:
            o = Obrigacao(ex.expr, ex.predicado)
            r = self._provar(o, com_antes, int_a, "antes")
            registrar(o, "equivalencia", r)
            if r is None:
                st.equivalencia_perdida = True
        # 3. o que "antes" exige e "depois" não: o passo alargou o domínio
        for o in o_a:
            r = self._provar(o, com_depois, int_d, "depois")
            registrar(o, "dominio_antes", r)
            if r is None:
                st.equivalencia_perdida = True

    def _v5(self, passo: Passo, st: _Estado) -> str:
        r = verificar_homogeneidade(passo.depois, self.tabela, self.glossario)
        if r.estado == "reprovado" and r.erro is not None:
            st.falha("verif.dimensional", erro=r.erro.mensagem())
        elif r.estado == "indeterminado":
            st.motivos.append(Motivo("verif.sem_grandeza",
                                     {"simbolos": ", ".join(sorted(r.sem_grandeza))}))
        return r.estado

    # ------------------------------------------------------------ cadeia

    def certificar_cadeia(self, passos: list[Passo],
                          contexto: Contexto = "motor") -> CertificadoCadeia:
        """Certifica cada passo e a ligação entre eles.

        * continuidade: o "depois" de um passo é o "antes" do seguinte;
        * composição: a cadeia é ``equivalente`` só se todos os passos forem,
          e as hipóteses se acumulam. Com algum ``implica``, as soluções da
          última equação precisam passar em V2 contra a primeira.
        """
        motivos: list[Motivo] = []
        certs = [self.certificar(p, contexto) for p in passos]
        for i in range(len(passos) - 1):
            if passos[i].depois != passos[i + 1].antes:
                motivos.append(Motivo("verif.cadeia_descontinua", {"passo": str(i + 1)}))
        hipoteses: list[Motivo] = []
        for c in certs:
            hipoteses += [h for h in c.hipoteses if h not in hipoteses]
        relacao: Relacao = "implica" if any(p.relacao == "implica" for p in passos) \
            else "equivalente"
        if motivos or any(c.estado == "reprovado" for c in certs):
            estado: EstadoCert = "reprovado"
        elif any(c.estado == "pendente" for c in certs):
            estado = "pendente"
        else:
            estado = "aprovado"
        return CertificadoCadeia(estado, relacao, bool(hipoteses), hipoteses, motivos, certs)

    # ------------------------------------------------------------ V2

    def verificar_solucao(self, equacao: Expr, alvo: Sym, solucao: Expr,
                          condicoes: tuple[Condicao, ...] = ()) -> ResultadoIdentidade:
        """V2: a solução satisfaz a equação original e cai no domínio dela."""
        if not isinstance(equacao, Eq):
            return ResultadoIdentidade(False, None, "verif.passo_sem_equacao")
        eq = substituir(equacao, alvo.id, solucao)
        assert isinstance(eq, Eq)
        st = _Estado()
        conds = self._conferir_condicoes(
            Passo(equacao, equacao, OPERACOES_FALSA, condicoes=condicoes), st,
            Comparador(self.tabela))
        if st.reprovado:
            return ResultadoIdentidade(False, None, st.motivos[0].chave)
        fatos = base([(c.q, c.predicado, c.rotulo) for c in conds])
        for o in obrigacoes(eq):
            if isinstance(o, Obrigacao) and refutado_por_suposicao(self.conv(o.expr), o.predicado):
                return ResultadoIdentidade(False, None, "verif.solucao_fora_do_dominio")
            if self._provar(o, fatos, [], "") is None:
                return ResultadoIdentidade(False, None, "verif.solucao_condicao_ausente")
        comp = Comparador(self.tabela, _semente(chave(eq)))
        r = comp.comparar(eq.esq, eq.dir)
        if not r.aprovado and conds:
            r = comp.comparar(eq.esq, eq.dir, [c.expr for c in conds])
        return r


OPERACOES_FALSA = Operacao("reescrever")


def certificar(passo: Passo, tabela: TabelaDeSimbolos, glossario: Glossario,
               contexto: Contexto = "motor") -> Certificado:
    return Verificador(tabela, glossario).certificar(passo, contexto)
