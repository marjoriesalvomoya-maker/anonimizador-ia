"""PDF: redacción real (el texto original se elimina del archivo) y etiqueta escrita encima.

Se usa la posición exacta de cada carácter para borrar solo el dato (sin tocar letras
vecinas). Como un PDF no puede reacomodar el texto, la etiqueta se escribe en el espacio que
ocupaba el dato, con letra más pequeña si hace falta. Para trabajar con una IA conviene la
versión Word que genera `exportar_word`, con el texto en orden de lectura.
"""
from __future__ import annotations

import pymupdf as fitz

_FONDO = (0.93, 0.93, 0.93)


def _texto_latin(texto: str) -> str:
    return texto.encode("latin-1", "replace").decode("latin-1")   # Helvetica base: Latin-1


def _bloques(page):
    """Devuelve [(texto, caracteres)] por bloque, en orden de lectura.
    caracteres[i] = (rect, tamaño_fuente, nro_linea) del carácter i del texto, o None si es
    un espacio agregado entre líneas."""
    raw = page.get_text("rawdict", flags=fitz.TEXTFLAGS_TEXT)
    bloques = [b for b in raw["blocks"] if b.get("type") == 0]
    bloques.sort(key=lambda b: (round(b["bbox"][1], 0), b["bbox"][0]))
    salida = []
    for b in bloques:
        texto, chars = [], []
        nlinea = 0
        for linea in b["lines"]:
            nlinea += 1
            if texto and texto[-1] != " ":
                texto.append(" ")
                chars.append(None)
            for span in linea["spans"]:
                for ch in span["chars"]:
                    c = ch["c"]
                    if c.isspace():
                        if texto and texto[-1] == " ":
                            continue
                        c = " "
                    texto.append(c)
                    chars.append((fitz.Rect(ch["bbox"]), span["size"], nlinea))
        while texto and texto[-1] == " ":
            texto.pop()
            chars.pop()
        if texto:
            salida.append(("".join(texto), chars))
    return salida


def _todas(doc):
    paginas = [_bloques(p) for p in doc]
    total = sum(len(t) for bloques in paginas for t, _ in bloques)
    return paginas, total


def _tamano(texto, ancho, maximo):
    fs = max(4.0, min(maximo, 12.0))
    w = fitz.get_text_length(texto, fontname="helv", fontsize=fs)
    if w > ancho:
        fs = max(4.0, fs * ancho / w)
    return fs


def procesar(entrada: str, salida: str, motor) -> dict:
    doc = fitz.open(entrada)
    if doc.needs_pass:
        raise ValueError("El PDF está protegido con contraseña; ábrelo y guárdalo sin protección.")
    avisos = []
    paginas, total_chars = _todas(doc)
    if total_chars < 20 * max(1, len(doc)):
        avisos.append("Este PDF parece escaneado (casi no tiene texto seleccionable). Las imágenes "
                      "no se anonimizan: revisa el resultado o usa una versión con texto.")
    motor.analizar([t for bloques in paginas for t, _ in bloques])

    total = 0
    for page, bloques in zip(doc, paginas):
        etiquetas = []                                   # (rect, tamaño, texto)
        for texto, chars in bloques:
            for ini, fin, nuevo in motor.reemplazos(texto):
                # Agrupar los caracteres del dato por línea
                por_linea = {}
                for c in chars[ini:fin]:
                    if c is not None:
                        por_linea.setdefault(c[2], []).append(c)
                primera = True
                for _, cs in sorted(por_linea.items()):
                    r = fitz.Rect(cs[0][0])
                    for c in cs[1:]:
                        r |= c[0]
                    # Área interior: borra el dato sin tocar letras de al lado ni de otras líneas
                    w0, w1 = cs[0][0].width, cs[-1][0].width
                    interior = fitz.Rect(r.x0 + w0 * 0.3, r.y0 + r.height * 0.25,
                                         r.x1 - w1 * 0.3, r.y1 - r.height * 0.25)
                    page.add_redact_annot(interior, fill=_FONDO)
                    if primera:
                        etiquetas.append((r, max(c[1] for c in cs), _texto_latin(nuevo)))
                        primera = False
                total += 1
        if not etiquetas:
            continue
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                              graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        for r, tam, etiqueta in etiquetas:
            fs = _tamano(etiqueta, r.width, tam * 0.92)
            base = fitz.Point(r.x0, r.y0 + (r.height + fs * 0.72) / 2)
            page.insert_text(base, etiqueta, fontsize=fs, fontname="helv", color=(0, 0, 0))

    if motor.modo == "anonimizar":
        doc.set_metadata({})
        try:
            doc.del_xml_metadata()
        except Exception:
            pass
    doc.save(salida, garbage=4, deflate=True, clean=True)
    doc.close()
    return {"reemplazos": total, "avisos": avisos}


def exportar_word(entrada: str, salida: str, motor) -> None:
    """Versión Word del PDF, con el texto en orden de lectura (ideal para la IA).
    Usa el mismo motor (y por lo tanto la misma tabla) que `procesar`."""
    from docx import Document
    from docx.shared import Pt

    from ..motor import aplicar

    doc = fitz.open(entrada)
    paginas, _ = _todas(doc)
    motor.analizar([t for bloques in paginas for t, _ in bloques])
    word = Document()
    word.styles["Normal"].font.size = Pt(11)
    for n, bloques in enumerate(paginas):
        if n:
            word.add_page_break()
        for texto, _ in bloques:
            word.add_paragraph(aplicar(texto, motor.reemplazos(texto)))
    doc.close()
    word.core_properties.author = ""
    word.core_properties.last_modified_by = ""
    word.save(salida)
