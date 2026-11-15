# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
# Partida do motor dentro do Pyodide (navegador e Node). Roda uma vez, depois de o
# zip do motor ser desempacotado em site-packages; deixa `chamar` pronto para o JS.
import json
import os
import site
import sys

_SITE = site.getsitepackages()[0] if hasattr(site, "getsitepackages") else sys.path[-1]
os.environ["AMSIOR_BIBLIOTECA"] = os.path.join(_SITE, "amsior_dados", "biblioteca")

from amsior.api.servico import executar  # noqa: E402

# Primeira chamada carrega o glossário e o SymPy: a espera fica na partida, não no primeiro clique.
executar("glossario", {})


def chamar(rota: str, dados_json: str) -> str:
    return json.dumps(executar(rota, json.loads(dados_json)), ensure_ascii=False)
