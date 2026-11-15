# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Protótipo de empacotamento da fase 1A ("olá, mundo").

Chama cada biblioteca que o instalador final vai carregar e imprime um
relatório em JSON. Sai com código 0 só se todas responderem. O objetivo é
descobrir cedo se o PyInstaller consegue embalar tudo no Windows (risco da
seção 10.2 da especificação), antes de existir interface.
"""

from __future__ import annotations

import importlib.metadata as md
import json
import platform
import sys
import traceback
from collections.abc import Callable
from typing import Any


def _versao(pacote: str) -> str:
    try:
        return md.version(pacote)
    except md.PackageNotFoundError:
        return "?"


def checar_sympy() -> str:
    import sympy as sp

    x = sp.Symbol("x", positive=True)
    raiz = sp.solve(sp.Eq(x**2, 4), x)
    assert raiz == [2], raiz
    return f"sympy {sp.__version__}: x² = 4 → {raiz}"


def checar_mpmath() -> str:
    import mpmath

    with mpmath.workdps(50):
        r = mpmath.sqrt(2) ** 2 - 2
    assert abs(r) < mpmath.mpf("1e-45")
    return f"mpmath {mpmath.__version__}: resíduo de √2² − 2 = {mpmath.nstr(r, 3)}"


def checar_pint() -> str:
    import pint

    ureg = pint.UnitRegistry()
    t = ureg.Quantity(25, "degC").to("K").magnitude
    assert abs(t - 298.15) < 1e-9
    return f"pint {pint.__version__}: 25 °C = {t} K"


def checar_coolprop() -> str:
    from CoolProp.CoolProp import PropsSI

    p95 = PropsSI("P", "T", 373.124, "Q", 0, "Water")
    p97 = PropsSI("P", "T", 373.124, "Q", 0, "IF97::Water")
    assert abs(p95 - 101325) < 20 and abs(p97 - 101325) < 20, (p95, p97)
    return f"CoolProp {_versao('CoolProp')}: Psat(373,124 K) IAPWS-95 = {p95:.1f} Pa, IF97 = {p97:.1f} Pa"


def checar_chemicals() -> str:
    from chemicals import Tc

    tc = Tc("7732-18-5")
    assert tc is not None and abs(tc - 647.096) < 0.01, tc
    return f"chemicals {_versao('chemicals')}: Tc da água = {tc} K"


def checar_fastapi() -> str:
    """Chama o aplicativo ASGI diretamente, sem cliente HTTP de testes."""
    import asyncio

    import fastapi

    app = fastapi.FastAPI()

    @app.get("/saude")
    def saude() -> dict[str, str]:
        return {"estado": "ok"}

    enviados: list[dict[str, Any]] = []

    async def receber() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def enviar(msg: dict[str, Any]) -> None:
        enviados.append(msg)

    escopo = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "GET", "scheme": "http", "path": "/saude", "raw_path": b"/saude",
        "query_string": b"", "root_path": "", "headers": [],
        "server": ("127.0.0.1", 8000), "client": ("127.0.0.1", 50000),
    }
    asyncio.run(app(escopo, receber, enviar))
    status = next(m["status"] for m in enviados if m["type"] == "http.response.start")
    corpo = b"".join(m.get("body", b"") for m in enviados if m["type"] == "http.response.body")
    assert status == 200 and json.loads(corpo) == {"estado": "ok"}, (status, corpo)
    return f"fastapi {fastapi.__version__}: rota local respondeu 200"


def checar_uvicorn() -> str:
    import uvicorn

    return f"uvicorn {uvicorn.__version__}: importado"


def checar_pywebview() -> str:
    import webview  # noqa: F401  (a janela só abre na fase 1B; aqui basta importar)

    return f"pywebview {_versao('pywebview')}: importado"


def checar_motor() -> str:
    from amsior.expr import analisar, para_latex
    from amsior.units import carregar_glossario
    from amsior.verify import Operacao, Passo, certificar
    from amsior.expr import TabelaDeSimbolos

    g = carregar_glossario()
    tab = TabelaDeSimbolos.de([g.simbolo(s, gr) for s, gr in (
        ("P", "pressao_absoluta"), ("V", "volume"), ("n", "quantidade_materia"),
        ("R", "constante_gases"), ("T", "temperatura_absoluta"))])
    passo = Passo(analisar("PV = nRT", tab), analisar(r"P = \frac{nRT}{V}", tab),
                  Operacao("dividir_ambos", analisar("V", tab)))
    cert = certificar(passo, tab, g)
    assert cert.estado == "aprovado", cert
    return f"amsior: {para_latex(passo.depois)} certificado ({cert.metodo})"


CHECAGENS: list[tuple[str, Callable[[], str]]] = [
    ("sympy", checar_sympy), ("mpmath", checar_mpmath), ("pint", checar_pint),
    ("CoolProp", checar_coolprop), ("chemicals", checar_chemicals),
    ("fastapi", checar_fastapi), ("uvicorn", checar_uvicorn),
    ("pywebview", checar_pywebview), ("motor", checar_motor),
]


def main() -> int:
    # no Windows, a saída redirecionada usaria cp1252 e quebraria em "²" e "√"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    relatorio: dict[str, Any] = {
        "python": sys.version.split()[0], "sistema": platform.platform(),
        "congelado": bool(getattr(sys, "frozen", False)), "resultados": {},
    }
    ok = True
    for nome, checar in CHECAGENS:
        try:
            relatorio["resultados"][nome] = {"ok": True, "detalhe": checar()}
        except Exception as exc:  # o relatório precisa mostrar toda falha
            ok = False
            relatorio["resultados"][nome] = {
                "ok": False, "erro": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=3),
            }
    print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
