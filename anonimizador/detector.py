"""Detección de datos sensibles: reglas precisas + modelo de lenguaje local (spaCy)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .lugares import es_lugar_protegido, normalizar

# --------------------------------------------------------------------------
# Tipos y categorías
# --------------------------------------------------------------------------
CATEGORIAS = {
    "chile": ("Identificadores chilenos (RUT, teléfonos, patentes, direcciones)",
              ["RUT", "TELEFONO", "PATENTE", "DIRECCION"]),
    "personas": ("Nombres de personas", ["PERSONA"]),
    "contacto": ("Contacto y finanzas (emails, tarjetas, cuentas)", ["EMAIL", "TARJETA", "CUENTA"]),
    "organizaciones": ("Organizaciones y lugares específicos", ["ORGANIZACION", "LUGAR"]),
}
TODOS_LOS_TIPOS = [t for _, (_, tipos) in CATEGORIAS.items() for t in tipos] + ["DATO"]

PRIORIDAD_FUENTE = {"usuario": 3, "regla": 2, "modelo": 1}


@dataclass(frozen=True)
class Entidad:
    inicio: int
    fin: int
    tipo: str
    texto: str
    fuente: str  # "usuario" | "regla" | "modelo"


# --------------------------------------------------------------------------
# Validadores
# --------------------------------------------------------------------------
def rut_valido(rut: str) -> bool:
    limpio = re.sub(r"[^0-9kK]", "", rut).upper()
    if len(limpio) < 2:
        return False
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit() or int(cuerpo) < 100000:
        return False
    suma, mult = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * mult
        mult = 2 if mult == 7 else mult + 1
    r = 11 - suma % 11
    esperado = "0" if r == 11 else "K" if r == 10 else str(r)
    return dv == esperado


def luhn_valido(numero: str) -> bool:
    digitos = [int(c) for c in numero if c.isdigit()]
    if not 13 <= len(digitos) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digitos)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# --------------------------------------------------------------------------
# Reglas
# --------------------------------------------------------------------------
_MAY = "A-ZÁÉÍÓÚÑÜ"
_PAL = rf"[{_MAY}0-9][\wÁÉÍÓÚÑÜáéíóúñü.'´’-]*"
_CONEC = r"(?:de|del|la|las|los|el|y|San|Santa)"
# Palabra de nombre propio: "Pérez", "PÉREZ", "O'Higgins", "Fuentes-Alba"
_NOMBRE = rf"(?:[{_MAY}][a-záéíóúñü'´’-]+|[{_MAY}][{_MAY}'´’-]+)(?![\w])"
_CONEC_NOMBRE = r"(?:de|del|de\s+la|de\s+los|y|DE|DEL|DE\s+LA|DE\s+LOS|Y)"

REGLAS = [
    ("RUT", re.compile(
        r"(?<![\w.])(?:\d{1,2}\.\d{3}\.\d{3}|\d{7,8})\s?-\s?[\dkK](?![\w])"), rut_valido),
    ("EMAIL", re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), None),
    ("TARJETA", re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"), luhn_valido),
    ("TELEFONO", re.compile(
        r"(?<![\w$+.,])(?:\+\s?56[\s.-]?|\(?56\)?[\s.-]?)?"
        r"(?:\(?9\)?[\s.-]?\d{4}[\s.-]?\d{4}"
        r"|\(?2\)?[\s.-]?\d{4}[\s.-]?\d{4}"
        r"|\(?[3-7]\d\)?[\s.-]?\d{3}[\s.-]?\d{4})(?![\d])"), None),
    ("CUENTA", re.compile(
        r"(?i)\b(?:cuenta|cta\.?)\s+(?:corriente|vista|rut|de\s+ahorros?|bancaria)?\s*"
        r"(?:n[°º.o]?\s*|número\s*|nro\.?\s*|#\s*)?:?\s*(\d[\d-]{5,18}\d)"), None),
    ("PATENTE", re.compile(
        r"(?<![\w-])(?:[BCDFGHJKLPRSTVWXYZ]{4}[-·\s]?\d{2}|[A-Z]{2}[-·]\d{4})(?![\w-])"), None),
    ("DIRECCION", re.compile(
        rf"\b(?:[Cc]alle|[Aa]venida|[Aa]vda\.?|[Aa]v\.?|[Pp]asaje|[Pp]je\.?|[Cc]amino|[Dd]iagonal|"
        rf"[Pp]aseo|[Pp]arcela|[Ll]ote|[Ss]itio|[Hh]ijuela)\s+{_PAL}(?:\s+(?:{_CONEC}|{_PAL}))*?"
        rf",?\s+(?:[Nn][°º.ro]{{0,2}}\s*|#\s*)?\d{{1,5}}[A-Za-z]?"
        rf"(?:\s*,?\s*(?:[Dd]epto\.?|[Dd]epartamento|[Dd]pto\.?|[Oo]ficina|[Oo]f\.|[Cc]asa|"
        rf"[Bb]lock|[Tt]orre|[Ll]ocal)\s*[\w-]+)*"), None),
    # Nombre tras tratamiento: "don Juan Pérez", "doña MARÍA JOSÉ GONZÁLEZ", "Sr. Pérez"
    ("PERSONA", re.compile(
        rf"(?:\b(?:[Dd]on|DON|[Dd]oña|DOÑA|[Ss]r\.?|SR\.?|[Ss]ra\.?|SRA\.?|[Ss]rta\.?|[Ss]eñor|"
        rf"[Ss]eñora|SEÑOR|SEÑORA|[Ss]eñorita|[Dd]r\.|[Dd]ra\.)\s+)"
        rf"({_NOMBRE}(?:\s+(?:{_CONEC_NOMBRE}\s+)?{_NOMBRE}){{0,4}})"), "persona"),
    # Nombre seguido de su identificación: "JUAN PÉREZ SOTO, RUT ...", "Ana Soto, chilena, ..."
    ("PERSONA", re.compile(
        rf"(?<![\w])({_NOMBRE}(?:\s+(?:{_CONEC_NOMBRE}\s+)?{_NOMBRE}){{1,5}})"
        rf"(?=\s*,?\s*(?:(?i:rut|r\.u\.t\.?|run|c\.?\s?i\.|c[ée]dula|chilen[oa]|"
        rf"extranjer[oa]|venezolan[oa]|peruan[oa]|argentin[oa]|colombian[oa]|boliviano|boliviana|"
        rf"haitian[oa]|mayor de edad|soltero|soltera|casad[oa]|divorciad[oa]|viud[oa])\b))"),
     "persona"),
    ("ORGANIZACION", re.compile(
        rf"\b(?:[{_MAY}0-9&][\w&.'’-]*\s+(?:(?:de|del|la|los|las|y)\s+)?){{1,6}}"
        rf"(?:S\.?\s?A\.?(?=[\s,;:)]|$)|SpA\b|S\.p\.A\.|Ltda\.?|Limitada\b|E\.?I\.?R\.?L\.?|"
        rf"S\.?A\.?C\.?(?=[\s,;:)]|$)|y\s+C[íi]a\.?)"), None),
]

# Palabras que delatan una organización aunque el modelo diga "lugar".
PREFIJOS_ORG = {
    "constructora", "inmobiliaria", "sociedad", "empresa", "empresas", "comercial",
    "comercializadora", "servicios", "inversiones", "banco", "fundacion", "corporacion",
    "asociacion", "cooperativa", "clinica", "colegio", "universidad", "instituto",
    "transportes", "agricola", "distribuidora", "importadora", "exportadora", "consultora",
    "ingenieria", "minera", "compania", "cia", "laboratorio", "laboratorios", "isapre", "afp",
    "holding", "grupo", "estudio", "agencia", "farmacia", "farmacias", "automotora", "viña",
    "supermercado", "supermercados", "club", "sindicato", "junta", "condominio", "edificio",
}

# Instituciones públicas: se mantienen (no son datos personales y dan contexto).
INSTITUCIONES_PUBLICAS = re.compile(
    r"^(?:el |la |los |las )?(?:i\.?\s*|ilustre\s+|excelentisima\s+|ilustrisima\s+)?"
    r"(?:tribunal|juzgado|corte|ministerio|subsecretaria|municipalidad|fiscalia|defensoria|"
    r"servicio de|superintendencia|contraloria|tesoreria|carabineros|policia|registro civil|"
    r"conservador de bienes raices|direccion del trabajo|direccion general|inspeccion del trabajo|"
    r"gobierno|congreso|senado|camara de diputados|poder judicial|presidencia|seremi|"
    r"intendencia|delegacion presidencial|gobernacion|consejo de defensa del estado|"
    r"instituto de prevision social|instituto nacional|banco central|banco estado|bancoestado|"
    r"comision para el mercado financiero|ministerio publico|"
    r"sii|sernac|fonasa|ine|cmf|tgr|pdi|ips|sag|serviu|minvu|mop|cde|csj)\b")

HONORIFICOS = re.compile(
    r"^(?:(?:el|la|los|las)\s+)?(?:(?:sr|sra|srta|sres|sras|dr|dra|don|doña|dona|señor|señora|"
    r"señorita|abogado|abogada|ing|lic|prof|profesor|profesora)\.?\s+)+", re.I)

_CONECTORES_NOMBRE = {"de", "del", "la", "los", "las", "y"}

# Cargos y roles que siguen a "Sr./Sra." pero no son nombres.
ROLES = {
    "juez", "jueza", "ministro", "ministra", "notario", "notaria", "presidente", "presidenta",
    "secretario", "secretaria", "fiscal", "alcalde", "alcaldesa", "gerente", "director",
    "directora", "rector", "rectora", "comprador", "compradora", "vendedor", "vendedora",
    "arrendador", "arrendadora", "arrendatario", "arrendataria", "demandante", "demandado",
    "demandada", "conservador", "receptor", "receptora", "abogado", "abogada", "perito",
    "profesor", "profesora", "doctor", "doctora", "subrogante", "suplente", "relator",
    "relatora", "actuario", "intendente", "gobernador", "senador", "diputado", "diputada",
    "usted", "ud", "uds", "mandante", "mandatario", "trabajador", "trabajadora", "empleador",
    "empleadora", "cliente", "paciente", "titular", "deudor", "deudora", "acreedor", "aval",
    "fiador", "propietario", "propietaria", "representante", "apoderado", "apoderada",
}

# Palabras que el modelo a veces confunde con entidades.
NO_ENTIDADES = {
    "rut", "run", "dni", "rol", "rit", "ruc", "fono", "tel", "telefono", "email", "correo",
    "mail", "n", "no", "nro", "cel", "celular", "fax", "cc", "atte", "anexo", "cláusula",
    "clausula", "considerando", "articulo", "inciso", "contrato", "señor", "señora",
    "nombre", "nombres", "apellido", "apellidos", "direccion", "domicilio", "comuna", "ciudad",
    "region", "fecha", "firma", "monto", "total", "subtotal", "cargo", "profesion", "nacionalidad",
    "estado civil", "edad", "giro", "razon social", "empresa", "rol", "cedula", "identidad",
    "pagina", "anexo", "observaciones", "detalle", "descripcion", "cantidad", "valor", "precio",
}

# Palabras con mayúscula que no son nombres (inicio de oración, títulos de documentos).
PALABRAS_COMUNES = {
    "en", "el", "la", "los", "las", "lo", "por", "con", "para", "del", "de", "y", "e", "que",
    "se", "su", "sus", "a", "al", "un", "una", "uno", "comparece", "comparecen", "entre", "segun",
    "según", "ante", "como", "este", "esta", "estos", "estas", "dicho", "dicha", "ademas", "asimismo",
    "contrato", "arrendamiento", "arriendo", "compraventa", "mandato", "poder", "escritura",
    "declaracion", "demanda", "acta", "informe", "certificado", "finiquito", "clausula",
    "sociedad", "carta", "solicitud", "resolucion", "sentencia", "querella", "recurso",
    "notificacion", "propuesta", "cotizacion", "factura", "boleta", "liquidacion", "presente",
    "primero", "segundo", "tercero", "cuarto", "quinto", "otrosi", "por tanto", "fecha",
    "don", "doña", "dona", "sr", "sra", "srta", "sres", "sras", "señor", "señora", "señorita",
    "dr", "dra", "estimado", "estimada", "atte", "saluda", "firma", "firmado",
}


def _validar_persona(texto, ini, fin):
    """Ajusta y valida un nombre encontrado por reglas. Devuelve (ini, fin) o None."""
    fragmento = texto[ini:fin]
    palabras = fragmento.split()
    # quitar palabras comunes al inicio ("En Santiago", "Comparece JUAN...")
    while palabras and normalizar(palabras[0]).strip(".,:;") in PALABRAS_COMUNES:
        ini = texto.index(palabras[0], ini) + len(palabras[0])
        while ini < fin and texto[ini].isspace():
            ini += 1
        palabras.pop(0)
    if not palabras:
        return None
    norm = [normalizar(w).strip(".,:;") for w in palabras]
    if norm[0] in ROLES or norm[0] in PREFIJOS_ORG or norm[-1] in _CONECTORES_NOMBRE:
        return None
    if any(w in PALABRAS_COMUNES and w not in _CONECTORES_NOMBRE for w in norm):
        return None
    if all(w in NO_ENTIDADES or w in ROLES for w in norm):
        return None
    if es_lugar_protegido(texto[ini:fin]):
        return None
    return ini, fin


_MAPA_NER = {"PER": "PERSONA", "ORG": "ORGANIZACION", "LOC": "LUGAR"}


class Detector:
    """Encuentra entidades sensibles en texto."""

    def __init__(self, tipos_activos=None, excluir=(), siempre=(),
                 modelo: str = "es_core_news_md", usar_modelo: bool = True):
        self.tipos = set(tipos_activos or TODOS_LOS_TIPOS) | {"DATO"}
        self.excluir = {normalizar(x) for x in excluir if x.strip()}
        self.siempre = sorted({x.strip() for x in siempre if x.strip()}, key=len, reverse=True)
        self._re_siempre = None
        if self.siempre:
            partes = [re.escape(x).replace(r"\ ", r"\s+") for x in self.siempre]
            self._re_siempre = re.compile(rf"(?<!\w)(?:{'|'.join(partes)})(?!\w)", re.I)
        self.nlp = None
        self.aviso = None
        necesita_modelo = self.tipos & {"PERSONA", "ORGANIZACION", "LUGAR"}
        if usar_modelo and necesita_modelo:
            self.nlp, self.aviso = cargar_modelo(modelo)

    # ---- API -------------------------------------------------------------
    def detectar(self, texto: str) -> list[Entidad]:
        return self.detectar_lote([texto])[0]

    def detectar_lote(self, textos: list[str]) -> list[list[Entidad]]:
        resultados = [self._reglas(t) for t in textos]
        if self.nlp is not None:
            dudosas_por_texto = []
            docs = self.nlp.pipe((t[:200000] for t in textos), batch_size=64)
            for i, doc in enumerate(docs):
                ents, dudosas = self._modelo(doc)
                resultados[i].extend(ents)
                dudosas_por_texto.append(dudosas)
            # Partes de nombres completos vistos en todo el lote (reglas o modelo)
            partes = set()
            for r in resultados:
                for e in r:
                    if e.tipo == "PERSONA" and len(e.texto.split()) >= 2:
                        partes |= {normalizar(w) for w in e.texto.split()}
            for i, dudosas in enumerate(dudosas_por_texto):
                resultados[i].extend(d for d in dudosas if normalizar(d.texto) in partes)
        return [self._resolver(r) for r in resultados]

    # ---- internas --------------------------------------------------------
    def _reglas(self, texto: str) -> list[Entidad]:
        ents = []
        if self._re_siempre:
            for m in self._re_siempre.finditer(texto):
                ents.append(Entidad(m.start(), m.end(), "DATO", m.group(0), "usuario"))
        for tipo, patron, validador in REGLAS:
            if tipo not in self.tipos:
                continue
            for m in patron.finditer(texto):
                g = 1 if patron.groups else 0
                valor = m.group(g)
                ini, fin = m.start(g), m.end(g)
                if validador == "persona":
                    r = _validar_persona(texto, ini, fin)
                    if r is None:
                        continue
                    ini, fin = r
                elif validador and not validador(valor):
                    continue
                if tipo == "ORGANIZACION":
                    ini, fin = self._recortar_org(texto, ini, fin)
                    if fin <= ini:
                        continue
                ents.append(Entidad(ini, fin, tipo, texto[ini:fin], "regla"))
        return [e for e in ents if not self._excluida(e)]

    @staticmethod
    def _recortar_org(texto, ini, fin):
        # Quita artículos/preposiciones iniciales ("La Constructora..." se conserva entera,
        # pero "de Constructora X SpA" pierde el "de").
        fragmento = texto[ini:fin]
        m = re.match(r"(?:(?:de|del|a|al|con|por|en|para|y|e|entre)\s+)+", fragmento, re.I)
        if m:
            ini += m.end()
        return ini, fin

    def _modelo(self, doc):
        """Devuelve (entidades, dudosas). Las dudosas son palabras sueltas al inicio de
        oración que el modelo marcó como persona; solo se aceptan si coinciden con parte de
        un nombre completo detectado en el mismo documento."""
        ents, dudosas = [], []
        for e in doc.ents:
            if e.label_ == "MISC":
                candidatos = self._desde_misc(doc, e)
            elif e.label_ in _MAPA_NER:
                candidatos = [(e.start_char, e.end_char, _MAPA_NER[e.label_])]
            else:
                continue
            for ini, fin, tipo in candidatos:
                r = self._filtrar(doc, ini, fin, tipo)
                if r is None:
                    continue
                ent, dudosa = r
                (dudosas if dudosa else ents).append(ent)
        return ents, dudosas

    def _desde_misc(self, doc, e):
        """Las entidades MISC suelen mezclar frases con nombres: se rescatan los tramos de
        nombres propios ("Lo vio Pedro Soto en..." -> "Pedro Soto")."""
        out, run = [], []
        for t in list(e) + [None]:
            if t is not None and (t.pos_ == "PROPN" or (run and t.lower_ in _CONECTORES_NOMBRE
                                                         and t.i + 1 < len(doc)
                                                         and doc[t.i + 1].pos_ == "PROPN")):
                run.append(t)
                continue
            if run:
                ini, fin = run[0].idx, run[-1].idx + len(run[-1])
                texto = doc.text[ini:fin]
                previo = doc.text[max(0, ini - 12):ini]
                primera = normalizar(run[0].text)
                if re.search(r"(?:don|doña|sr\.?|sra\.?|srta\.?|señor|señora|dr\.?|dra\.?)\s*$",
                             previo, re.I):
                    out.append((ini, fin, "PERSONA"))
                elif primera in PREFIJOS_ORG:
                    out.append((ini, fin, "ORGANIZACION"))
                elif len(texto.split()) >= 2 and all(w[0].isupper() for w in texto.split()
                                                     if w.lower() not in _CONECTORES_NOMBRE):
                    out.append((ini, fin, "PERSONA"))
                run = []
        return out

    def _filtrar(self, doc, ini, fin, tipo):
        texto = doc.text[ini:fin]
        m = HONORIFICOS.match(texto)             # "La Sra. González" -> persona "González"
        if m:
            ini += m.end()
            texto = texto[m.end():]
            tipo = "PERSONA"
        while texto and texto[-1] in " .,;:)»\"'”":
            texto, fin = texto[:-1], fin - 1
        while texto and texto[0] in " («\"'“":
            texto, ini = texto[1:], ini + 1
        if len(texto) < 3 or not texto[0].isupper() or "\n" in texto:
            return None
        palabras = [normalizar(w).strip(".,;:") for w in texto.split()]
        if normalizar(texto) in NO_ENTIDADES or all(w in NO_ENTIDADES for w in palabras):
            return None
        primera = normalizar(texto.split()[0])
        if tipo in ("LUGAR", "PERSONA") and primera in PREFIJOS_ORG:
            tipo = "ORGANIZACION"
        if tipo == "PERSONA" and (any(c.isdigit() for c in texto) or primera in ROLES):
            return None
        if tipo in ("LUGAR", "ORGANIZACION"):
            if es_lugar_protegido(texto) or INSTITUCIONES_PUBLICAS.match(normalizar(texto)):
                return None
            if texto.isupper():                     # títulos ("ARRENDAMIENTO", "CONTRATO DE ...")
                return None
        if tipo == "PERSONA" and texto.isupper() and len(texto.split()) == 1:
            return None
        if es_lugar_protegido(texto) and len(texto.split()) == 1:
            return None                                        # "Santiago" a secas
        if tipo not in self.tipos:
            return None
        ent = Entidad(ini, fin, tipo, texto, "modelo")
        if self._excluida(ent):
            return None
        # Palabra suelta al inicio de oración: dudosa ("Vehículo", "Pago").
        antes = doc.text[:ini].rstrip(" \t\"'“«(")
        inicio_oracion = not antes or antes[-1] in ".!?:;\n•-–—"
        dudosa = len(texto.split()) == 1 and inicio_oracion
        return ent, dudosa

    def _excluida(self, e: Entidad) -> bool:
        return e.fuente != "usuario" and normalizar(e.texto) in self.excluir

    @staticmethod
    def _resolver(ents: list[Entidad]) -> list[Entidad]:
        """Elimina solapamientos: gana la fuente más confiable y luego la más larga."""
        orden = sorted(ents, key=lambda e: (-PRIORIDAD_FUENTE[e.fuente], -(e.fin - e.inicio)))
        elegidas: list[Entidad] = []
        for e in orden:
            if all(e.fin <= o.inicio or e.inicio >= o.fin for o in elegidas):
                elegidas.append(e)
        return sorted(elegidas, key=lambda e: e.inicio)


# --------------------------------------------------------------------------
_CACHE_MODELOS: dict = {}


def cargar_modelo(nombre: str = "es_core_news_md"):
    """Carga spaCy una sola vez. Devuelve (nlp | None, aviso | None)."""
    if nombre in _CACHE_MODELOS:
        return _CACHE_MODELOS[nombre]
    try:
        import spacy
        candidatos = [nombre] + [m for m in ("es_core_news_lg", "es_core_news_md", "es_core_news_sm")
                                 if m != nombre]
        for cand in candidatos:
            try:
                nlp = spacy.load(cand, disable=["parser", "lemmatizer"])
                aviso = None if cand == nombre else f"Se usó el modelo {cand} en lugar de {nombre}."
                _CACHE_MODELOS[nombre] = (nlp, aviso)
                return nlp, aviso
            except OSError:
                continue
        res = (None, "No se encontró el modelo de lenguaje en español: solo se usarán reglas "
                     "(los nombres de personas y organizaciones no se detectarán automáticamente).")
    except ImportError:
        res = (None, "spaCy no está instalado: solo se usarán reglas.")
    _CACHE_MODELOS[nombre] = res
    return res
