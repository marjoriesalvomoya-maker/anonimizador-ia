"""Tabla de correspondencias: dato real <-> etiqueta, consistente en todo el documento o lote."""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime

from .lugares import normalizar

VERSION_FORMATO = 1
_CONECTORES = {"de", "del", "la", "las", "los", "y", "e", "van", "von", "da", "di"}


def clave_valor(tipo: str, texto: str) -> str:
    """Forma canónica para reconocer el mismo dato escrito de distintas maneras."""
    if tipo in ("RUT",):
        return re.sub(r"[^0-9k]", "", texto.lower())
    if tipo in ("TELEFONO",):
        d = re.sub(r"\D", "", texto)
        return d[2:] if d.startswith("56") and len(d) > 9 else d
    if tipo in ("TARJETA", "CUENTA"):
        return re.sub(r"\D", "", texto)
    if tipo == "PATENTE":
        return re.sub(r"[^A-Z0-9]", "", texto.upper())
    return normalizar(texto).strip(" .,;:")


def _tokens_nombre(clave: str) -> set:
    return {t for t in clave.replace(".", " ").split() if t not in _CONECTORES and len(t) > 1}


class TablaSeudonimos:
    def __init__(self):
        self.entradas: dict[str, dict] = {}      # etiqueta -> {tipo, original, variantes}
        self._indice: dict[str, str] = {}        # "TIPO|clave" -> etiqueta
        self.contadores: dict[str, int] = {}
        self.creada = datetime.now().isoformat(timespec="seconds")

    # ------------------------------------------------------------------
    def registrar(self, tipo: str, texto: str) -> str:
        texto = " ".join(texto.split())
        clave = clave_valor(tipo, texto)
        if not clave:
            return ""
        idx = f"{tipo}|{clave}"
        etiqueta = self._indice.get(idx)
        if etiqueta is None and tipo == "PERSONA":
            etiqueta = self._vincular_persona(clave)
        if etiqueta is None:
            n = self.contadores.get(tipo, 0) + 1
            self.contadores[tipo] = n
            etiqueta = f"{tipo}_{n}"
            self.entradas[etiqueta] = {"tipo": tipo, "original": texto, "variantes": []}
        self._indice[idx] = etiqueta
        ent = self.entradas[etiqueta]
        if texto not in ent["variantes"]:
            ent["variantes"].append(texto)
        # El "original" que se restaura es la forma más completa vista.
        if tipo == "PERSONA" and len(texto) > len(ent["original"]):
            ent["original"] = texto
        return etiqueta

    def _vincular_persona(self, clave: str):
        """'Pérez' o 'Juan Pérez' se vinculan a 'Juan Pérez Soto' si no hay ambigüedad."""
        nuevos = _tokens_nombre(clave)
        if not nuevos:
            return None
        candidatos = set()
        for idx, et in self._indice.items():
            tipo, c = idx.split("|", 1)
            if tipo != "PERSONA":
                continue
            existentes = _tokens_nombre(c)
            if existentes and (nuevos <= existentes or existentes <= nuevos):
                candidatos.add(et)
        return candidatos.pop() if len(candidatos) == 1 else None

    def formas(self) -> dict[str, str]:
        """Todas las variantes vistas -> etiqueta (para reemplazar en todo el documento)."""
        out = {}
        for et, ent in self.entradas.items():
            for v in ent["variantes"]:
                out[v] = et
        return out

    def original(self, etiqueta: str):
        ent = self.entradas.get(etiqueta)
        return ent["original"] if ent else None

    def __len__(self):
        return len(self.entradas)

    # ------------------------------------------------------------------
    def a_dict(self) -> dict:
        return {"version": VERSION_FORMATO, "creada": self.creada,
                "contadores": self.contadores, "entradas": self.entradas,
                "indice": self._indice}

    @classmethod
    def desde_dict(cls, d: dict) -> "TablaSeudonimos":
        t = cls()
        t.creada = d.get("creada", t.creada)
        t.contadores = dict(d.get("contadores", {}))
        t.entradas = dict(d.get("entradas", {}))
        t._indice = dict(d.get("indice", {}))
        if not t._indice:
            for et, ent in t.entradas.items():
                for v in ent["variantes"]:
                    t._indice[f"{ent['tipo']}|{clave_valor(ent['tipo'], v)}"] = et
        return t


# ----------------------------------------------------------------------
# Guardado cifrado
# ----------------------------------------------------------------------
class ContrasenaIncorrecta(Exception):
    pass


class TablaInvalida(Exception):
    pass


_ITERACIONES = 600_000
EXTENSION_TABLA = ".tabla"


def _derivar_clave(contrasena: str, sal: bytes, iteraciones: int) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=iteraciones)
    return base64.urlsafe_b64encode(kdf.derive(contrasena.encode("utf-8")))


def guardar_tabla(tabla: TablaSeudonimos, ruta: str, contrasena: str | None) -> None:
    contenido = json.dumps(tabla.a_dict(), ensure_ascii=False).encode("utf-8")
    if contrasena:
        from cryptography.fernet import Fernet
        sal = os.urandom(16)
        token = Fernet(_derivar_clave(contrasena, sal, _ITERACIONES)).encrypt(contenido)
        sobre = {"formato": "anonimizador-ia/tabla", "cifrado": True, "kdf": "pbkdf2-sha256",
                 "iteraciones": _ITERACIONES, "sal": base64.b64encode(sal).decode(),
                 "datos": token.decode()}
    else:
        sobre = {"formato": "anonimizador-ia/tabla", "cifrado": False,
                 "datos": json.loads(contenido)}
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sobre, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def tabla_esta_cifrada(ruta: str) -> bool:
    try:
        with open(ruta, encoding="utf-8") as f:
            return bool(json.load(f).get("cifrado"))
    except Exception:
        return False


def cargar_tabla(ruta: str, contrasena: str | None = None) -> TablaSeudonimos:
    try:
        with open(ruta, encoding="utf-8") as f:
            sobre = json.load(f)
    except (OSError, ValueError) as e:
        raise TablaInvalida(f"No se pudo leer la tabla: {e}") from e
    if sobre.get("formato") != "anonimizador-ia/tabla":
        raise TablaInvalida("El archivo no es una tabla del Anonimizador.")
    if sobre.get("cifrado"):
        if not contrasena:
            raise ContrasenaIncorrecta("Esta tabla está protegida: ingresa la contraseña.")
        from cryptography.fernet import Fernet, InvalidToken
        clave = _derivar_clave(contrasena, base64.b64decode(sobre["sal"]),
                               int(sobre.get("iteraciones", _ITERACIONES)))
        try:
            datos = json.loads(Fernet(clave).decrypt(sobre["datos"].encode()))
        except InvalidToken as e:
            raise ContrasenaIncorrecta("Contraseña incorrecta.") from e
    else:
        datos = sobre["datos"]
    return TablaSeudonimos.desde_dict(datos)
