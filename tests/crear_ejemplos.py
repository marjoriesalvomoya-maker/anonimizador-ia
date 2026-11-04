"""Genera documentos de ejemplo con datos chilenos ficticios para probar el anonimizador."""
import os
import sys

import pymupdf as fitz
import openpyxl
from docx import Document
from openpyxl.comments import Comment

PARRAFO_1 = ("En Santiago, a 4 de noviembre de 2026, comparecen don Juan Pérez Soto, RUT 12.345.678-5, "
             "domiciliado en Avenida Los Leones 1234, depto. 502, Providencia, teléfono +56 9 8765 4321, "
             "correo juan.perez@gmail.com, en adelante el arrendatario; y Constructora Los Andes SpA, "
             "RUT 76.543.210-3, representada por doña María José González Rojas, en adelante la arrendadora.")
PARRAFO_2 = ("El Sr. Pérez pagará la renta mediante transferencia a la cuenta corriente N° 0012345678 "
             "del Banco Santander. Estacionamiento para el vehículo patente BBCL-12.")
PARRAFO_3 = ("Cualquier controversia será conocida por el Juzgado de Letras de Talagante. "
             "La Sra. González firmará en representación de la sociedad.")


def crear_docx(ruta):
    d = Document()
    d.core_properties.author = "María José González Rojas"
    d.core_properties.title = "Contrato Juan Pérez Soto"
    d.sections[0].header.paragraphs[0].text = "Constructora Los Andes SpA — Confidencial"
    d.add_heading("CONTRATO DE ARRENDAMIENTO", 1)
    p = d.add_paragraph()
    # El nombre partido en varios fragmentos con formato distinto
    p.add_run("En Santiago, comparecen don ")
    p.add_run("Juan ").bold = True
    p.add_run("Pérez").italic = True
    p.add_run(" Soto, RUT 12.345.678-5, ya individualizado.")
    d.add_paragraph(PARRAFO_1)
    d.add_paragraph(PARRAFO_2)
    t = d.add_table(rows=2, cols=3)
    for c, v in zip(t.rows[0].cells, ["Nombre", "RUT", "Teléfono"]):
        c.text = v
    for c, v in zip(t.rows[1].cells, ["María José González Rojas", "9.876.543-3", "+56 2 2345 6789"]):
        c.text = v
    par = d.add_paragraph(PARRAFO_3)
    try:
        d.add_comment(par.runs, text="Revisar con Juan Pérez Soto", author="Pedro Rojas", initials="PR")
    except AttributeError:
        pass
    d.save(ruta)


def crear_xlsx(ruta):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.append(["Nombre", "RUT", "Email", "Teléfono", "Comuna", "Monto"])
    ws.append(["Juan Pérez Soto", "12.345.678-5", "juan.perez@gmail.com", 987654321, "Providencia", 450000])
    ws.append(["María José González Rojas", "9.876.543-3", "mjgonzalez@losandes.cl", "+56 9 1234 5678",
               "Talagante", 1200000])
    ws.append(["Total", None, None, None, None, "=SUM(F2:F3)"])
    ws["A2"].comment = Comment("Cliente preferente, contacto de Pedro Rojas", "Pedro Rojas")
    wb.properties.creator = "Pedro Rojas"
    wb.save(ruta)


def crear_pdf(ruta):
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for texto in ["CONTRATO DE ARRENDAMIENTO", PARRAFO_1, PARRAFO_2, PARRAFO_3]:
        rect = fitz.Rect(72, y, 540, y + 160)
        page.insert_textbox(rect, texto, fontsize=10, fontname="helv")
        y += 120 if len(texto) > 100 else 30
    doc.set_metadata({"author": "María José González Rojas", "title": "Contrato Juan Pérez"})
    doc.save(ruta)


if __name__ == "__main__":
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "ejemplos"
    os.makedirs(carpeta, exist_ok=True)
    crear_docx(os.path.join(carpeta, "contrato.docx"))
    crear_xlsx(os.path.join(carpeta, "clientes.xlsx"))
    crear_pdf(os.path.join(carpeta, "contrato.pdf"))
    with open(os.path.join(carpeta, "notas.txt"), "w", encoding="utf-8") as f:
        f.write(PARRAFO_1 + "\n\n" + PARRAFO_2 + "\n")
    print("Ejemplos creados en", carpeta)
