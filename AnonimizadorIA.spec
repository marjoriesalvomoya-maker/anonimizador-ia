# -*- mode: python ; coding: utf-8 -*-
# Empaquetado con PyInstaller para Windows y Mac:  pyinstaller AnonimizadorIA.spec
import sys
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = [("recursos", "recursos")], [], []
paquetes = ["spacy", "thinc", "es_core_news_md", "srsly", "blis", "cymem", "preshed", "murmurhash",
            "catalogue", "confection", "wasabi", "weasel", "spacy_legacy", "spacy_loggers",
            "langcodes", "language_data", "tkinterdnd2", "pymupdf"]
for p in paquetes:
    try:
        d, b, h = collect_all(p)
        datas += d; binaries += b; hiddenimports += h
    except Exception as e:
        print("aviso: no se pudo recolectar", p, e)
for p in ["spacy", "thinc", "es_core_news_md", "spacy_legacy", "spacy_loggers", "weasel",
          "confection", "catalogue", "srsly"]:
    try:
        datas += copy_metadata(p)
    except Exception:
        pass

# Solo español: se descartan las pruebas internas y los demás idiomas de spaCy (~80 MB menos)
def _idioma_innecesario(ruta: str) -> bool:
    partes = ruta.replace("\\", "/").replace(".", "/").split("/")
    if "tests" in partes and ("spacy" in partes or "thinc" in partes):
        return True
    if "spacy" in partes and "lang" in partes:
        i = partes.index("lang")
        if i + 1 < len(partes):
            sub = partes[i + 1]
            return len(sub) <= 3 and sub not in ("es", "xx", "py")
    return False


hiddenimports = [h for h in hiddenimports if not _idioma_innecesario(h)]
datas = [d for d in datas if not _idioma_innecesario(d[1] + "/" + d[0].split("/")[-1])]

a = Analysis(
    ["AnonimizadorIA.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["cryptography.hazmat.primitives.kdf.pbkdf2"],
    excludes=["matplotlib", "IPython", "notebook", "pandas", "scipy", "torch", "tensorflow",
              "pytest", "openpyxl", "PIL"],
    noarchive=False,
)
a.pure = [m for m in a.pure if not _idioma_innecesario(m[0])]
a.datas = [d for d in a.datas if not _idioma_innecesario(d[0])]
a.binaries = [b for b in a.binaries if not _idioma_innecesario(b[0])]
pyz = PYZ(a.pure)
icono = "recursos/icono.icns" if sys.platform == "darwin" else "recursos/icono.ico"

exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="AnonimizadorIA",
          console=False, icon=icono, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="AnonimizadorIA", upx=False)

if sys.platform == "darwin":
    app = BUNDLE(coll, name="Anonimizador IA.app", icon=icono,
                 bundle_identifier="cl.anonimizador.ia",
                 info_plist={"CFBundleShortVersionString": "1.0.0",
                             "NSHighResolutionCapable": True,
                             "CFBundleDisplayName": "Anonimizador IA"})
