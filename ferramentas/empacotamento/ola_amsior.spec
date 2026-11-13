# -*- mode: python ; coding: utf-8 -*-
# Amsior — protótipo de empacotamento (fase 1A). Rodar a partir desta pasta:
#   pyinstaller --noconfirm ola_amsior.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

RAIZ = Path(SPECPATH).resolve().parents[1]  # noqa: F821 (SPECPATH vem do PyInstaller)

datas = [(str(RAIZ / "biblioteca" / "_glossario.yaml"), "biblioteca")]
datas += collect_data_files("amsior")
binaries = []
hiddenimports = []
for pacote in ("CoolProp", "chemicals", "pint", "webview"):
    d, b, h = collect_all(pacote)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(  # noqa: F821
    ["ola_amsior.py"],
    pathex=[str(RAIZ / "motor")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython"],
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz, a.scripts, a.binaries, a.datas, [],
    name="ola_amsior", console=True, upx=False,
)
