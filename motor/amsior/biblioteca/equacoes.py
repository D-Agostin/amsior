# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Verificação das fichas de equação por máquina (seções 3.4, 5 e 8.5).

Para uma ficha de equação, confere o que a máquina sabe conferir:

* **V1 e V5, passo a passo:** a demonstração começa numa equação de partida e
  cada passo declara a operação; o verificador do motor refaz a operação e
  exige identidade dos dois lados, com análise dimensional. A cadeia tem de
  terminar na equação da ficha. Passos de princípio e de aproximação ficam
  pendentes de revisão humana (V7).
* **Hipóteses coerentes:** passo que usa uma hipótese só pode citar hipótese
  que a ficha declara.
* **Corpus:** cada variável é isolada pelo motor com passos, ou está na lista
  explícita ``nao_isolaveis``.
* **V6, exemplo numérico:** o valor pedido é calculado com unidades, a partir
  do resultado isolado pelo motor; bate com o ``esperado`` congelado na
  revisão (tolerância declarada) e, quando há fonte independente instalada
  (CoolProp, só nos testes), fica dentro do desvio aceito.

O resultado traz, além dos problemas, os passos certificados e o valor
calculado, que a interface mostra.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from amsior.biblioteca.esquema import Biblioteca, Ficha, Problema
from amsior.erros import ErroAmsior
from amsior.expr.analisador import analisar
from amsior.expr.latex import para_latex
from amsior.expr.nos import Eq, Expr, Sym
from amsior.expr.simbolos import Simbolo, TabelaDeSimbolos
from amsior.verify.certificador import Verificador
from amsior.verify.identidade import Comparador
from amsior.units.conversao import para_si
from amsior.verify.modelo import Certificado, Condicao, Operacao, Passo

TIPOS_DE_PASSO = ("algebra", "calculo", "substituicao", "principio", "aproximacao")
_NUMERO = re.compile(r"^\s*([-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?)\s*(.*)$")


@dataclass
class PassoVerificado:
    indice: int
    titulo: dict[str, str] | None
    texto: dict[str, str] | None
    tipo: str
    usa: str | None
    depois: str
    condicoes: list[str]
    relacao: str
    certificado: dict[str, Any]


@dataclass
class ResultadoFicha:
    id: str
    problemas: list[Problema] = field(default_factory=list)
    inicio: str | None = None
    passos: list[PassoVerificado] = field(default_factory=list)
    corpus: dict[str, str] = field(default_factory=dict)  # símbolo → com_passos | nao_isolavel
    exemplo: dict[str, Any] | None = None

    def erro(self, f: Ficha, campo: str, msg: str) -> None:
        self.problemas.append(Problema(f.arquivo, campo, msg))


# ------------------------------------------------------------------ símbolos


def tabela_da_ficha(b: Biblioteca, f: Ficha) -> TabelaDeSimbolos:
    """Variáveis da ficha e símbolos auxiliares da demonstração, com as grandezas do glossário."""
    assert b.glossario is not None
    g = b.glossario
    simbolos: list[Simbolo] = []
    vistos: set[str] = set()

    def incluir(spec: dict[str, Any]) -> None:
        sid = _canonico(str(spec["simbolo"]))
        if sid in vistos:
            return
        vistos.add(sid)
        papel = "constante" if spec.get("constante") else "variavel"
        dep: tuple[str, ...] = ()
        if spec.get("funcao_de"):
            papel, dep = "funcao", (_canonico(str(spec["funcao_de"])),)
        simbolos.append(g.simbolo(sid, str(spec["grandeza"]), papel=papel, depende_de=dep))  # type: ignore[arg-type]

    for v in f.dados.get("variaveis") or ():
        incluir(v)
    for v in (f.dados.get("demonstracao") or {}).get("simbolos") or ():
        incluir(v)
    return TabelaDeSimbolos.de(simbolos)


def _canonico(latex: str) -> str:
    e = analisar(latex)
    return e.id if isinstance(e, Sym) else latex


# ------------------------------------------------------------------ verificação


def verificar_ficha_equacao(b: Biblioteca, f: Ficha, *, corpus: bool = True,
                            referencia: bool = False) -> ResultadoFicha:
    r = ResultadoFicha(f.id)
    d = f.dados
    if not isinstance(d.get("equacao"), str):
        return r
    tab = tabela_da_ficha(b, f)
    try:
        equacao = analisar(d["equacao"], tab)
    except ErroAmsior as e:
        r.erro(f, "equacao", f"não se lê: {e}")
        return r
    assert b.glossario is not None
    ver = Verificador(tab, b.glossario)
    _demonstracao(b, f, r, tab, ver, equacao)
    if corpus:
        _corpus(f, r, tab)
    if d.get("exemplo"):
        _exemplo(b, f, r, tab, referencia)
    return r


def _operacao(spec: dict[str, Any], tab: TabelaDeSimbolos) -> Operacao:
    def expr(k: str) -> Expr | None:
        v = spec.get(k)
        return None if v is None else analisar(str(v), tab)
    simb = expr("simbolo")
    if simb is not None and not isinstance(simb, Sym):
        raise ValueError("simbolo da operação tem de ser um símbolo só")
    limites = spec.get("limites")
    return Operacao(
        str(spec["nome"]), expr("argumento"), spec.get("lado"), simb, spec.get("origem"),
        bool(spec.get("identidade", False)),
        None if limites is None else (analisar(str(limites[0]), tab), analisar(str(limites[1]), tab)),
    )


def _demonstracao(b: Biblioteca, f: Ficha, r: ResultadoFicha, tab: TabelaDeSimbolos,
                  ver: Verificador, equacao: Expr) -> None:
    dem = f.dados.get("demonstracao")
    if not dem:
        return
    hip_ficha = set(f.dados.get("hipoteses") or ())
    inicio = dem.get("inicio") or {}
    try:
        antes = analisar(str(inicio.get("equacao")), tab)
    except (ErroAmsior, ValueError) as e:
        r.erro(f, "demonstracao.inicio.equacao", f"não se lê: {e}")
        return
    r.inicio = para_latex(antes)
    for i, p in enumerate(dem.get("passos") or ()):
        campo = f"demonstracao.passos[{i}]"
        usa = p.get("usa")
        if isinstance(usa, str) and usa.startswith("hipotese."):
            h = usa.removeprefix("hipotese.")
            if h not in b.hipoteses:
                r.erro(f, f"{campo}.usa", f"hipótese fora do vocabulário: {h}")
            elif h not in hip_ficha:
                r.erro(f, f"{campo}.usa", f"a ficha usa {h} sem declará-la em hipoteses")
        elif isinstance(usa, str) and usa not in ("definicao",) and usa not in b.fichas:
            r.erro(f, f"{campo}.usa", f"ficha inexistente: {usa}")
        try:
            depois = analisar(str(p["depois"]), tab)
            op = _operacao(p.get("operacao") or {"nome": "reescrever"}, tab)
            conds = tuple(Condicao(analisar(str(c), tab)) for c in p.get("condicoes") or ())
        except (ErroAmsior, ValueError, KeyError) as e:
            r.erro(f, campo, f"não se lê: {e}")
            return
        passo = Passo(antes, depois, op, relacao=p.get("relacao", "equivalente"),
                      tipo=p.get("tipo", "algebra"), indice=i + 1, regra=op.nome, condicoes=conds)
        cert: Certificado = ver.certificar(passo, "ficha")
        if cert.estado == "reprovado":
            motivos = "; ".join(m.texto() for m in cert.motivos[:3])
            r.erro(f, campo, f"passo reprovado: {motivos}")
        elif (cert.estado != "aprovado" and f.dados.get("estado") == "verificada"
              and not (f.dados.get("revisao") or {}).get("humana")):
            # princípio e aproximação ficam pendentes até a revisão humana (seção 8.5)
            r.erro(f, campo, "passo sem certificado da máquina numa ficha verificada "
                   "sem revisão humana registrada")
        r.passos.append(PassoVerificado(
            i + 1, p.get("titulo"), p.get("texto"), passo.tipo, usa, para_latex(depois),
            [para_latex(c.expr) for c in conds], passo.relacao, cert.para_json()))
        antes = depois
    # a cadeia termina na equação da ficha
    if isinstance(antes, Eq) and isinstance(equacao, Eq):
        comp = Comparador(tab, 1)
        iguais = (comp.comparar(antes.esq, equacao.esq).aprovado
                  and comp.comparar(antes.dir, equacao.dir).aprovado)
        if not iguais:
            r.erro(f, "demonstracao", "a demonstração não termina na equação da ficha: "
                   f"{para_latex(antes)}")


def _corpus(f: Ficha, r: ResultadoFicha, tab: TabelaDeSimbolos) -> None:
    from amsior.api.servico import executar

    latex = f.dados["equacao"]
    nao = {_canonico(str(s)) for s in f.dados.get("nao_isolaveis") or ()}
    simbolos = _simbolos_para_api(latex, tab)
    funcoes = {x.id for x in tab if x.papel == "funcao"}
    from amsior.verify.arvore import livres
    soltos = livres(analisar(latex, tab))
    for s in simbolos:
        if s["papel"] == "constante" or s["id"] in funcoes or s["id"] not in soltos:
            continue
        res = executar("isolar", {"latex": latex, "alvo": s["id"], "simbolos": simbolos})
        estado = res.get("ok", {}).get("estado") if "ok" in res else None
        if estado == "com_passos":
            r.corpus[s["id"]] = "com_passos"
            if s["id"] in nao:
                r.erro(f, "nao_isolaveis", f"{s['id']} agora é isolado com passos: tire da lista")
        elif s["id"] in nao:
            r.corpus[s["id"]] = "nao_isolavel"
        else:
            motivo = (res.get("ok", {}).get("motivo") or {}).get("texto") if "ok" in res \
                else res.get("erro", {}).get("mensagem")
            r.erro(f, "corpus", f"{s['id']} não foi isolado com passos ({estado}: {motivo}); "
                   "corrija o motor ou declare em nao_isolaveis")


def _simbolos_para_api(latex: str, tab: TabelaDeSimbolos) -> list[dict[str, str]]:
    """Símbolos da equação para o motor; função (C_p(T)) vai como variável: isolar n ou Q
    numa equação com integral não depende de declarar a dependência."""
    return [{"id": s.id, "grandeza": s.grandeza or "",
             "papel": "variavel" if s.papel == "funcao" else s.papel}
            for s in tab if s.id in _livres_da(latex, tab)]


def _livres_da(latex: str, tab: TabelaDeSimbolos) -> set[str]:
    """Símbolos livres e variáveis de integração (o T de ∫ C_p dT também precisa de
    grandeza para a verificação dimensional dos passos)."""
    from amsior.verify.arvore import livres, variaveis_ligadas
    e = analisar(latex, tab)
    return livres(e) | variaveis_ligadas(e)


def ler_valor(texto: str) -> tuple[float, str]:
    """``"373,15 K"`` → (373.15, "K"); vírgula decimal aceita."""
    m = _NUMERO.match(str(texto))
    if not m:
        raise ValueError(f"valor sem número: {texto!r}")
    return float(m.group(1).replace(",", ".")), m.group(2).strip()


def _exemplo(b: Biblioteca, f: Ficha, r: ResultadoFicha, tab: TabelaDeSimbolos,
             referencia: bool) -> None:
    import sympy as sp

    from amsior.api.servico import executar
    from amsior.expr.ponte_sympy import ParaSympy
    from amsior.units.conversao import de_si

    assert b.glossario is not None
    ex = f.dados["exemplo"]
    pede = _canonico(str(ex.get("pede")))
    alvo = tab.obter(pede)
    if alvo is None or alvo.grandeza is None:
        r.erro(f, "exemplo.pede", f"{pede} não é variável da ficha")
        return
    simbolos = _simbolos_para_api(f.dados["equacao"], tab)
    res = executar("isolar", {"latex": f.dados["equacao"], "alvo": pede, "simbolos": simbolos})
    ok = res.get("ok")
    if not ok or ok["estado"] != "com_passos" or len(ok["ramos"]) != 1:
        r.erro(f, "exemplo", f"o motor não isola {pede} num ramo só, com passos")
        return
    resultado = analisar(ok["ramos"][0]["resultado"], tab)
    assert isinstance(resultado, Eq)
    conv = ParaSympy(tab)
    valores: dict[Any, float] = {}
    dados_si: dict[str, float] = {}
    for k, v in (ex.get("dados") or {}).items():
        sid = _canonico(str(k))
        s = tab.obter(sid)
        if s is None or s.grandeza is None:
            r.erro(f, f"exemplo.dados.{k}", "símbolo fora da ficha")
            return
        try:
            num, uni = ler_valor(str(v))
            si = para_si(num, uni or b.glossario[s.grandeza].unidade_si, b.glossario[s.grandeza])
        except Exception as e:  # noqa: BLE001
            r.erro(f, f"exemplo.dados.{k}", f"valor ou unidade inválidos: {e}")
            return
        dados_si[sid] = si
        valores[conv.simbolo(sid)] = si
    # constantes da ficha com valor definido (R) entram pelo glossário de constantes
    for s in tab:
        if s.papel == "constante" and s.id not in dados_si and s.id in _CONSTANTES:
            valores[conv.simbolo(s.id)] = _CONSTANTES[s.id]
            dados_si[s.id] = _CONSTANTES[s.id]
    expr = conv(resultado.dir)
    # funções da ficha (C_p(T)) recebem a expressão do exemplo, com coeficientes no SI
    for nome, corpo in (ex.get("funcoes") or {}).items():
        sid = _canonico(str(nome))
        simb = tab.obter(sid)
        if simb is None or not simb.depende_de:
            r.erro(f, f"exemplo.funcoes.{nome}", "não é função declarada na ficha")
            return
        var = conv.simbolo(simb.depende_de[0])
        corpo_sp = conv(analisar(str(corpo), tab))
        fun = sp.Function(sid)
        expr = expr.replace(lambda x, fun=fun: isinstance(x, sp.core.function.AppliedUndef)
                            and x.func.__name__ == fun.__name__,
                            lambda x, corpo_sp=corpo_sp, var=var: corpo_sp.subs(var, x.args[0]))
    faltam = {str(x) for x in expr.free_symbols} - {str(x) for x in valores}
    if faltam:
        r.erro(f, "exemplo.dados", f"faltam dados para: {', '.join(sorted(faltam))}")
        return
    valor_si = float(sp.N(expr.subs(valores).doit(), 30))
    g = b.glossario[alvo.grandeza]
    r.exemplo = {"pede": pede, "valor_si": valor_si, "unidade_si": g.unidade_si,
                 "dados_si": dados_si, "resultado": ok["ramos"][0]["resultado"]}
    esperado = ex.get("esperado")
    if esperado is not None:
        num, uni = ler_valor(str(esperado))
        esp_si = para_si(num, uni or g.unidade_si, g)
        tol = float(ex.get("tolerancia_rel", 1e-6))
        if abs(valor_si - esp_si) > tol * abs(esp_si):
            r.erro(f, "exemplo.esperado", f"calculado {valor_si:.6g} {g.unidade_si}, "
                   f"esperado {esp_si:.6g} (tolerância {tol:g})")
        r.exemplo["esperado_si"] = esp_si
    comp = ex.get("comparacao_independente")
    if comp and referencia:
        ref = _referencia(comp, dados_si, g)
        if ref is None:
            r.erro(f, "exemplo.comparacao_independente", "fonte independente indisponível")
        else:
            desvio = abs(valor_si - ref) / abs(ref)
            r.exemplo["referencia_si"] = ref
            r.exemplo["desvio_rel"] = desvio
            aceito = float(comp.get("desvio_aceito_rel", 0.05))
            if desvio > aceito:
                r.erro(f, "exemplo.comparacao_independente",
                       f"desvio de {desvio:.2%} da fonte independente; aceito até {aceito:.2%}")
    # mostra o valor também na unidade em que o pedido foi escrito, se houver
    uni_saida = str(ex.get("unidade") or g.unidade_si)
    r.exemplo["unidade"] = uni_saida
    r.exemplo["valor"] = de_si(valor_si, uni_saida, g)
    if "referencia_si" in r.exemplo:
        r.exemplo["referencia"] = de_si(r.exemplo["referencia_si"], uni_saida, g)


def _valor_de_entrada(v: str, dados_si: dict[str, float]) -> float:
    """Entrada da fonte independente: número, símbolo do exemplo ou expressão deles (n/V)."""
    import sympy as sp

    from amsior.expr.ponte_sympy import ParaSympy
    try:
        return ler_valor(v)[0]
    except ValueError:
        pass
    tab = TabelaDeSimbolos.de([Simbolo(k) for k in dados_si])
    e = ParaSympy(tab)(analisar(v, tab))
    return float(sp.N(e.subs({x: dados_si[str(x)] for x in e.free_symbols})))


#: valores exatos das constantes que as fichas usam (SI 2019)
_CONSTANTES = {"R": 8.314462618}


def _referencia(comp: dict[str, Any], dados_si: dict[str, float],
                g: Any = None) -> float | None:
    """Valor da fonte independente: tabela publicada (``valor``) ou CoolProp."""
    if comp.get("valor") is not None:
        num, uni = ler_valor(str(comp["valor"]))
        return para_si(num, uni, g) if uni and g is not None else num
    if comp.get("fonte") != "coolprop":
        return None
    try:
        import CoolProp.CoolProp as CP  # noqa: N813 - nome da biblioteca
    except ImportError:
        return None
    entradas: list[Any] = []
    for nome, v in comp["entradas"].items():
        if isinstance(v, str):
            entradas += [nome, _valor_de_entrada(v, dados_si)]
        else:
            entradas += [nome, float(v)]
    if len(entradas) != 4:
        return None
    n1, v1, n2, v2 = entradas
    return float(CP.PropsSI(str(comp["propriedade"]), str(n1), float(v1), str(n2), float(v2),
                            str(comp["fluido"])))
