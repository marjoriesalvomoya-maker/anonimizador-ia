"""Motores de transformación de texto: Anonimizador (datos -> etiquetas) y Reversor (etiquetas -> datos).

Ambos exponen la misma interfaz que usan los procesadores de formatos:
    analizar(textos)        primera pasada sobre todo el documento
    reemplazos(texto)       lista de (inicio, fin, texto_nuevo)
"""
from __future__ import annotations

import re
from collections import Counter

from .detector import TODOS_LOS_TIPOS, Detector
from .seudonimos import TablaSeudonimos


def _patron_forma(forma: str) -> str:
    return re.escape(forma).replace(r"\ ", r"\s+")


def _clave_forma(texto: str) -> str:
    return " ".join(texto.lower().split())


class Anonimizador:
    modo = "anonimizar"

    def __init__(self, detector: Detector, tabla: TablaSeudonimos | None = None):
        self.detector = detector
        self.tabla = tabla if tabla is not None else TablaSeudonimos()
        self.conteo: Counter = Counter()
        self._regex = None
        self._buscar: dict[str, str] = {}
        self._n_formas = -1

    def analizar(self, textos) -> None:
        textos = [t for t in textos if t and t.strip()]
        if textos:
            for ents in self.detector.detectar_lote(textos):
                for e in ents:
                    self.tabla.registrar(e.tipo, e.texto)
        self._compilar()

    def _compilar(self) -> None:
        formas = self.tabla.formas()
        if len(formas) == self._n_formas:
            return
        self._n_formas = len(formas)
        self._buscar = {_clave_forma(f): et for f, et in formas.items()}
        if not formas:
            self._regex = None
            return
        partes = sorted(formas, key=len, reverse=True)
        patron = "|".join(_patron_forma(f) for f in partes)
        self._regex = re.compile(rf"(?<![\w@])(?:{patron})(?![\w@])", re.IGNORECASE)

    def reemplazos(self, texto: str):
        if not texto or self._regex is None:
            return []
        out = []
        for m in self._regex.finditer(texto):
            et = self._buscar.get(_clave_forma(m.group(0)))
            if et:
                out.append((m.start(), m.end(), f"[{et}]"))
                self.conteo[et.rsplit("_", 1)[0]] += 1
        return out


# ----------------------------------------------------------------------
_TIPOS_RE = "|".join(sorted(TODOS_LOS_TIPOS, key=len, reverse=True))
# Reconoce las etiquetas aunque la IA las altere: [PERSONA_1], [ persona 1 ], \[PERSONA_1\],
# PERSONA_1, (PERSONA_1), [Persona-1], \[PERSONA\_1\], 【PERSONA_1】 ...
PATRON_ETIQUETA = re.compile(
    rf"(?:\\?[\[【〔]\s*(?P<t1>{_TIPOS_RE})(?:\\?_|[\s-])?(?P<n1>\d+)\s*\\?[\]】〕])"
    rf"|(?<![\w\[])(?P<t2>{_TIPOS_RE})\\?_(?P<n2>\d+)(?!\w)",
    re.IGNORECASE)


class Reversor:
    modo = "revertir"

    def __init__(self, tabla: TablaSeudonimos):
        self.tabla = tabla
        self.restauradas: Counter = Counter()
        self.desconocidas: Counter = Counter()
        self.conteo = self.restauradas

    def analizar(self, textos) -> None:  # no necesita primera pasada
        pass

    def reemplazos(self, texto: str):
        if not texto:
            return []
        out = []
        for m in PATRON_ETIQUETA.finditer(texto):
            tipo = (m.group("t1") or m.group("t2")).upper()
            num = m.group("n1") or m.group("n2")
            et = f"{tipo}_{int(num)}"
            original = self.tabla.original(et)
            if original is None:
                self.desconocidas[et] += 1
                continue
            out.append((m.start(), m.end(), original))
            self.restauradas[et] += 1
        return out

    def revertir_texto(self, texto: str) -> str:
        return aplicar(texto, self.reemplazos(texto))


def aplicar(texto: str, cambios) -> str:
    for ini, fin, nuevo in sorted(cambios, reverse=True):
        texto = texto[:ini] + nuevo + texto[fin:]
    return texto


INSTRUCCION_IA = (
    "Este documento fue anonimizado: los datos personales se reemplazaron por etiquetas "
    "entre corchetes, como [PERSONA_1], [RUT_1] u [ORGANIZACION_2]. Cada etiqueta representa "
    "siempre al mismo dato. Al responder o editar, conserva las etiquetas exactamente como "
    "están escritas (con corchetes, mayúsculas y número), no las traduzcas, no inventes "
    "etiquetas nuevas y no intentes adivinar los datos reales."
)
