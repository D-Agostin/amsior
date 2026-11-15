# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Monta o motor do Amsior para o navegador (fase 1C, decisão 0006).

Gera ``interface/public/motor/``:

- ``motor-<hash>.zip``: as bibliotecas Python que o Pyodide desempacota em
  ``site-packages`` (SymPy, mpmath, pint e dependências, nas versões do arquivo
  de trava, mais o pacote ``amsior``) e a biblioteca de dados (glossário em JSON);
- ``motor.json``: nome do zip, hash, tamanho e as versões incluídas;
- ``dados.json``: textos da interface e glossário, para a tela abrir na hora,
  antes de o motor terminar de carregar (gerados pelas mesmas rotas do motor).

O nome leva o hash do conteúdo: o navegador guarda o zip em cache sem risco de
usar uma versão velha. O zip é determinístico (ordem e datas fixas), então o
mesmo código gera sempre o mesmo hash.

Bytecode: se houver um CPython da mesma versão do Pyodide (3.14; variável
AMSIOR_PYTHON_PYODIDE, ``python3.14`` no PATH ou ``uv python find 3.14``), as
bibliotecas de terceiros vão só como ``.pyc`` já compilados, no lugar dos fontes:
o navegador não compila o SymPy a cada partida (cerca de 2 s a menos) e o zip
fica do mesmo tamanho. O pacote ``amsior`` vai com os fontes e o bytecode. Sem
o CPython 3.14, tudo vai como fonte e funciona igual, só mais devagar.

Uso, da raiz do repositório:  python ferramentas/web/montar_motor.py
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "interface" / "public" / "motor"
TRAVA = RAIZ / "motor" / "requirements-lock.txt"

#: Bibliotecas que o motor importa no navegador. Todas são só Python (py3-none-any).
PACOTES = ["sympy", "mpmath", "pint", "flexcache", "flexparser", "platformdirs", "typing_extensions"]

#: O que não vai para o navegador: testes das bibliotecas e o que só serve no desktop.
_FORA = re.compile(r"(^|/)(tests|benchmarks|__pycache__)(/|$)|\.pyc$|^amsior/(janela|api/app)\.py$")

_DATA_FIXA = (2026, 1, 1, 0, 0, 0)


def versoes_travadas() -> dict[str, str]:
    v: dict[str, str] = {}
    for linha in TRAVA.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9_.-]+)==([^\s;]+)", linha.strip())
        if m:
            v[m.group(1).lower().replace("-", "_")] = m.group(2)
    return v


def baixar_rodas(destino: Path, versoes: dict[str, str]) -> list[Path]:
    pedidos = [f"{p}=={versoes[p.lower()]}" for p in PACOTES]
    subprocess.run([sys.executable, "-m", "pip", "download", "--quiet", "--no-deps",
                    "--only-binary=:all:", "--dest", str(destino), *pedidos], check=True)
    rodas = sorted(destino.glob("*.whl"))
    for r in rodas:
        if not r.name.endswith("-none-any.whl"):
            raise SystemExit(f"{r.name} não é só Python: não roda no Pyodide sem compilação própria")
    return rodas


def python_do_pyodide() -> str | None:
    """CPython com a mesma versão (e o mesmo número mágico de bytecode) do Pyodide."""
    candidatos = [os.environ.get("AMSIOR_PYTHON_PYODIDE"), shutil.which("python3.14")]
    try:
        candidatos.append(subprocess.run(["uv", "python", "find", "3.14"], capture_output=True,
                                         text=True, check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        pass
    for c in candidatos:
        if c and Path(c).exists():
            return c
    return None


def compilar(arquivos: dict[str, bytes], python: str) -> dict[str, bytes]:
    """Troca os fontes de terceiros por ``.pyc`` ao lado (sem fonte) e acrescenta o
    bytecode do ``amsior`` em ``__pycache__`` (unchecked-hash: vale com as datas fixas)."""
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)
        for nome, conteudo in arquivos.items():
            if nome.endswith(".py"):
                (raiz / nome).parent.mkdir(parents=True, exist_ok=True)
                (raiz / nome).write_bytes(conteudo)
        terceiros = [str(d) for d in raiz.iterdir() if d.is_dir() and d.name != "amsior"]
        terceiros += [str(f) for f in raiz.glob("*.py")]
        base = [python, "-m", "compileall", "-q", "-j", "0", "--invalidation-mode", "unchecked-hash"]
        # Sem -O/-OO: tirar asserts e docstrings encolheria o zip, mas muda o comportamento
        # das bibliotecas, e o motor tem de ser o mesmo do Python nativo (seção 10.1).
        subprocess.run([*base, "-b", "-s", str(raiz), *terceiros], check=True)
        subprocess.run([*base, "-s", str(raiz), str(raiz / "amsior")], check=True)
        novos = dict(arquivos)
        for f in sorted(raiz.rglob("*.pyc")):
            rel = f.relative_to(raiz).as_posix()
            novos[rel] = f.read_bytes()
            if "__pycache__" not in rel:
                novos.pop(rel[:-1], None)  # x.pyc substitui x.py
        return novos


def glossario_json() -> bytes:
    import yaml

    dados = yaml.safe_load((RAIZ / "biblioteca" / "_glossario.yaml").read_text(encoding="utf-8"))
    return json.dumps(dados, ensure_ascii=False, sort_keys=True).encode("utf-8")


def montar() -> dict[str, object]:
    versoes = versoes_travadas()
    arquivos: dict[str, bytes] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for roda in baixar_rodas(Path(tmp), versoes):
            with zipfile.ZipFile(roda) as z:
                for nome in z.namelist():
                    if not nome.endswith("/") and not _FORA.search(nome):
                        arquivos[nome] = z.read(nome)
    pacote = RAIZ / "motor" / "amsior"
    for f in sorted(pacote.rglob("*")):
        rel = "amsior/" + f.relative_to(pacote).as_posix()
        if f.is_file() and not _FORA.search(rel):
            arquivos[rel] = f.read_bytes()
    arquivos["amsior_dados/biblioteca/_glossario.json"] = glossario_json()
    python = python_do_pyodide()
    if python:
        arquivos = compilar(arquivos, python)
    else:
        print("Aviso: sem CPython 3.14, o motor vai sem bytecode (a partida no navegador fica mais lenta)",
              file=sys.stderr)
    bytecode = [n for n in arquivos if n.endswith(".pyc")]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for nome in sorted(arquivos):
            info = zipfile.ZipInfo(nome, _DATA_FIXA)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, arquivos[nome])
    dados = buf.getvalue()
    sha = hashlib.sha256(dados).hexdigest()
    nome = f"motor-{sha[:16]}.zip"

    SAIDA.mkdir(parents=True, exist_ok=True)
    for velho in SAIDA.glob("motor-*.zip"):
        velho.unlink()
    (SAIDA / nome).write_bytes(dados)
    manifesto = {
        "arquivo": nome, "sha256": sha, "bytes": len(dados), "arquivos": len(arquivos),
        "bytecode": len(bytecode),
        "versoes": {p: versoes[p.lower()] for p in PACOTES},
        # relativo a site-packages, onde o zip é desempacotado
        "biblioteca": "amsior_dados/biblioteca",
    }
    (SAIDA / "motor.json").write_text(json.dumps(manifesto, indent=2) + "\n", encoding="utf-8")
    (SAIDA / "dados.json").write_text(json.dumps(dados_da_interface(), ensure_ascii=False), encoding="utf-8")
    return manifesto


def dados_da_interface() -> dict[str, object]:
    sys.path.insert(0, str(RAIZ / "motor"))
    from amsior.api.servico import executar

    return {"textos": executar("textos", {})["ok"], "glossario": executar("glossario", {})["ok"]}


if __name__ == "__main__":
    print(json.dumps(montar(), indent=2))
