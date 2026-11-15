# -*- mode: python ; coding: utf-8 -*-
# Amsior — executável do aplicativo (fase 1B). Antes, compilar a interface:
#   cd interface && npm ci && npm run build
# Depois, a partir desta pasta:
#   pyinstaller --noconfirm amsior.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

RAIZ = Path(SPECPATH).resolve().parents[1]  # noqa: F821 (SPECPATH vem do PyInstaller)
INTERFACE = RAIZ / "interface" / "dist"
if not (INTERFACE / "index.html").exists():
    raise SystemExit("interface/dist não existe: rode 'npm run build' em interface/ antes")

datas = [(str(RAIZ / "biblioteca" / "_glossario.yaml"), "biblioteca"), (str(INTERFACE), "interface")]
# Catálogos de texto explícitos: com o motor instalado em modo editável, collect_data_files não os acha.
datas += [(str(RAIZ / "motor" / "amsior" / "i18n" / "*.json"), "amsior/i18n")]
datas += collect_data_files("amsior")
binaries = []
hiddenimports = collect_submodules("uvicorn") + collect_submodules("amsior")
for pacote in ("pint", "webview"):
    d, b, h = collect_all(pacote)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(  # noqa: F821
    ["amsior_app.py"],
    pathex=[str(RAIZ / "motor")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "CoolProp", "chemicals", "fluids", "scipy", "pandas"],
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Amsior", console=False, upx=False,
)
