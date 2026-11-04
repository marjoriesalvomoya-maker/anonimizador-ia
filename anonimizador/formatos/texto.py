"""Texto plano (.txt, .md, .csv): útil sobre todo para revertir respuestas de la IA."""
from __future__ import annotations

import re

from ..motor import aplicar


def leer(ruta: str) -> tuple[str, str]:
    with open(ruta, "rb") as f:
        crudo = f.read()
    for cod in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return crudo.decode(cod), cod
        except UnicodeDecodeError:
            continue
    return crudo.decode("utf-8", "replace"), "utf-8"


def procesar(entrada: str, salida: str, motor) -> dict:
    texto, cod = leer(entrada)
    motor.analizar([p for p in re.split(r"\n\s*\n|\r\n\s*\r\n", texto) if p.strip()])
    cambios = motor.reemplazos(texto)
    nuevo = aplicar(texto, cambios)
    with open(salida, "w", encoding="utf-8-sig" if cod == "utf-8-sig" else "utf-8", newline="") as f:
        f.write(nuevo)
    return {"reemplazos": len(cambios), "avisos": []}
