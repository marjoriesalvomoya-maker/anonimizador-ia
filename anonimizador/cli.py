"""Línea de comandos.

Ejemplos:
  python -m anonimizador.cli anonimizar contrato.docx anexo.pdf
  python -m anonimizador.cli anonimizar carpeta/ --salida resultados/ --siempre "Proyecto Cóndor"
  python -m anonimizador.cli revertir respuesta_ia.docx --tabla contrato_anonimizado.tabla
  python -m anonimizador.cli revertir-texto --tabla t.tabla < respuesta.txt
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

from .detector import CATEGORIAS
from .formatos import soportado
from .motor import INSTRUCCION_IA, Reversor
from .seudonimos import cargar_tabla, tabla_esta_cifrada
from .servicio import Opciones, anonimizar, revertir


def _expandir(rutas):
    out = []
    for r in rutas:
        if os.path.isdir(r):
            for raiz, _, archivos in os.walk(r):
                out += [os.path.join(raiz, a) for a in sorted(archivos)
                        if soportado(a) and not a.startswith("~$") and "_anonimizado" not in a]
        else:
            out.append(r)
    return out


def _lista(valores, archivo):
    items = list(valores or [])
    if archivo:
        with open(archivo, encoding="utf-8") as f:
            items += [x.strip() for x in f if x.strip()]
    return items


def _contrasena(args, nueva: bool):
    if args.contrasena is not None:
        return args.contrasena or None
    if args.sin_contrasena:
        return None
    p = getpass.getpass("Contraseña para la tabla: ")
    if nueva and getpass.getpass("Repítela: ") != p:
        sys.exit("Las contraseñas no coinciden.")
    return p or None


def _cargar_tabla(args):
    ruta = args.tabla
    clave = None
    if tabla_esta_cifrada(ruta):
        clave = args.contrasena if args.contrasena is not None else getpass.getpass("Contraseña de la tabla: ")
    return cargar_tabla(ruta, clave)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="anonimizador", description="Anonimiza documentos para usarlos con IA.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("anonimizar", help="anonimiza documentos o carpetas")
    a.add_argument("rutas", nargs="+")
    a.add_argument("--salida", default="", help="carpeta de destino (por defecto, junto al original)")
    a.add_argument("--categorias", default=",".join(CATEGORIAS),
                   help=f"lista separada por comas: {', '.join(CATEGORIAS)}")
    a.add_argument("--siempre", action="append", help="término a anonimizar siempre (repetible)")
    a.add_argument("--siempre-archivo", help="archivo con un término por línea")
    a.add_argument("--excluir", action="append", help="término que nunca se anonimiza (repetible)")
    a.add_argument("--excluir-archivo")
    a.add_argument("--tabla-por-archivo", action="store_true", help="una tabla por documento")
    a.add_argument("--sin-modelo", action="store_true", help="solo reglas, sin modelo de lenguaje")
    a.add_argument("--sin-word-de-pdf", action="store_true", help="no crear la versión Word de los PDF")
    a.add_argument("--contrasena", help="contraseña de la tabla (si se omite, se pregunta)")
    a.add_argument("--sin-contrasena", action="store_true", help="guardar la tabla sin cifrar")

    r = sub.add_parser("revertir", help="restaura los datos reales en documentos")
    r.add_argument("rutas", nargs="+")
    r.add_argument("--tabla", required=True)
    r.add_argument("--salida", default="")
    r.add_argument("--contrasena")

    t = sub.add_parser("revertir-texto", help="restaura texto leído de la entrada estándar")
    t.add_argument("--tabla", required=True)
    t.add_argument("--contrasena")

    sub.add_parser("instruccion", help="muestra la instrucción recomendada para la IA")

    args = ap.parse_args(argv)

    if args.cmd == "instruccion":
        print(INSTRUCCION_IA)
        return 0

    if args.cmd == "anonimizar":
        cats = [c.strip() for c in args.categorias.split(",") if c.strip()]
        malas = [c for c in cats if c not in CATEGORIAS]
        if malas:
            sys.exit(f"Categorías desconocidas: {', '.join(malas)}")
        op = Opciones(categorias=cats, siempre=_lista(args.siempre, args.siempre_archivo),
                      excluir=_lista(args.excluir, args.excluir_archivo), carpeta_salida=args.salida,
                      tabla_comun=not args.tabla_por_archivo, usar_modelo=not args.sin_modelo,
                      pdf_a_word=not args.sin_word_de_pdf)
        rutas = _expandir(args.rutas)
        if not rutas:
            sys.exit("No hay documentos para procesar.")
        clave = _contrasena(args, nueva=True)
        res, tablas = anonimizar(rutas, op, clave, avisar=lambda m: print(m, file=sys.stderr))
        for x in res:
            print(f"{'OK ' if x.ok else 'ERR'} {x.entrada} -> {x.salida or x.error} "
                  f"({x.reemplazos} reemplazos)")
            for e in x.extras:
                print(f"    + {e}")
            for av in x.avisos:
                print(f"    aviso: {av}")
        for tb in tablas:
            print(f"Tabla: {tb}{'' if clave else ' (SIN CIFRAR)'}")
        return 0 if all(x.ok for x in res) else 1

    tabla = _cargar_tabla(args)
    if args.cmd == "revertir-texto":
        rev = Reversor(tabla)
        sys.stdout.write(rev.revertir_texto(sys.stdin.read()))
        if rev.desconocidas:
            print(f"\naviso: etiquetas sin correspondencia: {', '.join(sorted(rev.desconocidas))}",
                  file=sys.stderr)
        return 0

    res, rev = revertir(_expandir(args.rutas), tabla, args.salida)
    for x in res:
        print(f"{'OK ' if x.ok else 'ERR'} {x.entrada} -> {x.salida or x.error}")
    print(f"{sum(rev.restauradas.values())} etiquetas restauradas.")
    if rev.desconocidas:
        print(f"aviso: etiquetas sin correspondencia: {', '.join(sorted(rev.desconocidas))}")
    return 0 if all(x.ok for x in res) else 1


if __name__ == "__main__":
    sys.exit(main())
