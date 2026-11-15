# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Partida do aplicativo (seção 2): servidor local, janela própria e processo de cálculo.

* O servidor sobe só em ``127.0.0.1``, numa porta livre, com um token de sessão
  sorteado (``secrets``); a janela abre ``http://127.0.0.1:<porta>/#token=<token>``.
* A janela é o pywebview sobre o WebView2 do Windows (no Linux, GTK ou Qt).
* ``--servidor`` sobe só o servidor, para desenvolvimento e capturas de tela;
  ``--autoteste`` sobe o servidor, faz os pedidos da primeira tela e sai com 0
  se tudo responder: é o que o CI roda no executável.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import secrets
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

#: Cor de fundo da janela antes da interface carregar: --cor-fundo da aparência D, modo claro.
FUNDO_JANELA = "#F6F4EF"


def pasta_interface() -> Path:
    """``interface/dist`` do repositório, ou a cópia dentro do executável."""
    congelado = getattr(sys, "_MEIPASS", None)
    if congelado:
        return Path(congelado) / "interface"
    return Path(__file__).resolve().parents[2] / "interface" / "dist"


def pasta_usuario() -> Path:
    """Onde ficam as preferências: ``AMSIOR_CONFIG``, ``%APPDATA%\\Amsior`` ou ``~/.config/amsior``."""
    if os.environ.get("AMSIOR_CONFIG"):
        return Path(os.environ["AMSIOR_CONFIG"])
    if os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "Amsior"
    return Path.home() / ".config" / "amsior"


def porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Servidor:
    """Uvicorn numa linha de execução própria, com parada limpa."""

    def __init__(self, porta: int, token: str, pasta_config: Path | None) -> None:
        import uvicorn

        from amsior.api.app import Calculista, criar_app

        self.porta = porta
        self.token = token
        self.calculista = Calculista()
        app = criar_app(token, pasta_interface(), self.calculista, pasta_config=pasta_config)
        # log_config=None: no executável sem console não há sys.stderr para o uvicorn.
        config = uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="warning",
                                log_config=None, access_log=False, lifespan="off")
        self._uvicorn = uvicorn.Server(config)
        self._linha = threading.Thread(target=self._uvicorn.run, name="servidor", daemon=True)

    @property
    def endereco(self) -> str:
        return f"http://127.0.0.1:{self.porta}/"

    def subir(self, espera_s: float = 15.0) -> None:
        self.calculista.aquecer()
        self._linha.start()
        limite = time.monotonic() + espera_s
        while not self._uvicorn.started:
            if time.monotonic() > limite or not self._linha.is_alive():
                raise RuntimeError("o servidor local não subiu")
            time.sleep(0.02)

    def parar(self) -> None:
        self._uvicorn.should_exit = True
        self._linha.join(timeout=5)
        self.calculista.fechar()


def _pedir(servidor: Servidor, metodo: str, rota: str, corpo: Any = None) -> Any:
    dados = None if corpo is None else json.dumps(corpo).encode()
    req = urllib.request.Request(servidor.endereco + rota.lstrip("/"), data=dados, method=metodo,
                                 headers={"content-type": "application/json",
                                          "x-amsior-token": servidor.token})
    with urllib.request.urlopen(req, timeout=60) as r:
        bruto = r.read()
    return json.loads(bruto) if rota.startswith("/api/") else bruto.decode("utf-8")


def autoteste(servidor: Servidor) -> dict[str, Any]:
    """Pedidos da primeira tela contra o servidor que acabou de subir."""
    rel: dict[str, Any] = {}
    pagina = _pedir(servidor, "GET", "/")
    assert "<div id=\"raiz\">" in pagina, "interface não encontrada"
    rel["interface"] = "ok"
    rel["textos"] = len(_pedir(servidor, "GET", "/api/v1/textos"))
    rel["grandezas"] = len(_pedir(servidor, "GET", "/api/v1/glossario")["grandezas"])
    simbolos = [{"id": "p", "grandeza": "pressao_absoluta"}, {"id": "V", "grandeza": "volume"},
                {"id": "n", "grandeza": "quantidade_materia"},
                {"id": "R", "grandeza": "constante_gases", "papel": "constante"},
                {"id": "T", "grandeza": "temperatura_absoluta"}]
    a = _pedir(servidor, "POST", "/api/v1/analisar", {"latex": "pV=nRT", "simbolos": simbolos})
    rel["analisar"] = a["latex"]
    r = _pedir(servidor, "POST", "/api/v1/isolar", {"latex": "pV=nRT", "alvo": "V", "simbolos": simbolos})
    assert r["estado"] == "com_passos", r
    assert all(p["selo"]["estado"] == "aprovado" for ramo in r["ramos"] for p in ramo["passos"]), r
    rel["isolar"] = r["ramos"][0]["resultado"]
    return rel


def principal(argv: list[str] | None = None) -> int:
    mp.freeze_support()
    p = argparse.ArgumentParser(prog="amsior")
    p.add_argument("--servidor", action="store_true", help="só o servidor, sem janela")
    p.add_argument("--autoteste", action="store_true", help="sobe, confere a primeira tela e sai")
    p.add_argument("--porta", type=int, default=0)
    p.add_argument("--token", default=None, help="só para desenvolvimento")
    p.add_argument("--relatorio", type=Path, default=None,
                   help="arquivo do relatório do autoteste (o executável não tem console)")
    args = p.parse_args(argv)

    token = args.token or secrets.token_urlsafe(24)
    servidor = Servidor(args.porta or porta_livre(), token,
                        None if args.autoteste else pasta_usuario())
    servidor.subir()
    try:
        if args.autoteste:
            try:
                rel: dict[str, Any] = {"ok": True, **autoteste(servidor)}
            except Exception as e:  # o relatório diz o que falhou; o código de saída também
                rel = {"ok": False, "erro": f"{type(e).__name__}: {e}"}
            texto = json.dumps(rel, ensure_ascii=False, indent=2)
            if args.relatorio is not None:
                args.relatorio.write_text(texto, encoding="utf-8")
            if sys.stdout is not None:
                print(texto)
            return 0 if rel["ok"] else 1
        url = f"{servidor.endereco}#token={token}"
        if args.servidor:
            if sys.stdout is not None:
                print(url, flush=True)
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                return 0
        import webview

        webview.create_window("Amsior", url, width=1440, height=900, min_size=(960, 620),
                              background_color=FUNDO_JANELA, text_select=True)
        webview.start(private_mode=True)
        return 0
    finally:
        servidor.parar()


def main() -> None:
    sys.exit(principal())


if __name__ == "__main__":
    main()
