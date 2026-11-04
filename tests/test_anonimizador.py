"""Pruebas: python -m pytest tests -q"""
import os
import sys
import zipfile

import openpyxl
import pymupdf as fitz
import pytest
from docx import Document

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crear_ejemplos import crear_docx, crear_pdf, crear_xlsx  # noqa: E402

from anonimizador.detector import Detector, luhn_valido, rut_valido  # noqa: E402
from anonimizador.motor import Anonimizador, Reversor, aplicar  # noqa: E402
from anonimizador.seudonimos import (ContrasenaIncorrecta, cargar_tabla,  # noqa: E402
                                     guardar_tabla)
from anonimizador.servicio import Opciones, anonimizar, revertir  # noqa: E402

SENSIBLES = ["Juan", "Pérez", "González", "12.345.678", "juan.perez", "Leones", "8765 4321",
             "Santander", "BBCL", "Pedro Rojas", "Constructora", "0012345678", "2345 6789"]


def fugas(texto):
    return [s for s in SENSIBLES if s in texto]


def texto_ooxml(ruta):
    with zipfile.ZipFile(ruta) as z:
        return " ".join(z.read(n).decode("utf8", "ignore") for n in z.namelist()
                        if n.endswith((".xml", ".rels")))


@pytest.fixture(scope="module")
def detector():
    return Detector()


# ---------------------------------------------------------------- reglas
def test_rut():
    assert rut_valido("12.345.678-5")
    assert rut_valido("76543210-3")
    assert not rut_valido("12.345.678-9")


def test_luhn():
    assert luhn_valido("4111 1111 1111 1111")
    assert not luhn_valido("4111 1111 1111 1112")


def test_detecta_y_mantiene_comunas(detector):
    t = ("Don Juan Pérez Soto, RUT 12.345.678-5, con domicilio en Avenida Los Leones 1234, "
         "Providencia, ciudad de Santiago, región Metropolitana. Fono +56 9 8765 4321.")
    ents = {(e.tipo, e.texto) for e in detector.detectar(t)}
    assert ("PERSONA", "Juan Pérez Soto") in ents
    assert ("RUT", "12.345.678-5") in ents
    assert ("TELEFONO", "+56 9 8765 4321") in ents
    assert any(tp == "DIRECCION" and "Leones 1234" in tx for tp, tx in ents)
    textos = " ".join(tx for _, tx in ents)
    assert "Providencia" not in textos and "Santiago" not in textos


def test_instituciones_publicas_se_mantienen(detector):
    t = "La causa la conoce el Juzgado de Letras de Talagante y la Corte de Apelaciones de San Miguel."
    assert not [e for e in detector.detectar(t) if e.tipo in ("ORGANIZACION", "LUGAR")]


def test_nombres_en_mayusculas(detector):
    ents = detector.detectar("Comparece don JUAN PÉREZ SOTO, chileno, casado.")
    assert [(e.tipo, e.texto) for e in ents] == [("PERSONA", "JUAN PÉREZ SOTO")]


def test_listas_del_usuario():
    d = Detector(excluir=["Banco Santander"], siempre=["Proyecto Cóndor"])
    tipos = {(e.tipo, e.texto) for e in d.detectar("Pago al Banco Santander por el Proyecto Cóndor.")}
    assert ("DATO", "Proyecto Cóndor") in tipos
    assert not any(tx == "Banco Santander" for _, tx in tipos)


# ---------------------------------------------------------------- motor
def test_consistencia_y_vinculo_de_apellido(detector):
    a = Anonimizador(detector)
    t = "Don Juan Pérez Soto firmó. Luego el Sr. Pérez pagó. JUAN PÉREZ SOTO aceptó."
    a.analizar([t])
    out = aplicar(t, a.reemplazos(t))
    assert out.count("[PERSONA_1]") == 3 and "Pérez" not in out


def test_reversion_tolerante(detector):
    a = Anonimizador(detector)
    a.analizar(["Don Juan Pérez Soto, RUT 12.345.678-5."])
    r = Reversor(a.tabla)
    respuesta_ia = ("Resumen: **PERSONA_1** (\\[RUT\\_1\\]) firmó. [ Persona 1 ] confirma. "
                    "(PERSONA_1) y [RUT-1]. Además [PERSONA_7].")
    out = r.revertir_texto(respuesta_ia)
    assert out.count("Juan Pérez Soto") == 3 and out.count("12.345.678-5") == 2
    assert "[PERSONA_7]" in out and r.desconocidas["PERSONA_7"] == 1


def test_tabla_cifrada(tmp_path, detector):
    a = Anonimizador(detector)
    a.analizar(["Don Juan Pérez Soto"])
    ruta = str(tmp_path / "t.tabla")
    guardar_tabla(a.tabla, ruta, "secreta")
    assert "Juan" not in open(ruta, encoding="utf-8").read()
    with pytest.raises(ContrasenaIncorrecta):
        cargar_tabla(ruta, "otra")
    assert cargar_tabla(ruta, "secreta").original("PERSONA_1") == "Juan Pérez Soto"


# ---------------------------------------------------------------- formatos
@pytest.fixture(scope="module")
def lote(tmp_path_factory):
    d = tmp_path_factory.mktemp("lote")
    rutas = [str(d / "contrato.docx"), str(d / "clientes.xlsx"), str(d / "contrato.pdf")]
    crear_docx(rutas[0])
    crear_xlsx(rutas[1])
    crear_pdf(rutas[2])
    res, tablas = anonimizar(rutas, Opciones(), "clave")
    assert all(r.ok for r in res), [r.error for r in res]
    return d, res, tablas


def test_word_sin_fugas_y_con_formato(lote):
    _, res, _ = lote
    ruta = res[0].salida
    assert fugas(texto_ooxml(ruta)) == []
    doc = Document(ruta)
    p = doc.paragraphs[1]
    assert "[PERSONA_1]" in p.text
    assert any(r.bold and "[PERSONA_1]" in r.text for r in p.runs)   # conserva negrita
    assert doc.core_properties.author == ""
    assert "Providencia" in "\n".join(x.text for x in doc.paragraphs)


def test_excel_sin_fugas(lote):
    _, res, _ = lote
    assert fugas(texto_ooxml(res[1].salida)) == []
    ws = openpyxl.load_workbook(res[1].salida).active
    assert ws["D2"].value.startswith("[TELEFONO_")       # número convertido a etiqueta
    assert ws["F4"].value == "=SUM(F2:F3)"                # fórmulas intactas
    assert ws["E2"].value == "Providencia"


def test_pdf_sin_fugas_y_version_word(lote):
    _, res, _ = lote
    texto = fitz.open(res[2].salida)[0].get_text()
    assert fugas(texto) == []
    assert "[PERSONA_1]" in texto
    word = "\n".join(p.text for p in Document(res[2].extras[0]).paragraphs)
    assert "[PERSONA_1]" in word and fugas(word) == []


def test_ida_y_vuelta_word(lote, tmp_path):
    _, res, tablas = lote
    tabla = cargar_tabla(tablas[0], "clave")
    out, _ = revertir([res[0].salida], tabla, str(tmp_path))
    original = Document(str(res[0].entrada))
    revertido = Document(out[0].salida)
    assert ([p.text for p in revertido.paragraphs[:5]] ==
            [p.text.replace("Sr. Pérez", "Sr. Juan Pérez Soto")
                    .replace("Sra. González", "Sra. María José González Rojas")
             for p in original.paragraphs[:5]])


def test_documento_nuevo_escrito_por_la_ia(lote, tmp_path):
    """La IA crea un Word nuevo, cambia formato y altera algunas etiquetas."""
    _, _, tablas = lote
    tabla = cargar_tabla(tablas[0], "clave")
    ia = Document()
    ia.add_heading("Carta de término de contrato", 1)
    p = ia.add_paragraph("Estimado ")
    p.add_run("[PERSO").bold = True                  # etiqueta partida en dos fragmentos
    p.add_run("NA_1]").bold = True
    p.add_run(":")
    ia.add_paragraph("Por medio de la presente, [ORGANIZACION_1] (RUT [RUT_3]) le informa "
                     "que el contrato del inmueble ubicado en [DIRECCION_1], Providencia, termina.")
    ia.add_paragraph("Saluda atentamente, PERSONA_2.")
    entrada = str(tmp_path / "respuesta_ia.docx")
    ia.save(entrada)
    out, rev = revertir([entrada], tabla, str(tmp_path))
    texto = "\n".join(x.text for x in Document(out[0].salida).paragraphs)
    assert "Estimado Juan Pérez Soto:" in texto
    assert "Constructora Los Andes SpA" in texto and "Avenida Los Leones 1234" in texto
    assert "María José González Rojas." in texto
    assert not rev.desconocidas
