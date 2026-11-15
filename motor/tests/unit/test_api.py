# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""API local: token, rotas, formato de erro, processo de cálculo com tempo limite."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

pytest.importorskip("fastapi")

from amsior.api.app import Calculista, criar_app  # noqa: E402
from amsior.api.servico import executar, rota_textos, unidade_legivel  # noqa: E402

TOKEN = "teste-123"
GAS = [{"id": "P", "grandeza": "pressao_absoluta"}, {"id": "V", "grandeza": "volume"},
       {"id": "n", "grandeza": "quantidade_materia"},
       {"id": "R", "grandeza": "constante_gases", "papel": "constante"},
       {"id": "T", "grandeza": "temperatura_absoluta"}]


def chamar(app: Any, metodo: str, caminho: str, corpo: Any = None,
           token: str | None = TOKEN) -> tuple[int, Any]:
    """Cliente ASGI mínimo, sem dependências."""
    dados = b"" if corpo is None else json.dumps(corpo).encode()
    cabecalhos = [(b"content-type", b"application/json")]
    if token is not None:
        cabecalhos.append((b"x-amsior-token", token.encode()))
    escopo = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
              "method": metodo, "path": caminho, "raw_path": caminho.encode(),
              "query_string": b"", "headers": cabecalhos, "scheme": "http",
              "server": ("127.0.0.1", 0), "client": ("127.0.0.1", 0), "root_path": ""}
    saida: dict[str, Any] = {"corpo": b""}
    enviado = False

    async def receber() -> dict[str, Any]:
        nonlocal enviado
        if enviado:
            await asyncio.sleep(3600)
        enviado = True
        return {"type": "http.request", "body": dados, "more_body": False}

    async def enviar(msg: dict[str, Any]) -> None:
        if msg["type"] == "http.response.start":
            saida["status"] = msg["status"]
        elif msg["type"] == "http.response.body":
            saida["corpo"] += msg.get("body", b"")

    asyncio.run(app(escopo, receber, enviar))
    return saida["status"], json.loads(saida["corpo"] or b"null")


@pytest.fixture(scope="module")
def app() -> Any:
    return criar_app(TOKEN, calculista=Calculista(processo_separado=False))


def test_token_obrigatorio(app: Any) -> None:
    status, corpo = chamar(app, "GET", "/api/v1/glossario", token=None)
    assert status == 401 and corpo["codigo"] == "nao_autorizado"
    status, _ = chamar(app, "GET", "/api/v1/glossario", token="errado")
    assert status == 401


def test_glossario(app: Any) -> None:
    status, corpo = chamar(app, "GET", "/api/v1/glossario")
    assert status == 200 and len(corpo["grandezas"]) >= 60
    assert {"id": "volume", "nome": "Volume", "unidade": "m³"}.items() <= next(
        g for g in corpo["grandezas"] if g["id"] == "volume").items()


def test_analisar_ecoa_a_interpretacao(app: Any) -> None:
    status, corpo = chamar(app, "POST", "/api/v1/analisar", {"latex": "PV = nRT"})
    assert status == 200
    assert corpo["latex"] == "P V = n R T" and corpo["simbolos"] == ["P", "V", "n", "R", "T"]
    assert corpo["tipos"]["V"]["chave"] == "tipo.polinomial_1"


def test_erro_de_analise_no_formato_unico(app: Any) -> None:
    status, corpo = chamar(app, "POST", "/api/v1/analisar", {"latex": r"\frac{a}{"})
    assert status == 422 and corpo["codigo"] == "analise"
    assert set(corpo) == {"codigo", "mensagem", "chave", "detalhe"}


def test_isolar(app: Any) -> None:
    status, corpo = chamar(app, "POST", "/api/v1/isolar",
                           {"latex": "PV = nRT", "alvo": "V", "simbolos": GAS})
    assert status == 200 and corpo["estado"] == "com_passos"
    passos = corpo["ramos"][0]["passos"]
    assert [p["selo"]["estado"] for p in passos] == ["aprovado", "aprovado"]
    assert corpo["ramos"][0]["resultado"] == r"V = \frac{n R T}{P}"


def test_isolar_sem_grandeza_pede_a_grandeza(app: Any) -> None:
    status, corpo = chamar(app, "POST", "/api/v1/isolar", {"latex": "PV = nRT", "alvo": "V"})
    assert status == 422 and corpo["codigo"] == "grandeza_ausente"
    assert corpo["detalhe"] == ["P", "V", "n", "R", "T"]


def test_pedido_que_nao_e_json(app: Any) -> None:
    status, corpo = chamar(app, "POST", "/api/v1/isolar", "texto solto")
    assert status == 422 and corpo["codigo"] == "pedido_invalido"


def test_unidade_legivel() -> None:
    assert unidade_legivel("J/(mol*K)") == "J/(mol·K)"
    assert unidade_legivel("m**3") == "m³"
    assert unidade_legivel("1") == ""


def test_processo_separado_e_tempo_limite() -> None:
    calc = Calculista(tempo_limite=60)
    try:
        r = calc("isolar", {"latex": "PV = nRT", "alvo": "T", "simbolos": GAS})
        assert r["ok"]["estado"] == "com_passos"
        calc.tempo_limite = 0.05  # o próximo pedido (alguns segundos) não cabe no tempo
        cc = r"\ln\frac{P_{2}}{P_{1}} = -\frac{\Delta H_{vap}}{R}\left(\frac{1}{T_{2}}-\frac{1}{T_{1}}\right)"
        simb = [{"id": "P_{1}", "grandeza": "pressao_saturacao"},
                {"id": "P_{2}", "grandeza": "pressao_saturacao"},
                {"id": "\\Delta H_{\\mathrm{vap}}", "grandeza": "entalpia_vaporizacao_molar"},
                {"id": "R", "grandeza": "constante_gases", "papel": "constante"},
                {"id": "T_{1}", "grandeza": "temperatura_absoluta"},
                {"id": "T_{2}", "grandeza": "temperatura_absoluta"}]
        r = calc("isolar", {"latex": cc, "alvo": "T_{2}", "simbolos": simb})
        assert r["erro"]["codigo"] == "tempo_esgotado"
        calc.tempo_limite = 60  # o processo foi recriado e volta a responder
        assert "ok" in calc("analisar", {"latex": "x = 1"})
    finally:
        calc.fechar()


def test_executar_nunca_levanta() -> None:
    assert executar("isolar", {"latex": "PV = nRT", "alvo": "V", "simbolos": [{"id": "P",
                    "grandeza": "nao_existe"}]})["erro"]["codigo"] == "pedido_invalido"


# ---------------------------------------------------------------- interface

RAIZ = __import__("pathlib").Path(__file__).resolve().parents[3]
INTERFACE = RAIZ / "interface" / "src"


def test_textos_traz_so_chaves_da_interface(app: Any) -> None:
    status, corpo = chamar(app, "GET", "/api/v1/textos")
    assert status == 200 and corpo["ui.marca"] == "Amsior"
    assert all(k.startswith("ui.") for k in corpo)


@pytest.mark.skipif(not INTERFACE.exists(), reason="interface fora do repositório")
def test_toda_chave_ui_usada_na_interface_existe() -> None:
    import re
    from amsior.i18n import catalogo
    cat = catalogo("pt-BR")
    usadas: set[str] = set()
    for arq in (a for a in INTERFACE.rglob("*.ts*") if "testes" not in a.parts):
        usadas |= set(re.findall(r"[\"'`](ui\.[a-z0-9_.]+)[\"'`]", arq.read_text(encoding="utf-8")))
    assert usadas, "nenhuma chave encontrada: o padrão de busca mudou?"
    faltam = sorted(k for k in usadas if k not in cat and not k.endswith("."))
    assert not faltam, faltam


@pytest.mark.skipif(not INTERFACE.exists(), reason="interface fora do repositório")
def test_exemplos_da_interface_isolam_com_passos_certificados() -> None:
    """Cada exemplo do painel: símbolos e grandezas batem com a leitura e o alvo sai certificado."""
    from amsior.i18n import catalogo
    cat = catalogo("pt-BR")
    exemplos = json.loads((INTERFACE / "dados" / "exemplos.json").read_text(encoding="utf-8"))
    for ex in exemplos:
        assert f"ui.exemplo.{ex['id']}" in cat and f"ui.area.{ex['area']}" in cat, ex["id"]
        a = executar("analisar", {"latex": ex["latex"], "simbolos": ex["simbolos"]})["ok"]
        assert set(a["simbolos"]) == {s["id"] for s in ex["simbolos"]}, ex["id"]
        assert ex["alvo"] in a["simbolos"], ex["id"]
        r = executar("isolar", {"latex": ex["latex"], "alvo": ex["alvo"],
                                "simbolos": ex["simbolos"]})["ok"]
        assert r["estado"] == "com_passos", ex["id"]
        for ramo in r["ramos"]:
            assert ramo["passos"], ex["id"]
            assert all(p["selo"] and p["selo"]["estado"] == "aprovado" for p in ramo["passos"]), ex["id"]


def test_preferencias_ficam_no_arquivo_do_usuario(tmp_path: Any) -> None:
    app = criar_app(TOKEN, calculista=Calculista(processo_separado=False), pasta_config=tmp_path)
    status, corpo = chamar(app, "GET", "/api/v1/preferencias")
    assert status == 200 and corpo == {"aparencia": "d", "modo": "sistema", "nivel": "completo"}
    status, corpo = chamar(app, "PUT", "/api/v1/preferencias", {"aparencia": "h", "modo": "escuro"})
    assert status == 200 and corpo["aparencia"] == "h"
    # Nova partida (outra porta): as preferências continuam.
    app2 = criar_app(TOKEN, calculista=Calculista(processo_separado=False), pasta_config=tmp_path)
    assert chamar(app2, "GET", "/api/v1/preferencias")[1]["modo"] == "escuro"
    status, corpo = chamar(app2, "PUT", "/api/v1/preferencias", {"aparencia": "z"})
    assert status == 422 and corpo["codigo"] == "pedido_invalido"
    status, _ = chamar(app2, "PUT", "/api/v1/preferencias", {"fonte": "d"})
    assert status == 422


def test_autoteste_da_janela_sobe_o_servidor_de_verdade(tmp_path: Any, monkeypatch: Any) -> None:
    """O que o CI roda no executável: servidor em porta livre, token, interface e cálculo."""
    from amsior import janela
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text('<div id="raiz"></div>', encoding="utf-8")
    monkeypatch.setattr(janela, "pasta_interface", lambda: dist)
    s = janela.Servidor(janela.porta_livre(), "tk", None)
    s.subir()
    try:
        rel = janela.autoteste(s)
    finally:
        s.parar()
    assert rel["interface"] == "ok" and rel["grandezas"] >= 60
    assert rel["isolar"] == "V = \\frac{n R T}{p}"


def test_glossario_em_json_e_o_mesmo_do_yaml(tmp_path: Any) -> None:
    """No navegador (sem PyYAML) o motor lê _glossario.json; tem de dar o mesmo glossário."""
    import yaml
    from amsior.units.glossario import carregar_glossario, pasta_biblioteca
    dados = yaml.safe_load((pasta_biblioteca() / "_glossario.yaml").read_text(encoding="utf-8"))
    (tmp_path / "_glossario.json").write_text(json.dumps(dados), encoding="utf-8")
    de_json, de_yaml = carregar_glossario(str(tmp_path / "_glossario.json")), carregar_glossario()
    assert de_json._g == de_yaml._g and len(de_json._g) >= 60


def test_textos_tambem_saem_pelo_executar() -> None:
    """O trabalhador do navegador só fala por executar(rota, dados)."""
    assert executar("textos", {})["ok"] == rota_textos()
