"""Operaciones de alto nivel usadas por la ventana y por la línea de comandos."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

from .detector import CATEGORIAS, Detector
from .formatos import procesar_archivo, soportado
from .motor import Anonimizador, Reversor
from .seudonimos import EXTENSION_TABLA, TablaSeudonimos, guardar_tabla


@dataclass
class Opciones:
    categorias: list = field(default_factory=lambda: list(CATEGORIAS))
    excluir: list = field(default_factory=list)
    siempre: list = field(default_factory=list)
    carpeta_salida: str = ""            # vacío = junto al original
    tabla_comun: bool = True            # una tabla para todo el lote
    modelo: str = "es_core_news_md"
    usar_modelo: bool = True
    pdf_a_word: bool = True             # del PDF, generar también una versión Word para la IA

    def tipos(self):
        return [t for c in self.categorias for t in CATEGORIAS[c][1]]


@dataclass
class Resultado:
    entrada: str
    salida: str = ""
    ok: bool = False
    reemplazos: int = 0
    avisos: list = field(default_factory=list)
    error: str = ""
    extras: list = field(default_factory=list)   # otros archivos generados


def _ruta_salida(entrada: str, carpeta: str, sufijo: str) -> str:
    base, ext = os.path.splitext(os.path.basename(entrada))
    for s in ("_anonimizado_texto", "_anonimizado", "_revertido"):
        if base.endswith(s):
            base = base[: -len(s)]
    carpeta = carpeta or os.path.dirname(os.path.abspath(entrada))
    ruta = os.path.join(carpeta, f"{base}{sufijo}{ext}")
    n = 2
    while os.path.exists(ruta) and os.path.abspath(ruta) != os.path.abspath(entrada):
        ruta = os.path.join(carpeta, f"{base}{sufijo} ({n}){ext}")
        n += 1
    return ruta


def crear_detector(op: Opciones) -> Detector:
    return Detector(op.tipos(), excluir=op.excluir, siempre=op.siempre,
                    modelo=op.modelo, usar_modelo=op.usar_modelo)


def anonimizar(rutas, op: Opciones, contrasena: str | None, detector: Detector | None = None,
               avisar=lambda msg: None, progreso=lambda i, n: None):
    """Devuelve (resultados, rutas_de_tablas)."""
    detector = detector or crear_detector(op)
    if detector.aviso:
        avisar("⚠ " + detector.aviso)
    resultados, tablas = [], []
    tabla_lote = TablaSeudonimos() if op.tabla_comun else None
    rutas = list(rutas)
    for i, ruta in enumerate(rutas):
        progreso(i, len(rutas))
        res = Resultado(ruta)
        if not soportado(ruta):
            res.error = "formato no soportado"
            resultados.append(res)
            continue
        motor = Anonimizador(detector, tabla_lote if tabla_lote is not None else TablaSeudonimos())
        try:
            salida = _ruta_salida(ruta, op.carpeta_salida, "_anonimizado")
            info = procesar_archivo(ruta, salida, motor)
            res.salida, res.ok = salida, True
            res.reemplazos, res.avisos = info["reemplazos"], info["avisos"]
            if op.pdf_a_word and ruta.lower().endswith(".pdf"):
                from .formatos import pdf as _pdf
                extra = _ruta_salida(ruta[:-4] + ".docx", op.carpeta_salida or
                                     os.path.dirname(os.path.abspath(ruta)), "_anonimizado_texto")
                _pdf.exportar_word(ruta, extra, motor)
                res.extras.append(extra)
            if tabla_lote is None:
                ruta_tabla = os.path.splitext(salida)[0] + EXTENSION_TABLA
                guardar_tabla(motor.tabla, ruta_tabla, contrasena)
                tablas.append(ruta_tabla)
        except Exception as e:  # noqa: BLE001 - se informa al usuario
            res.error = str(e) or e.__class__.__name__
        resultados.append(res)
    progreso(len(rutas), len(rutas))
    if tabla_lote is not None and any(r.ok for r in resultados):
        primera = next(r for r in resultados if r.ok)
        carpeta = op.carpeta_salida or os.path.dirname(primera.salida)
        if len([r for r in resultados if r.ok]) == 1:
            ruta_tabla = os.path.splitext(primera.salida)[0] + EXTENSION_TABLA
        else:
            ruta_tabla = os.path.join(
                carpeta, f"lote_anonimizado_{datetime.now():%Y%m%d-%H%M%S}{EXTENSION_TABLA}")
        guardar_tabla(tabla_lote, ruta_tabla, contrasena)
        tablas.append(ruta_tabla)
    return resultados, tablas


def revertir(rutas, tabla: TablaSeudonimos, carpeta_salida: str = "",
             progreso=lambda i, n: None):
    """Devuelve (resultados, reversor) — el reversor tiene el detalle de etiquetas."""
    reversor = Reversor(tabla)
    resultados = []
    rutas = list(rutas)
    for i, ruta in enumerate(rutas):
        progreso(i, len(rutas))
        res = Resultado(ruta)
        try:
            salida = _ruta_salida(ruta, carpeta_salida, "_revertido")
            info = procesar_archivo(ruta, salida, reversor)
            res.salida, res.ok = salida, True
            res.reemplazos, res.avisos = info["reemplazos"], info["avisos"]
        except Exception as e:  # noqa: BLE001
            res.error = str(e) or e.__class__.__name__
        resultados.append(res)
    progreso(len(rutas), len(rutas))
    return resultados, reversor
