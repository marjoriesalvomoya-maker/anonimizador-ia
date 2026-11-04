# Anonimizador IA

Aplicación de escritorio para **Windows y Mac** que oculta los datos personales de tus documentos antes de entregárselos a una IA (ChatGPT, Claude, Gemini u otra), y después **restaura los datos reales** en lo que la IA te devuelva.

Todo ocurre en tu computador. Ningún documento ni dato se envía a internet.

---

## Cómo funciona

```
 contrato.docx ──► [Anonimizar] ──► contrato_anonimizado.docx  ──► se lo pasas a la IA
                        │
                        └──────► contrato_anonimizado.tabla  (cifrada, queda en tu equipo)

 respuesta_ia.docx ─┐
 (o texto del chat) ├──► [Revertir] + tabla + contraseña ──► respuesta_ia_revertido.docx
                    ┘
```

1. **Anonimizar.** Cada dato sensible se reemplaza por una etiqueta: `[PERSONA_1]`, `[RUT_2]`, `[ORGANIZACION_1]`… La misma persona recibe siempre la misma etiqueta (también si después aparece solo por su apellido o en MAYÚSCULAS), así la IA entiende quién es quién.
2. **Trabajar con la IA.** Le entregas el archivo `_anonimizado`. Usa el botón **«Copiar instrucción para la IA»** y pega ese texto junto al documento: le pide conservar las etiquetas tal cual.
3. **Revertir.** En la pestaña *Revertir* abres la tabla con tu contraseña y:
   - **A)** arrastras el documento que generó la IA (Word, Excel, PowerPoint, PDF o texto), **aunque sea un documento nuevo** escrito por ella; o
   - **B)** pegas la respuesta del chat y copias el resultado.

La reversión tolera los cambios típicos que hacen las IA: `PERSONA_1`, `[Persona 1]`, `**[PERSONA_1]**`, `\[PERSONA\_1\]`, `(PERSONA_1)`, etiquetas partidas entre fragmentos con distinto formato, etc. Si la IA inventa una etiqueta que no existe (p. ej. `[PERSONA_9]`), se deja tal cual y se te avisa.

## Qué se anonimiza

| Categoría | Ejemplos | Cómo se detecta |
|---|---|---|
| Identificadores chilenos | RUT (con dígito verificador válido), teléfonos fijos y móviles, patentes (nuevas y antiguas), calle y número | Reglas |
| Personas | Nombres y apellidos, también en MAYÚSCULAS y tras «don», «doña», «Sr.», «Sra.» | Reglas + modelo de lenguaje local |
| Contacto y finanzas | Emails, tarjetas (validación Luhn), cuentas bancarias | Reglas |
| Organizaciones y lugares específicos | Empresas (SpA, Ltda., S.A.…), bancos, fundos, villas | Reglas + modelo |

**Se mantienen siempre:** las 346 comunas, ciudades, regiones y países, y las instituciones públicas (tribunales, juzgados, ministerios, municipalidades, SII, Fonasa, etc.). Así la IA conserva el contexto geográfico y legal. En una dirección se oculta la calle y el número, pero la comuna queda: `[DIRECCION_1], Providencia`.

**Tus listas** (se recuerdan entre usos):
- *Anonimizar siempre*: nombres de clientes, proyectos o tu propia empresa.
- *Nunca anonimizar*: palabras que el detector marcó por error.

## Formatos

| Formato | Anonimizar | Revertir | Notas |
|---|---|---|---|
| Word `.docx` | ✔ | ✔ | Conserva el formato. Incluye encabezados, pies, tablas, notas, comentarios y control de cambios. Borra autor y nombres de quienes comentaron. |
| Excel `.xlsx` | ✔ | ✔ | Celdas, comentarios y teléfonos guardados como número. Las fórmulas no se tocan. |
| PowerPoint `.pptx` | ✔ | ✔ | Diapositivas y notas. |
| PDF | ✔ | ✔ | Redacción real: el dato se elimina del archivo, no solo se tapa. Además se genera **una versión Word** (`_anonimizado_texto.docx`) en orden de lectura, que es la mejor opción para la IA. |
| Texto `.txt` `.md` `.csv` | ✔ | ✔ | Útil para guardar respuestas del chat. |

Los formatos antiguos (`.doc`, `.xls`, `.ppt`) deben guardarse primero como `.docx`, `.xlsx` o `.pptx`.

## La tabla y su contraseña

- La tabla (`.tabla`) es la **llave** para revertir. Está cifrada con tu contraseña (PBKDF2-SHA256 con 600.000 iteraciones + cifrado autenticado Fernet).
- **No compartas la tabla** con la IA ni con terceros.
- La contraseña no se guarda en ninguna parte: si la olvidas, no hay forma de recuperar la tabla.
- Con «Usar una sola tabla para todos los documentos», un lote completo (p. ej. todos los documentos de un caso) comparte etiquetas: `[PERSONA_1]` es la misma persona en todos.

---

## Instalación

### Opción 1 — Instaladores automáticos con GitHub (recomendada, sin instalar Python)

1. Crea un repositorio en GitHub y sube esta carpeta.
2. Ve a la pestaña **Actions → Construir instaladores → Run workflow**.
3. Al terminar (unos 15 minutos), descarga en **Artifacts**:
   - `AnonimizadorIA-Windows` → `AnonimizadorIA-Instalador.exe`
   - `AnonimizadorIA-Mac-AppleSilicon` (M1/M2/M3/M4) o `AnonimizadorIA-Mac-Intel` → `.dmg`

### Opción 2 — Construir el instalador en tu propio equipo

Necesitas **Python 3.12** de [python.org](https://www.python.org/downloads/) (en Windows marca *«Add python.exe to PATH»*).

- **Windows:** doble clic en `construir_windows.bat`. Si además instalas [Inno Setup 6](https://jrsoftware.org/isinfo.php), genera `salida\AnonimizadorIA-Instalador.exe`; si no, deja el programa listo en `dist\AnonimizadorIA\`.
- **Mac:** en Terminal, `bash construir_mac.sh`. Genera `salida/AnonimizadorIA-Mac-arm64.dmg` (o `x86_64`).

### Opción 3 — Usarlo sin empaquetar

Con Python 3.12 instalado: doble clic en `ejecutar_windows.bat` (Windows) o `ejecutar_mac.command` (Mac). La primera vez descarga lo necesario (requiere internet); después funciona sin conexión.

### Primera apertura en Mac

La app no está firmada por Apple. La primera vez: **clic derecho sobre «Anonimizador IA» → Abrir → Abrir**. Si macOS insiste en que «está dañada», en Terminal:
```
xattr -dr com.apple.quarantine "/Applications/Anonimizador IA.app"
```

---

## Uso por línea de comandos (opcional)

```bash
python -m anonimizador anonimizar contrato.docx anexos/ --salida resultados/
python -m anonimizador revertir respuesta_ia.docx --tabla resultados/lote_anonimizado_20261104-1700.tabla
python -m anonimizador revertir-texto --tabla contrato_anonimizado.tabla < respuesta.txt
python -m anonimizador instruccion
```
Con el programa instalado, los mismos comandos funcionan con `AnonimizadorIA.exe anonimizar ...`.

## Limitaciones conocidas

- **Revisa siempre el resultado antes de enviarlo.** Ningún detector automático es perfecto; usa las listas para corregir.
- Un **apellido suelto** al inicio de una oración solo se oculta si ese apellido aparece en un nombre completo del mismo documento.
- Al revertir, una mención parcial («la Sra. González») se restaura con el nombre completo («la Sra. María José González Rojas»).
- **PDF escaneados** (imágenes): no se anonimizan; la app avisa cuando un PDF casi no tiene texto.
- En el PDF anonimizado la etiqueta ocupa el espacio del dato original, por lo que a veces se ve con letra pequeña. Para la IA usa la versión Word que se genera junto al PDF.
- No se anonimizan imágenes, firmas escaneadas, logos ni texto dentro de gráficos incrustados como imagen.

## Para desarrolladores

```
anonimizador/
  detector.py      reglas (RUT, teléfonos, patentes, direcciones, empresas...) + spaCy
  lugares.py       comunas, regiones y países que se conservan
  seudonimos.py    tabla de correspondencias y cifrado
  motor.py         Anonimizador (datos → etiquetas) y Reversor (etiquetas → datos)
  formatos/        ooxml.py (Word/Excel/PowerPoint), pdf.py, texto.py
  servicio.py      operaciones por lote usadas por la ventana y la CLI
  app.py           ventana (tkinter)
  cli.py           línea de comandos
tests/             pruebas y generador de documentos de ejemplo
```

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest openpyxl
python -m spacy download es_core_news_md
python -m pytest tests -q
```

**Nota técnica:** `pymupdf` está fijado en 1.26.5 porque las versiones 1.27 y posteriores desplazan el texto que sigue a un dato redactado en el PDF (las letras vecinas quedan tapadas). Antes de actualizarlo, corre las pruebas y revisa visualmente un PDF anonimizado.

Para mayor precisión en nombres puedes usar el modelo grande: `python -m spacy download es_core_news_lg` y cambiar `modelo` en `servicio.Opciones` (agrega ~500 MB al instalador).
