# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Identidade numérica: sorteio por estratos, precisão crescente e cobertura de ramos.

* **Estratos de magnitude.** Cada variável percorre seis faixas de três
  décadas entre 10⁻⁹ e 10⁹ (hipercubo latino em escala log), e parte dos
  pontos cai perto dos números que aparecem na expressão (2300, 273,15...).
  Assim ``|Re − 2300|`` e ``T − 273,15`` são testados dos dois lados.
* **Resíduo relativo sem piso.** ``|a − b| ≤ 10⁻³⁰·max(|a|, |b|)`` mais o
  ruído de arredondamento medido; ``6,6·10⁻³⁴ u`` e ``13,2·10⁻³⁴ u`` diferem.
* **Precisão crescente.** Cada lado é avaliado a 60 e a 120 dígitos (240 se
  instável). A diferença entre as duas é o ruído; um valor que só concorda
  dentro do ruído não esconde diferença maior que 10⁻¹¹⁰ da escala.
* **Cobertura de ramos.** Para cada subexpressão que escolhe ramo (argumento
  de módulo, ``w`` em ``√(w²)``), se a amostra só viu um sinal, uma varredura
  dirigida procura o outro; achando, o ponto também é comparado.
* **Domínio.** Pontos em que um dos lados não existe não entram na
  comparação: o domínio é julgado pelas obrigações (``dominio.py``). Mas se
  todas as obrigações de um lado valem e o avaliador não consegue o valor, a
  análise de domínio está incompleta e o passo reprova.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

import mpmath as mp

from amsior.expr.nos import Expr
from amsior.expr.simbolos import TabelaDeSimbolos
from amsior.verify.arvore import chave, livres, numeros, variaveis_de_amostragem
from amsior.verify.avaliador import Avaliador, _semente
from amsior.verify.dominio import Obrigacao, ObrigacaoIntegral, obrigacoes, sensiveis_a_sinal

PONTOS = 20
TENTATIVAS = 2000
LIMITE_RESIDUO = mp.mpf("1e-30")
PRECISOES = (60, 120, 240)
ESTRATOS = 6
EXPOENTE_MIN, EXPOENTE_MAX = -9.0, 9.0


@dataclass
class ResultadoNumerico:
    aprovado: bool
    motivo: str = ""
    pontos: int = 0
    pior_residuo: float = 0.0
    semente: int = 0
    digitos: int = PRECISOES[1]
    ramos: list[str] = field(default_factory=list)
    ramos_nao_alcancados: list[str] = field(default_factory=list)

    def auditoria(self) -> dict[str, Any]:
        return {"semente": self.semente, "pontos": self.pontos,
                "pior_residuo": self.pior_residuo, "digitos": self.digitos,
                "ramos": self.ramos, "ramos_nao_alcancados": self.ramos_nao_alcancados}


class Amostrador:
    def __init__(self, variaveis: list[str], tabela: TabelaDeSimbolos,
                 constantes: list[Fraction], semente: int) -> None:
        self.variaveis = variaveis
        self.tabela = tabela
        self.constantes = sorted({abs(c) for c in constantes if c not in (0, 1, -1)})
        self.rng = random.Random(semente)
        self._perms: dict[str, list[int]] = {}

    def _estrato(self, var: str, i: int) -> int:
        bloco = i // ESTRATOS
        k = (var, bloco)
        if k not in self._perms:  # type: ignore[comparison-overlap]
            p = list(range(ESTRATOS))
            self.rng.shuffle(p)
            self._perms[k] = p  # type: ignore[index]
        return self._perms[k][i % ESTRATOS]  # type: ignore[index]

    def magnitude(self, var: str, i: int) -> float:
        if self.constantes and self.rng.random() < 0.25:
            c = float(self.rng.choice(self.constantes))
            return c * 10 ** self.rng.uniform(-0.3, 0.3)
        largura = (EXPOENTE_MAX - EXPOENTE_MIN) / ESTRATOS
        base = EXPOENTE_MIN + largura * self._estrato(var, i)
        return float(10 ** self.rng.uniform(base, base + largura))

    def valor(self, var: str, mag: float) -> Any:
        sup = self.tabela.suposicoes(var)
        if "inteiro" in sup:
            n = self.rng.randint(1, 6)
            return mp.mpf(n if sup & {"positivo", "nao_negativo"} else self.rng.choice([-1, 1]) * n)
        if "positivo" in sup:
            return mp.mpf(mag)
        if "nao_negativo" in sup:
            return mp.mpf(0) if self.rng.random() < 0.05 else mp.mpf(mag)
        return mp.mpf(mag) * self.rng.choice([-1, 1])

    def ponto(self, i: int) -> dict[str, Any]:
        return {v: self.valor(v, self.magnitude(v, i)) for v in self.variaveis}

    def candidatos(self, var: str) -> list[Any]:
        """Valores da varredura dirigida (com sinal possível pelas suposições)."""
        mags = [10 ** (k / 2) for k in range(int(2 * EXPOENTE_MIN), int(2 * EXPOENTE_MAX) + 1)]
        for c in self.constantes:
            mags += [float(c) * f for f in (0.5, 0.9, 0.99, 1.01, 1.1, 2)]
        sup = self.tabela.suposicoes(var)
        sinais = [1] if sup & {"positivo", "nao_negativo"} else [1, -1]
        return [mp.mpf(s * m) for m in mags for s in sinais]


def avaliar_estavel(av: Avaliador, e: Expr, env: dict[str, Any]) -> tuple[Any, Any] | None:
    """(valor, ruído) no maior número de dígitos usado, ou None se fora do domínio."""
    anterior = None
    for dps in PRECISOES:
        with mp.workdps(dps):
            v = av.valor(e, env)
        if v is None or isinstance(v, bool):
            return None  # fora do domínio ou estouro (av.estourou diz qual)
        if anterior is not None:
            with mp.workdps(PRECISOES[-1]):
                ruido = abs(v - anterior)
                if ruido <= mp.mpf(10) ** -40 * abs(v) or dps == PRECISOES[-1]:
                    return v, ruido
        anterior = v
    return None  # pragma: no cover


def _iguais(a: tuple[Any, Any], b: tuple[Any, Any]) -> tuple[bool, Any]:
    with mp.workdps(PRECISOES[-1]):
        (va, ra), (vb, rb) = a, b
        escala = max(abs(va), abs(vb))
        dif = abs(va - vb)
        tol = LIMITE_RESIDUO * escala + 1000 * (ra + rb)
        residuo = mp.mpf(0) if escala == 0 else dif / escala
        return bool(dif <= tol), residuo


def _condicoes_ok(av: Avaliador, conds: list[Expr], env: dict[str, Any]) -> bool:
    with mp.workdps(PRECISOES[1]):
        return all(av.valor(c, env) is True for c in conds)


def _obrigacoes_valem(av: Avaliador, obr: list[Obrigacao | ObrigacaoIntegral],
                      env: dict[str, Any]) -> bool:
    with mp.workdps(PRECISOES[1]):
        for o in obr:
            if isinstance(o, ObrigacaoIntegral):
                if av.valor(o.origem, env) is None:
                    return False
                continue
            x = av.valor(o.expr, env)
            if x is None or isinstance(x, bool):
                return False
            if o.predicado == "positivo" and not x > 0 or \
                    o.predicado == "nao_negativo" and not x >= 0 or \
                    o.predicado == "nao_nulo" and x == 0:
                return False
    return True


def satisfaziveis(conds: list[Expr], tabela: TabelaDeSimbolos, av: Avaliador) -> bool:
    """Existe ao menos um ponto que satisfaz as suposições e todas as condições?"""
    if not conds:
        return True
    variaveis = variaveis_de_amostragem(conds, tabela)
    cts: list[Fraction] = [n for c in conds for n in numeros(c)]
    amostrador = Amostrador(variaveis, tabela, cts, _semente(*map(chave, conds)))
    for i in range(TENTATIVAS):
        if _condicoes_ok(av, conds, amostrador.ponto(i)):
            return True
    return False


def comparar_numerico(a: Expr, b: Expr, tabela: TabelaDeSimbolos, av: Avaliador,
                      condicoes: Sequence[Expr] = (), originais: tuple[Expr, Expr] | None = None,
                      ) -> ResultadoNumerico:
    """Compara ``a`` e ``b`` (já opacificadas) em pontos sorteados.

    ``originais`` são as formas antes da opacificação, de onde saem as
    obrigações de domínio usadas na conferência de consistência.
    """
    conds = list(condicoes)
    variaveis = variaveis_de_amostragem([a, b, *conds], tabela)
    cts = numeros(a) + numeros(b) + [n for c in conds for n in numeros(c)]
    semente = _semente(chave(a), chave(b), *map(chave, conds))
    amostrador = Amostrador(variaveis, tabela, cts, semente)
    oa, ob = (originais or (a, b))
    obr = (obrigacoes(oa), obrigacoes(ob))
    sensiveis = sensiveis_a_sinal(a) + [s for s in sensiveis_a_sinal(b)
                                        if s not in sensiveis_a_sinal(a)]
    sinais: dict[int, set[int]] = {i: set() for i in range(len(sensiveis))}
    res = ResultadoNumerico(True, semente=semente)
    pior = mp.mpf(0)
    validos: list[dict[str, Any]] = []
    alvo = PONTOS if variaveis else 1

    def testar(env: dict[str, Any]) -> str | None:
        """'' se comparou e confere; motivo se reprova; None se o ponto não vale."""
        nonlocal pior
        if not _condicoes_ok(av, conds, env):
            return None
        va = avaliar_estavel(av, a, env)
        estouro_a = av.estourou
        vb = avaliar_estavel(av, b, env)
        estouro_b = av.estourou
        if va is None or vb is None:
            if estouro_a or estouro_b:
                return None  # grande demais: o ponto não decide nada
            for v, ob_ in ((va, obr[0]), (vb, obr[1])):
                if v is None and _obrigacoes_valem(av, ob_, env) and not av.estourou:
                    return "verif.identidade.dominio_inconsistente"
            return None
        ok, r = _iguais(va, vb)
        if not ok:
            res.pior_residuo = float(r)
            return "verif.identidade.residuo"
        pior = max(pior, r)
        with mp.workdps(PRECISOES[1]):
            for i, s in enumerate(sensiveis):
                x = av.valor(s, env)
                if x is not None and not isinstance(x, bool) and x != 0:
                    sinais[i].add(1 if x > 0 else -1)
        return ""

    for i in range(TENTATIVAS):
        if len(validos) >= alvo:
            break
        env = amostrador.ponto(i)
        r = testar(env)
        if r:
            res.aprovado, res.motivo = False, r
            return res
        if r == "":
            validos.append(env)
    res.pontos = len(validos)
    if len(validos) < alvo:
        res.aprovado, res.motivo = False, "verif.identidade.amostras_insuficientes"
        return res

    # cobertura de ramos: procurar o sinal que faltou
    for i, s in enumerate(sensiveis):
        rotulo = chave(s)
        if len(sinais[i]) == 2:
            res.ramos.append(rotulo)
            continue
        achou = False
        for var in sorted(livres(s) & set(variaveis)):
            for cand in amostrador.candidatos(var):
                env = {**validos[0], var: cand}
                with mp.workdps(PRECISOES[1]):
                    x = av.valor(s, env)
                if x is None or isinstance(x, bool) or x == 0:
                    continue
                sinal = 1 if x > 0 else -1
                if sinal in sinais[i]:
                    continue
                r = testar(env)
                if r:
                    res.aprovado, res.motivo = False, r
                    return res
                if r == "":
                    achou = True
                    res.pontos += 1
                    break
            if achou:
                break
        (res.ramos if achou else res.ramos_nao_alcancados).append(rotulo)
    res.pior_residuo = float(pior)
    return res

