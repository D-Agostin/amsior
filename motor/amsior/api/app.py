# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Servidor local (seção 2): FastAPI só em loopback, com token de sessão.

* Toda rota ``/api/v1`` exige o cabeçalho ``X-Amsior-Token`` com o token
  sorteado na partida; outro programa da máquina não consegue usar a API.
* Os cálculos rodam num processo separado, com tempo limite (T-06): se o
  SymPy travar, o processo é encerrado e recriado, e a interface recebe o erro
  ``tempo_esgotado`` sem congelar.
* A interface compilada (``interface/dist``) é servida em ``/``.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import multiprocessing as mp
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from amsior.api.servico import ErroDePedido, executar, rota_textos

TEMPO_LIMITE_S = 10.0  # seção 2 da especificação: padrão de 10 s por tarefa


class Calculista:
    """Um processo de cálculo, recriado se estourar o tempo."""

    def __init__(self, tempo_limite: float = TEMPO_LIMITE_S, processo_separado: bool = True) -> None:
        self.tempo_limite = tempo_limite
        self.processo_separado = processo_separado
        self._trava = threading.Lock()
        self._exec: cf.ProcessPoolExecutor | None = None

    def _executor(self) -> cf.ProcessPoolExecutor:
        if self._exec is None:
            self._exec = cf.ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context("spawn"))
        return self._exec

    def aquecer(self) -> None:
        """Carrega SymPy e o glossário no processo antes do primeiro pedido."""
        if self.processo_separado:
            self._executor().submit(executar, "glossario", {})

    def __call__(self, rota: str, dados: dict[str, Any]) -> dict[str, Any]:
        if not self.processo_separado:
            return executar(rota, dados)
        with self._trava:
            fut = self._executor().submit(executar, rota, dados)
            try:
                return fut.result(timeout=self.tempo_limite)
            except cf.TimeoutError:
                self._encerrar()
                return {"erro": ErroDePedido("tempo_esgotado", "api.tempo_esgotado",
                                             self.tempo_limite,
                                             segundos=f"{self.tempo_limite:g}").para_json()}
            except cf.process.BrokenProcessPool:
                self._encerrar()
                return {"erro": ErroDePedido("interno", "api.erro_interno",
                                             "processo de cálculo caiu").para_json()}

    def _encerrar(self) -> None:
        ex, self._exec = self._exec, None
        if ex is None:
            return
        for p in list(getattr(ex, "_processes", {}).values()):
            p.terminate()
        ex.shutdown(wait=False, cancel_futures=True)

    def fechar(self) -> None:
        self._encerrar()


#: Preferências aceitas (especificação 9.4) e o valor padrão de cada uma.
PREFERENCIAS: dict[str, tuple[str, ...]] = {
    "aparencia": ("d", "h"), "modo": ("sistema", "claro", "escuro"), "nivel": ("completo", "resumido")}


class Preferencias:
    """Preferências da interface num JSON da pasta do usuário.

    Ficam no servidor, e não no armazenamento do navegador, porque a porta
    muda a cada partida e o navegador separa o armazenamento por porta.
    """

    def __init__(self, pasta: Path | None) -> None:
        self.arquivo = None if pasta is None else pasta / "preferencias.json"
        self._valores = {k: v[0] for k, v in PREFERENCIAS.items()}
        if self.arquivo is not None and self.arquivo.exists():
            try:
                self.atualizar(json.loads(self.arquivo.read_text(encoding="utf-8")), gravar=False)
            except (OSError, ValueError):
                pass  # arquivo ilegível: valem os padrões

    def ler(self) -> dict[str, str]:
        return dict(self._valores)

    def atualizar(self, dados: Any, gravar: bool = True) -> dict[str, str]:
        if not isinstance(dados, dict):
            raise ErroDePedido("pedido_invalido", "api.preferencia_invalida", None)
        for k, v in dados.items():
            if k not in PREFERENCIAS or v not in PREFERENCIAS[k]:
                raise ErroDePedido("pedido_invalido", "api.preferencia_invalida", k)
        self._valores.update(dados)
        if gravar and self.arquivo is not None:
            try:
                self.arquivo.parent.mkdir(parents=True, exist_ok=True)
                self.arquivo.write_text(json.dumps(self._valores, indent=2), encoding="utf-8")
            except OSError:
                pass  # sem gravar: vale só nesta sessão
        return self.ler()


def criar_app(token: str, pasta_interface: Path | None = None,
              calculista: Calculista | None = None, pasta_config: Path | None = None) -> FastAPI:
    app = FastAPI(title="Amsior", docs_url=None, redoc_url=None, openapi_url=None)
    calc = calculista or Calculista()
    app.state.calculista = calc
    prefs = Preferencias(pasta_config)

    @app.middleware("http")
    async def proteger(request: Request, chamar: Any) -> Any:
        if request.url.path.startswith("/api/"):
            if request.headers.get("x-amsior-token") != token:
                return JSONResponse(ErroDePedido("nao_autorizado", "api.nao_autorizado")
                                    .para_json(), status_code=401)
        return await chamar(request)

    def responder(rota: str, dados: dict[str, Any]) -> JSONResponse:
        r = calc(rota, dados)
        if "erro" in r:
            codigo = r["erro"]["codigo"]
            status = {"tempo_esgotado": 504, "interno": 500}.get(codigo, 422)
            return JSONResponse(r["erro"], status_code=status)
        return JSONResponse(r["ok"])

    @app.get("/api/v1/textos")
    def textos() -> JSONResponse:
        return JSONResponse(rota_textos())

    @app.get("/api/v1/preferencias")
    def ler_preferencias() -> JSONResponse:
        return JSONResponse(prefs.ler())

    @app.put("/api/v1/preferencias")
    async def gravar_preferencias(request: Request) -> JSONResponse:
        try:
            return JSONResponse(prefs.atualizar(await request.json()))
        except ErroDePedido as e:
            return JSONResponse(e.para_json(), status_code=422)
        except ValueError:
            return JSONResponse(ErroDePedido("pedido_invalido", "api.preferencia_invalida")
                                .para_json(), status_code=422)

    @app.get("/api/v1/glossario")
    def glossario() -> JSONResponse:
        return responder("glossario", {})

    @app.post("/api/v1/analisar")
    async def analisar(request: Request) -> JSONResponse:
        return responder("analisar", await _json(request))

    @app.post("/api/v1/isolar")
    async def isolar(request: Request) -> JSONResponse:
        return responder("isolar", await _json(request))

    if pasta_interface is not None and (pasta_interface / "index.html").exists():
        app.mount("/", StaticFiles(directory=pasta_interface, html=True), name="interface")
    return app


async def _json(request: Request) -> dict[str, Any]:
    try:
        dados = await request.json()
    except Exception:
        dados = None
    if not isinstance(dados, dict):
        return {"latex": None}
    return dados
