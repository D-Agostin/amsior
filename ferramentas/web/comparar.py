# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Compara o motor no navegador (Pyodide) com o Python nativo (fase 1C).

O mesmo pedido tem de dar exatamente a mesma resposta nos dois: passos, LaTeX,
justificativas e certificados. Diferença é falha (especificação, seção 10.1).

  python ferramentas/web/comparar.py pedidos  pedidos.json
  node interface/ferramentas/motor-node.mjs pedidos.json > pyodide.json   (em interface/)
  python ferramentas/web/comparar.py comparar pedidos.json pyodide.json [relatorio.json]

Os pedidos são os exemplos da interface, todas as variáveis do corpus de isolar e, da
biblioteca montada (dados.json), os exemplos das fichas e cada "Usar na folha" das fichas
de equação.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "motor"))


def gerar_pedidos() -> list[dict[str, Any]]:
    from tests.corpus.corpus_isolar import CORPUS

    pedidos: list[dict[str, Any]] = [{"rota": "textos", "dados": {}}, {"rota": "glossario", "dados": {}}]
    exemplos = json.loads((RAIZ / "interface" / "src" / "dados" / "exemplos.json").read_text(encoding="utf-8"))
    for e in exemplos:
        pedidos.append({"origem": f"exemplo {e['id']}", "rota": "analisar",
                        "dados": {"latex": e["latex"], "simbolos": e["simbolos"]}})
        pedidos.append({"origem": f"exemplo {e['id']} → {e['alvo']}", "rota": "isolar",
                        "dados": {"latex": e["latex"], "alvo": e["alvo"], "simbolos": e["simbolos"]}})
    for eq in CORPUS:
        simbolos = []
        for sid, spec in eq.simbolos.items():
            grandeza, _, papel = spec.partition(":")
            simbolos.append({"id": sid, "grandeza": grandeza, "papel": papel or "variavel"})
        for s in simbolos:
            if s["papel"] != "constante":
                pedidos.append({"origem": f"corpus {eq.nome} → {s['id']}", "rota": "isolar",
                                "dados": {"latex": eq.latex, "alvo": s["id"], "simbolos": simbolos}})
    dados = RAIZ / "interface" / "public" / "motor" / "dados.json"
    if dados.exists():
        fichas = json.loads(dados.read_text(encoding="utf-8"))["biblioteca"]["fichas"]
        for fid, f in sorted(fichas.items()):
            for i, ex in enumerate(f.get("exemplos") or (), 1):
                pedidos.append({"origem": f"ficha {fid} exemplo {i}", "rota": "isolar",
                                "dados": {"latex": ex["equacao"], "alvo": ex["pede"], "simbolos": ex["simbolos"]}})
            eq = f.get("equacao")
            for alvo in (eq or {}).get("isolaveis") or ():
                pedidos.append({"origem": f"ficha {fid} → {alvo}", "rota": "isolar",
                                "dados": {"latex": eq["latex"], "alvo": alvo, "simbolos": eq["simbolos"]}})
    return pedidos


def _diferenca(a: Any, b: Any, caminho: str = "") -> str | None:
    if type(a) is not type(b):
        return f"{caminho}: tipo {type(a).__name__} × {type(b).__name__}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return f"{caminho}.{k}: só em um dos lados"
            d = _diferenca(a[k], b[k], f"{caminho}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{caminho}: {len(a)} × {len(b)} itens"
        for i, (x, y) in enumerate(zip(a, b)):
            d = _diferenca(x, y, f"{caminho}[{i}]")
            if d:
                return d
        return None
    return None if a == b else f"{caminho}: {a!r} × {b!r}"


def comparar(pedidos: list[dict[str, Any]], navegador: dict[str, Any]) -> dict[str, Any]:
    from amsior.api.servico import executar

    executar("glossario", {})
    diferencas, nativo_ms, pyodide_ms = [], [], []
    for p, r in zip(pedidos, navegador["respostas"], strict=True):
        t = time.perf_counter()
        esperado = executar(p["rota"], p["dados"])
        ms = (time.perf_counter() - t) * 1000
        if p["rota"] == "isolar":
            nativo_ms.append(ms)
            pyodide_ms.append(r["ms"])
        d = _diferenca(esperado, r["resposta"])
        if d:
            diferencas.append({"pedido": p.get("origem", p["rota"]), "onde": d})
    razao = [b / a for a, b in zip(nativo_ms, pyodide_ms) if a > 5]

    def resumo(xs: list[float]) -> dict[str, float]:
        xs = sorted(xs)
        return {"mediana_ms": round(statistics.median(xs)), "p95_ms": round(xs[int(0.95 * (len(xs) - 1))]),
                "max_ms": round(xs[-1])}

    return {
        "pedidos": len(pedidos), "isolar": len(nativo_ms), "diferencas": diferencas,
        "python_navegador": navegador.get("python", "")[:6], "partida_navegador_ms": round(navegador["partida_ms"]),
        "nativo": resumo(nativo_ms), "navegador": resumo(pyodide_ms),
        "navegador_sobre_nativo_mediana": round(statistics.median(razao), 2) if razao else None,
    }


if __name__ == "__main__":
    if sys.argv[1] == "pedidos":
        Path(sys.argv[2]).write_text(json.dumps(gerar_pedidos(), ensure_ascii=False), encoding="utf-8")
    else:
        pedidos = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        nav = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        rel = comparar(pedidos, nav)
        texto = json.dumps(rel, ensure_ascii=False, indent=2)
        if len(sys.argv) > 4:
            Path(sys.argv[4]).write_text(texto, encoding="utf-8")
        print(texto)
        sys.exit(1 if rel["diferencas"] else 0)
