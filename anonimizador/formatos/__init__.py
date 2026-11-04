"""Despacho por tipo de archivo."""
from __future__ import annotations

import os

from . import ooxml, pdf, texto

FORMATOS = {
    **{ext: ooxml for ext in ooxml.EXTENSIONES},
    ".pdf": pdf,
    ".txt": texto, ".md": texto, ".csv": texto, ".tsv": texto,
}
EXTENSIONES_SOPORTADAS = sorted(FORMATOS)


def soportado(ruta: str) -> bool:
    return os.path.splitext(ruta.lower())[1] in FORMATOS


def procesar_archivo(entrada: str, salida: str, motor) -> dict:
    ext = os.path.splitext(entrada.lower())[1]
    if ext == ".doc" or ext == ".xls" or ext == ".ppt":
        raise ValueError("Formato antiguo de Office: ábrelo y guárdalo como .docx/.xlsx/.pptx.")
    modulo = FORMATOS.get(ext)
    if modulo is None:
        raise ValueError(f"Formato no soportado: {ext or 'sin extensión'}")
    if os.path.abspath(entrada) == os.path.abspath(salida):
        raise ValueError("El archivo de salida no puede sobrescribir el original.")
    tmp = salida + ".tmp" + ext
    try:
        res = modulo.procesar(entrada, tmp, motor)
        os.replace(tmp, salida)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return res
