"""Word (.docx), Excel (.xlsx) y PowerPoint (.pptx).

Se trabaja directamente sobre el XML interno para no perder formato: el texto de un párrafo
suele estar partido en varios fragmentos ("runs") con estilos distintos; los reemplazos se
aplican sobre el párrafo completo y se redistribuyen en los fragmentos originales.
"""
from __future__ import annotations

import posixpath
import re
import zipfile
from urllib.parse import quote, unquote

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_PARSER = etree.XMLParser(resolve_entities=False, huge_tree=True, no_network=True)


def _q(prefijo, nombre):
    return f"{{{NS[prefijo]}}}{nombre}"


EXTENSIONES = {
    ".docx": "word", ".docm": "word", ".dotx": "word",
    ".xlsx": "xl", ".xlsm": "xl", ".xltx": "xl",
    ".pptx": "ppt", ".pptm": "ppt",
}
_OMITIR = re.compile(r"(styles|stylesWithEffects|fontTable|settings|webSettings|numbering|theme\d*|"
                     r"vbaData|calcChain|styles\d*)\.xml$", re.I)


# --------------------------------------------------------------------------
# Reescritura de un grupo de nodos de texto como un solo párrafo
# --------------------------------------------------------------------------
def reescribir_nodos(nodos, motor) -> int:
    textos = [n.text or "" for n in nodos]
    completo = "".join(textos)
    if not completo.strip():
        return 0
    cambios = motor.reemplazos(completo)
    if not cambios:
        return 0
    inicios, dueno, pos = [], [], 0
    for i, t in enumerate(textos):
        inicios.append(pos)
        dueno.extend([i] * len(t))
        pos += len(t)
    nuevos = list(textos)
    for ini, fin, rep in sorted(cambios, reverse=True):
        i0, i1 = dueno[ini], dueno[fin - 1]
        li, lf = ini - inicios[i0], fin - inicios[i1]
        if i0 == i1:
            nuevos[i0] = nuevos[i0][:li] + rep + nuevos[i0][lf:]
        else:
            nuevos[i0] = nuevos[i0][:li] + rep
            for k in range(i0 + 1, i1):
                nuevos[k] = ""
            nuevos[i1] = nuevos[i1][lf:]
    for n, original, nuevo in zip(nodos, textos, nuevos):
        if nuevo != original:
            n.text = nuevo
            if n.tag.startswith("{" + NS["w"]) or n.tag.startswith("{" + NS["s"]):
                n.set(XML_SPACE, "preserve")
    return len(cambios)


def _ancestro(el, tags):
    p = el.getparent()
    while p is not None and p.tag not in tags:
        p = p.getparent()
    return p


def _grupos(root):
    """Agrupa nodos de texto por párrafo/celda, sin repetir ninguno."""
    grupos = []
    reglas = [
        ({_q("w", "p")}, _q("w", "t")),
        ({_q("w", "p")}, _q("w", "delText")),
        ({_q("a", "p")}, _q("a", "t")),
        ({_q("s", "si"), _q("s", "is"), _q("s", "text")}, _q("s", "t")),
    ]
    rph = _q("s", "rPh")
    for contenedores, tag in reglas:
        por_contenedor = {}
        orden = []
        for t in root.iter(tag):
            if tag == _q("s", "t") and _ancestro(t, {rph}) is not None:
                grupos.append([t])                      # texto fonético: aparte
                continue
            c = _ancestro(t, contenedores)
            clave = c if c is not None else t   # el propio elemento (id() puede reutilizarse)
            if clave not in por_contenedor:
                por_contenedor[clave] = []
                orden.append(clave)
            por_contenedor[clave].append(t)
        grupos.extend(por_contenedor[k] for k in orden)
    for tag in (_q("w", "instrText"),):                  # códigos de campo (HYPERLINK "mailto:...")
        grupos.extend([t] for t in root.iter(tag))
    for hf in ("oddHeader", "oddFooter", "evenHeader", "evenFooter", "firstHeader", "firstFooter"):
        grupos.extend([t] for t in root.iter(_q("s", hf)))
    return grupos


def _celdas_numericas(root):
    """Celdas Excel con número (sin fórmula): teléfonos guardados como número."""
    out = []
    for c in root.iter(_q("s", "c")):
        if c.get("t") in (None, "n") and c.find(_q("s", "f")) is None:
            v = c.find(_q("s", "v"))
            if v is not None and v.text and re.fullmatch(r"\d{8,19}", v.text):
                out.append((c, v))
    return out


# --------------------------------------------------------------------------
_ATRIB_AUTOR = {"author": "Anónimo", "initials": "A", "displayName": "Anónimo",
                "userId": "anonimo", "providerId": "None"}


def _anonimizar_autores(root) -> None:
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        for atr in list(el.attrib):
            local = atr.rsplit("}", 1)[-1]
            if local in _ATRIB_AUTOR:
                el.set(atr, _ATRIB_AUTOR[local])
            elif local == "name" and el.tag.endswith("}cmAuthor"):
                el.set(atr, "Anónimo")
        if el.tag == _q("s", "author"):
            el.text = "Anónimo"


def procesar(entrada: str, salida: str, motor) -> dict:
    ext = posixpath.splitext(entrada.lower())[1]
    carpeta = EXTENSIONES.get(ext)
    if carpeta is None:
        raise ValueError(f"Formato no soportado: {ext}")
    anonimizando = motor.modo == "anonimizar"

    with zipfile.ZipFile(entrada) as z:
        infos = z.infolist()
        datos = {i.filename: z.read(i.filename) for i in infos}

    arboles = {}
    for nombre, contenido in datos.items():
        if not nombre.endswith(".xml"):
            continue
        es_contenido = nombre.startswith(carpeta + "/") and not _OMITIR.search(nombre)
        es_meta = nombre in ("docProps/core.xml", "docProps/app.xml", "docProps/custom.xml")
        if es_contenido or es_meta:
            try:
                arboles[nombre] = etree.fromstring(contenido, _PARSER)
            except etree.XMLSyntaxError:
                continue

    grupos, numericas = [], []
    for nombre, root in arboles.items():
        if nombre.startswith("docProps/"):
            continue
        grupos.extend(_grupos(root))
        if carpeta == "xl" and "/worksheets/" in nombre:
            numericas.extend(_celdas_numericas(root))

    # Metadatos con texto libre (título, asunto, palabras clave...)
    meta_nodos = []
    core = arboles.get("docProps/core.xml")
    if core is not None:
        for el in core:
            local = etree.QName(el).localname
            if local in ("creator", "lastModifiedBy"):
                if anonimizando:
                    el.text = ""
            elif local in ("title", "subject", "description", "keywords", "category"):
                meta_nodos.append([el])
    app = arboles.get("docProps/app.xml")
    if app is not None and anonimizando:
        for el in app:
            if etree.QName(el).localname in ("Company", "Manager", "HyperlinkBase"):
                el.text = ""
    custom = arboles.get("docProps/custom.xml")
    if custom is not None:
        meta_nodos.extend([el] for el in custom.iter() if isinstance(el.tag, str)
                          and el.text and el.text.strip() and len(el) == 0)

    # Primera pasada: detectar en todo el documento
    textos = ["".join(n.text or "" for n in g) for g in grupos + meta_nodos]
    textos += [v.text for _, v in numericas]
    motor.analizar(textos)

    # Segunda pasada: reemplazar
    total = 0
    for g in grupos + meta_nodos:
        total += reescribir_nodos(g, motor)
    for c, v in numericas:
        cambios = motor.reemplazos(v.text)
        if len(cambios) == 1 and cambios[0][0] == 0 and cambios[0][1] == len(v.text):
            c.remove(v)
            c.set("t", "inlineStr")
            is_ = etree.SubElement(c, _q("s", "is"))
            etree.SubElement(is_, _q("s", "t")).text = cambios[0][2]
            total += 1

    if anonimizando:
        for nombre, root in arboles.items():
            if not nombre.startswith("docProps/"):
                _anonimizar_autores(root)

    # Enlaces externos (mailto:, URLs con datos)
    rels_modificados = {}
    for nombre, contenido in datos.items():
        if not nombre.endswith(".rels"):
            continue
        try:
            root = etree.fromstring(contenido, _PARSER)
        except etree.XMLSyntaxError:
            continue
        cambiado = False
        for r in root.iter(_q("rel", "Relationship")):
            if r.get("TargetMode") != "External":
                continue
            destino = unquote(r.get("Target", ""))
            cambios = motor.reemplazos(destino)
            if cambios:
                from ..motor import aplicar
                nuevo = aplicar(destino, cambios)
                r.set("Target", quote(nuevo, safe=":/@?=&#%+,;~"))
                cambiado = True
        if cambiado:
            rels_modificados[nombre] = root

    # Escribir el nuevo archivo conservando el orden y compresión de las partes
    with zipfile.ZipFile(salida, "w") as zout:
        for info in infos:
            nombre = info.filename
            if nombre in arboles or nombre in rels_modificados:
                root = arboles.get(nombre, rels_modificados.get(nombre))
                contenido = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                                           standalone=True)
            else:
                contenido = datos[nombre]
            zout.writestr(info, contenido, compress_type=info.compress_type)
    return {"reemplazos": total, "avisos": []}
