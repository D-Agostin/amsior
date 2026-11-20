# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Teste do site num Chrome de verdade (fase 1C).

Com o site servido em URL (por exemplo ``npx vite preview``):

1. abre a página, espera o motor e isola um exemplo; todos os passos têm de
   vir certificados, sem erro no console e sem nenhum pedido para fora do site
   (T-07);
2. espera o service worker guardar o site;
3. desliga a rede, recarrega e isola outro exemplo: o Amsior tem de abrir e
   calcular sem internet.

  python ferramentas/web/teste_navegador.py http://localhost:4173/ [relatorio.json]

O Chrome usado é o instalado (``channel="chrome"``) ou o de CHROME_CAMINHO. Com
NAVEGADOR=firefox, roda no Firefox do Playwright (``playwright install firefox``).
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from playwright.sync_api import Page, sync_playwright


def isolar_exemplo(pg: Page, nome: str) -> dict[str, Any]:
    t0 = time.monotonic()
    pg.get_by_role("button", name=nome, exact=True).click()
    pg.wait_for_selector(".resultado", timeout=120_000)
    passos = pg.locator(".passo:not(.passo-cabeca):not(.passo-dada)").count()
    selos = pg.locator(".passo .selo-ok").count()
    return {"exemplo": nome, "passos": passos, "certificados": selos, "s": round(time.monotonic() - t0, 2)}


def biblioteca(pg: Page) -> dict[str, Any]:
    """Abre a ficha-modelo de Matemática, leva um exemplo à folha e volta pela etiqueta do tipo."""
    pg.get_by_role("button", name="Biblioteca", exact=True).click()
    pg.locator(".arvore-item", has_text="Equação racional").click()
    pg.wait_for_selector(".ficha-papel", timeout=30_000)
    # a ficha é mais alta que a tela: a área central tem de rolar até as referências
    rola = pg.locator("article.ficha").evaluate(
        "e => { const antes = e.scrollHeight > e.clientHeight + 200; e.scrollTo(0, e.scrollHeight);"
        " const ref = e.querySelector('.ficha-referencias').getBoundingClientRect();"
        " const caixa = e.getBoundingClientRect(); e.scrollTo(0, 0);"
        " return antes && ref.top < caixa.bottom; }")
    r: dict[str, Any] = {
        "rola_ate_o_fim": rola,
        "equacoes": pg.locator(".ficha-eq-num").count(),
        "passos_da_deducao": pg.locator(".ficha-passo").count(),
        "caixas": pg.locator(".ficha-caixa").count(),
    }
    pg.get_by_role("button", name="Abrir na folha").nth(1).click()  # o exemplo que vira do 2º grau
    pg.wait_for_selector(".resultado", timeout=120_000)
    r["exemplo_passos"] = pg.locator(".passo:not(.passo-cabeca):not(.passo-dada)").count()
    r["exemplo_certificados"] = pg.locator(".passo .selo-ok").count()
    pg.get_by_role("button", name="Ver a ficha").click()
    r["volta_pela_etiqueta"] = pg.locator("#ficha-titulo").inner_text() == "Equação racional"
    return r


def ficha_de_equacao(pg: Page) -> dict[str, Any]:
    """Ficha de Clausius-Clapeyron: um selo por passo da demonstração, o exemplo calculado
    e "Usar na folha" isolando T₂ com passos verificados."""
    item = pg.locator(".arvore-item", has_text="Clausius-Clapeyron (forma integrada)")
    if item.count() == 0:
        pg.get_by_role("button", name="Biblioteca", exact=True).click()
    item.click()
    pg.wait_for_selector(".ficha-demonstracao", timeout=30_000)
    r: dict[str, Any] = {
        "passos": pg.locator(".ficha-demonstracao .ficha-passo").count(),
        "passos_verificados": pg.locator(".ficha-demonstracao .ficha-passo .selo-ok").count(),
        "exemplo_com_valor": "197,5" in pg.locator(".ficha-exemplo-equacao").inner_text(),
        "botoes_usar": pg.locator(".ficha-usar-botoes button").count(),
    }
    pg.get_by_role("button", name="Isolar T_{2} na folha").click()
    pg.wait_for_selector(".resultado", timeout=120_000)
    r["isolar_passos"] = pg.locator(".passo:not(.passo-cabeca):not(.passo-dada)").count()
    r["isolar_certificados"] = pg.locator(".passo .selo-ok").count()
    return r


def main(url: str) -> dict[str, Any]:
    rel: dict[str, Any] = {"url": url, "erros": [], "pedidos_para_fora": []}
    origem = url.split("#")[0].rstrip("/")
    with sync_playwright() as p:
        if os.environ.get("NAVEGADOR") == "firefox":
            nav = p.firefox.launch()
        else:
            caminho = os.environ.get("CHROME_CAMINHO")
            nav = p.chromium.launch(**({"executable_path": caminho} if caminho else {"channel": "chrome"}),
                                    args=["--disable-background-networking", "--disable-component-update"])
        rel["navegador"] = f"{nav.browser_type.name} {nav.version}"
        ctx = nav.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.on("console", lambda m: rel["erros"].append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: rel["erros"].append(str(e)))
        ctx.on("request", lambda r: rel["pedidos_para_fora"].append(r.url)
               if not r.url.startswith(origem) and not r.url.startswith(("data:", "blob:")) else None)

        t0 = time.monotonic()
        pg.goto(url)
        pg.wait_for_selector(".arvore-item", timeout=30_000)
        rel["tela_s"] = round(time.monotonic() - t0, 2)
        pg.wait_for_selector(".estado-pronto", timeout=180_000)
        rel["motor_s"] = round(time.monotonic() - t0, 2)
        rel["com_internet"] = isolar_exemplo(pg, "Clausius-Clapeyron")

        # o service worker se registra quando o motor fica pronto e guarda o site
        pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.ready.then(r => !!r.active)",
                             timeout=120_000)
        pg.wait_for_function("""async () => {
            for (const n of await caches.keys()) {
              const c = await caches.open(n);
              if ((await c.keys()).some(r => r.url.includes('/motor/motor-'))) return true;
            }
            return false; }""", timeout=180_000)
        rel["cache_s"] = round(time.monotonic() - t0, 2)

        ctx.set_offline(True)
        pg.reload()
        pg.wait_for_selector(".arvore-item", timeout=30_000)
        pg.wait_for_selector(".estado-pronto", timeout=180_000)
        rel["controlada_pelo_sw"] = pg.evaluate("!!navigator.serviceWorker.controller")
        rel["sem_internet"] = isolar_exemplo(pg, "Arrhenius")
        rel["biblioteca"] = biblioteca(pg)
        rel["ficha_de_equacao"] = ficha_de_equacao(pg)
        nav.close()

    ok = (not rel["erros"] and not rel["pedidos_para_fora"] and rel["controlada_pelo_sw"]
          and all(r["passos"] > 0 and r["passos"] == r["certificados"]
                  for r in (rel["com_internet"], rel["sem_internet"]))
          and rel["biblioteca"]["equacoes"] >= 10 and rel["biblioteca"]["caixas"] >= 3
          and 0 < rel["biblioteca"]["exemplo_passos"] == rel["biblioteca"]["exemplo_certificados"]
          and rel["biblioteca"]["volta_pela_etiqueta"] and rel["biblioteca"]["rola_ate_o_fim"]
          and 0 < rel["ficha_de_equacao"]["passos"] == rel["ficha_de_equacao"]["passos_verificados"]
          and rel["ficha_de_equacao"]["exemplo_com_valor"] and rel["ficha_de_equacao"]["botoes_usar"] == 5
          and 0 < rel["ficha_de_equacao"]["isolar_passos"] == rel["ficha_de_equacao"]["isolar_certificados"])
    rel["ok"] = ok
    return rel


if __name__ == "__main__":
    relatorio = main(sys.argv[1])
    texto = json.dumps(relatorio, ensure_ascii=False, indent=2)
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(texto)
    print(texto)
    sys.exit(0 if relatorio["ok"] else 1)
