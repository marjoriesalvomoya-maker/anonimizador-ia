"""Ventana principal del Anonimizador IA (tkinter, funciona en Windows y Mac)."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .detector import CATEGORIAS
from .formatos import EXTENSIONES_SOPORTADAS, soportado
from .motor import INSTRUCCION_IA, Reversor
from .seudonimos import (EXTENSION_TABLA, ContrasenaIncorrecta, TablaInvalida, cargar_tabla,
                         tabla_esta_cifrada)
from .servicio import Opciones, anonimizar, crear_detector, revertir

try:  # arrastrar y soltar (opcional)
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:  # noqa: BLE001
    TkinterDnD = None
    DND_FILES = None

ES_MAC = sys.platform == "darwin"
ES_WIN = sys.platform.startswith("win")
TIPOS_ARCHIVO = [("Documentos", " ".join("*" + e for e in EXTENSIONES_SOPORTADAS)),
                 ("Todos los archivos", "*.*")]
MIN_CONTRASENA = 6


# ------------------------------------------------------------------ configuración
def carpeta_config() -> str:
    if ES_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif ES_MAC:
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    ruta = os.path.join(base, "AnonimizadorIA")
    os.makedirs(ruta, exist_ok=True)
    return ruta


def cargar_config() -> dict:
    try:
        with open(os.path.join(carpeta_config(), "config.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def guardar_config(cfg: dict) -> None:
    try:
        with open(os.path.join(carpeta_config(), "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def abrir_en_sistema(ruta: str) -> None:
    try:
        if ES_WIN:
            os.startfile(ruta)  # type: ignore[attr-defined]
        elif ES_MAC:
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except Exception:  # noqa: BLE001
        pass


def rutas_desde_drop(widget, data: str) -> list[str]:
    try:
        return list(widget.tk.splitlist(data))
    except Exception:  # noqa: BLE001
        return [data]


# ------------------------------------------------------------------ widgets
class ListaArchivos(ttk.Frame):
    """Lista de archivos con botones y arrastrar-soltar."""

    def __init__(self, master, texto_vacio: str, alto=6):
        super().__init__(master)
        self.rutas: list[str] = []
        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True)
        self.lista = tk.Listbox(marco, height=alto, activestyle="none", selectmode="extended",
                                relief="solid", borderwidth=1, highlightthickness=0)
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        self.lista.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.texto_vacio = texto_vacio
        botones = ttk.Frame(self)
        botones.pack(fill="x", pady=(6, 0))
        ttk.Button(botones, text="Agregar archivos…", command=self.agregar_dialogo).pack(side="left")
        ttk.Button(botones, text="Quitar", command=self.quitar).pack(side="left", padx=6)
        ttk.Button(botones, text="Limpiar", command=self.limpiar).pack(side="left")
        if TkinterDnD is not None:
            self.lista.drop_target_register(DND_FILES)
            self.lista.dnd_bind("<<Drop>>", lambda e: self.agregar(rutas_desde_drop(self, e.data)))
        self._refrescar()

    def agregar_dialogo(self):
        self.agregar(filedialog.askopenfilenames(title="Elegir documentos", filetypes=TIPOS_ARCHIVO))

    def agregar(self, rutas):
        for r in rutas:
            if os.path.isdir(r):
                for raiz, _, archivos in os.walk(r):
                    for a in sorted(archivos):
                        p = os.path.join(raiz, a)
                        if soportado(p) and p not in self.rutas and not a.startswith("~$"):
                            self.rutas.append(p)
            elif r and r not in self.rutas:
                self.rutas.append(r)
        self._refrescar()

    def quitar(self):
        for i in reversed(self.lista.curselection()):
            if i < len(self.rutas):
                del self.rutas[i]
        self._refrescar()

    def limpiar(self):
        self.rutas.clear()
        self._refrescar()

    def _refrescar(self):
        self.lista.delete(0, "end")
        if not self.rutas:
            self.lista.insert("end", self.texto_vacio)
            self.lista.itemconfig(0, foreground="#888888")
        for r in self.rutas:
            self.lista.insert("end", os.path.basename(r) + ("" if soportado(r) else "  (no soportado)"))


def area_texto(master, alto=4, ancho=30):
    marco = ttk.Frame(master)
    t = tk.Text(marco, height=alto, width=ancho, wrap="word", relief="solid", borderwidth=1,
                highlightthickness=0, undo=True)
    barra = ttk.Scrollbar(marco, orient="vertical", command=t.yview)
    t.configure(yscrollcommand=barra.set)
    t.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    return marco, t


# ------------------------------------------------------------------ aplicación
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cfg = cargar_config()
        self.cola: queue.Queue = queue.Queue()
        self.ocupado = False
        self.detector = None
        self.detector_clave = None
        self.tabla_revertir = None
        self.ultima_carpeta = ""

        root.title(f"Anonimizador IA {__version__}")
        root.minsize(760, 640)
        try:
            root.geometry(self.cfg.get("geometria", "900x760"))
        except tk.TclError:
            root.geometry("900x760")
        self._estilos()

        cabecera = ttk.Frame(root, padding=(16, 12, 16, 4))
        cabecera.pack(fill="x")
        ttk.Label(cabecera, text="Anonimizador IA", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(cabecera, style="Sub.TLabel",
                  text="Oculta datos personales antes de usar una IA y recupéralos después. "
                       "Todo ocurre en este equipo; nada se envía a internet.").pack(anchor="w")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=8)
        self._pestana_anonimizar()
        self._pestana_revertir()

        abajo = ttk.Frame(root, padding=(16, 0, 16, 12))
        abajo.pack(fill="x")
        self.progreso = ttk.Progressbar(abajo, mode="determinate")
        self.progreso.pack(fill="x")
        marco, self.registro = area_texto(abajo, alto=7)
        marco.pack(fill="both", expand=False, pady=(6, 0))
        self.registro.configure(state="disabled", background="#f7f7f7")

        root.protocol("WM_DELETE_WINDOW", self.cerrar)
        root.after(100, self._procesar_cola)
        self.log("Listo. Agrega documentos (Word, Excel, PowerPoint, PDF o texto) para comenzar.")

    # ---- estilo -------------------------------------------------------------
    def _estilos(self):
        st = ttk.Style()
        if ES_WIN and "vista" in st.theme_names():
            st.theme_use("vista")
        elif not ES_MAC and "clam" in st.theme_names():
            st.theme_use("clam")
        fuente = "Segoe UI" if ES_WIN else ("Helvetica Neue" if ES_MAC else "DejaVu Sans")
        self.fuente = fuente
        st.configure("Titulo.TLabel", font=(fuente, 18, "bold"))
        st.configure("Sub.TLabel", foreground="#555555")
        st.configure("Seccion.TLabelframe.Label", font=(fuente, 10, "bold"))
        st.configure("Accion.TButton", font=(fuente, 11, "bold"), padding=(16, 8))
        st.configure("Nota.TLabel", foreground="#666666")

    # ---- pestaña Anonimizar --------------------------------------------------
    def _pestana_anonimizar(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="  1 · Anonimizar  ")
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)

        f_arch = ttk.LabelFrame(tab, text="Documentos", style="Seccion.TLabelframe", padding=8)
        f_arch.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        vacio = ("Arrastra aquí tus documentos o usa «Agregar archivos…»" if TkinterDnD
                 else "Usa «Agregar archivos…» para elegir documentos")
        self.lista_anon = ListaArchivos(f_arch, vacio)
        self.lista_anon.pack(fill="both", expand=True)

        f_cat = ttk.LabelFrame(tab, text="Qué anonimizar", style="Seccion.TLabelframe", padding=8)
        f_cat.grid(row=0, column=1, sticky="nsew")
        guardadas = self.cfg.get("categorias", list(CATEGORIAS))
        self.vars_cat = {}
        for clave, (etiqueta, _) in CATEGORIAS.items():
            v = tk.BooleanVar(value=clave in guardadas)
            self.vars_cat[clave] = v
            ttk.Checkbutton(f_cat, text=etiqueta, variable=v).pack(anchor="w", pady=2)
        ttk.Label(f_cat, style="Nota.TLabel", wraplength=300, justify="left",
                  text="Se mantienen siempre: comunas, ciudades, regiones, países e "
                       "instituciones públicas (tribunales, ministerios, SII…).").pack(anchor="w", pady=(8, 0))

        f_listas = ttk.LabelFrame(tab, text="Tus listas (una entrada por línea)",
                                  style="Seccion.TLabelframe", padding=8)
        f_listas.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        f_listas.columnconfigure(0, weight=1)
        f_listas.columnconfigure(1, weight=1)
        ttk.Label(f_listas, text="Anonimizar siempre (nombres, proyectos, clientes…)").grid(
            row=0, column=0, sticky="w")
        ttk.Label(f_listas, text="Nunca anonimizar (palabras marcadas por error)").grid(
            row=0, column=1, sticky="w", padx=(10, 0))
        m1, self.txt_siempre = area_texto(f_listas, alto=4)
        m2, self.txt_excluir = area_texto(f_listas, alto=4)
        m1.grid(row=1, column=0, sticky="nsew")
        m2.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        self.txt_siempre.insert("1.0", "\n".join(self.cfg.get("siempre", [])))
        self.txt_excluir.insert("1.0", "\n".join(self.cfg.get("excluir", [])))

        f_op = ttk.LabelFrame(tab, text="Opciones", style="Seccion.TLabelframe", padding=8)
        f_op.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        f_op.columnconfigure(1, weight=1)

        ttk.Label(f_op, text="Contraseña de la tabla:").grid(row=0, column=0, sticky="w")
        self.var_pass1 = tk.StringVar()
        self.var_pass2 = tk.StringVar()
        fp = ttk.Frame(f_op)
        fp.grid(row=0, column=1, sticky="w", padx=6)
        ttk.Entry(fp, textvariable=self.var_pass1, show="•", width=22).pack(side="left")
        ttk.Label(fp, text="  Repetir:").pack(side="left")
        ttk.Entry(fp, textvariable=self.var_pass2, show="•", width=22).pack(side="left", padx=(4, 0))
        ttk.Label(f_op, style="Nota.TLabel", wraplength=640, justify="left",
                  text="La necesitarás para revertir. No se guarda en ninguna parte: si la "
                       "olvidas, la tabla no se puede abrir.").grid(row=1, column=1, sticky="w", padx=6)

        ttk.Label(f_op, text="Guardar en:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        fc = ttk.Frame(f_op)
        fc.grid(row=2, column=1, sticky="ew", padx=6, pady=(8, 0))
        fc.columnconfigure(0, weight=1)
        self.var_carpeta = tk.StringVar(value=self.cfg.get("carpeta_salida", ""))
        ttk.Entry(fc, textvariable=self.var_carpeta).grid(row=0, column=0, sticky="ew")
        ttk.Button(fc, text="Elegir…", command=lambda: self._elegir_carpeta(self.var_carpeta)).grid(
            row=0, column=1, padx=(6, 0))
        ttk.Label(f_op, style="Nota.TLabel", text="Vacío = en la misma carpeta de cada documento.").grid(
            row=3, column=1, sticky="w", padx=6)

        self.var_lote = tk.BooleanVar(value=self.cfg.get("tabla_comun", True))
        ttk.Checkbutton(f_op, variable=self.var_lote,
                        text="Usar una sola tabla para todos los documentos (misma persona = misma etiqueta)"
                        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.var_pdfword = tk.BooleanVar(value=self.cfg.get("pdf_a_word", True))
        ttk.Checkbutton(f_op, variable=self.var_pdfword,
                        text="De los PDF, crear también una versión Word (la mejor opción para la IA)"
                        ).grid(row=5, column=0, columnspan=2, sticky="w")

        acciones = ttk.Frame(tab)
        acciones.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.btn_anon = ttk.Button(acciones, text="Anonimizar", style="Accion.TButton",
                                   command=self.ejecutar_anonimizar)
        self.btn_anon.pack(side="left")
        ttk.Button(acciones, text="Copiar instrucción para la IA",
                   command=self.copiar_instruccion).pack(side="left", padx=8)
        self.btn_abrir = ttk.Button(acciones, text="Abrir carpeta de resultados", state="disabled",
                                    command=lambda: abrir_en_sistema(self.ultima_carpeta))
        self.btn_abrir.pack(side="left")
        tab.rowconfigure(0, weight=1)

    # ---- pestaña Revertir ----------------------------------------------------
    def _pestana_revertir(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="  2 · Revertir  ")
        tab.columnconfigure(0, weight=1)

        f_tab = ttk.LabelFrame(tab, text="Tabla de correspondencias", style="Seccion.TLabelframe",
                               padding=8)
        f_tab.grid(row=0, column=0, sticky="ew")
        f_tab.columnconfigure(1, weight=1)
        ttk.Label(f_tab, text="Archivo:").grid(row=0, column=0, sticky="w")
        self.var_tabla = tk.StringVar()
        ttk.Entry(f_tab, textvariable=self.var_tabla).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(f_tab, text="Elegir…", command=self._elegir_tabla).grid(row=0, column=2)
        ttk.Label(f_tab, text="Contraseña:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        fpw = ttk.Frame(f_tab)
        fpw.grid(row=1, column=1, columnspan=2, sticky="w", padx=6, pady=(6, 0))
        self.var_pass_rev = tk.StringVar()
        e = ttk.Entry(fpw, textvariable=self.var_pass_rev, show="•", width=24)
        e.pack(side="left")
        e.bind("<Return>", lambda _e: self.cargar_tabla_rev())
        ttk.Button(fpw, text="Abrir tabla", command=self.cargar_tabla_rev).pack(side="left", padx=6)
        self.lbl_tabla = ttk.Label(fpw, style="Nota.TLabel", text="")
        self.lbl_tabla.pack(side="left", padx=6)

        f_arch = ttk.LabelFrame(tab, text="A) Documentos que te devolvió la IA",
                                style="Seccion.TLabelframe", padding=8)
        f_arch.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        vacio = ("Arrastra aquí el Word, Excel, PowerPoint, PDF o texto que generó la IA" if TkinterDnD
                 else "Usa «Agregar archivos…» para elegir lo que generó la IA")
        self.lista_rev = ListaArchivos(f_arch, vacio, alto=4)
        self.lista_rev.pack(fill="both", expand=True)
        fb = ttk.Frame(f_arch)
        fb.pack(fill="x", pady=(8, 0))
        self.btn_rev = ttk.Button(fb, text="Revertir documentos", style="Accion.TButton",
                                  command=self.ejecutar_revertir)
        self.btn_rev.pack(side="left")
        ttk.Label(fb, style="Nota.TLabel", text="  Se guardan junto a cada archivo con «_revertido».").pack(
            side="left")

        f_txt = ttk.LabelFrame(tab, text="B) Respuesta pegada desde el chat de la IA",
                               style="Seccion.TLabelframe", padding=8)
        f_txt.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        f_txt.columnconfigure(0, weight=1)
        f_txt.columnconfigure(1, weight=1)
        f_txt.rowconfigure(1, weight=1)
        ttk.Label(f_txt, text="Pega aquí la respuesta de la IA:").grid(row=0, column=0, sticky="w")
        ttk.Label(f_txt, text="Resultado con los datos reales:").grid(row=0, column=1, sticky="w", padx=(10, 0))
        m1, self.txt_entrada = area_texto(f_txt, alto=8)
        m2, self.txt_salida = area_texto(f_txt, alto=8)
        m1.grid(row=1, column=0, sticky="nsew")
        m2.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        fb2 = ttk.Frame(f_txt)
        fb2.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(fb2, text="Revertir texto", command=self.revertir_texto).pack(side="left")
        ttk.Button(fb2, text="Copiar resultado", command=self.copiar_resultado).pack(side="left", padx=6)
        ttk.Button(fb2, text="Limpiar", command=lambda: (self.txt_entrada.delete("1.0", "end"),
                                                       self.txt_salida.delete("1.0", "end"))).pack(side="left")
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(2, weight=2)

    # ---- utilidades ----------------------------------------------------------
    def log(self, texto: str):
        self.registro.configure(state="normal")
        self.registro.insert("end", texto + "\n")
        self.registro.see("end")
        self.registro.configure(state="disabled")

    def _elegir_carpeta(self, var):
        c = filedialog.askdirectory(title="Carpeta de destino")
        if c:
            var.set(c)

    def _elegir_tabla(self):
        r = filedialog.askopenfilename(title="Elegir tabla de correspondencias",
                                       filetypes=[("Tabla del Anonimizador", "*" + EXTENSION_TABLA),
                                                  ("Todos los archivos", "*.*")])
        if r:
            self.var_tabla.set(r)
            self.tabla_revertir = None
            self.lbl_tabla.configure(text="")

    @staticmethod
    def _lineas(txt: tk.Text):
        return [x.strip() for x in txt.get("1.0", "end").splitlines() if x.strip()]

    def _opciones(self) -> Opciones:
        return Opciones(categorias=[c for c, v in self.vars_cat.items() if v.get()],
                        excluir=self._lineas(self.txt_excluir), siempre=self._lineas(self.txt_siempre),
                        carpeta_salida=self.var_carpeta.get().strip(), tabla_comun=self.var_lote.get(),
                        pdf_a_word=self.var_pdfword.get())

    def _guardar_preferencias(self):
        op = self._opciones()
        self.cfg.update({"categorias": op.categorias, "excluir": op.excluir, "siempre": op.siempre,
                         "carpeta_salida": op.carpeta_salida, "tabla_comun": op.tabla_comun,
                         "pdf_a_word": op.pdf_a_word, "geometria": self.root.geometry()})
        guardar_config(self.cfg)

    def _ocupar(self, si: bool):
        self.ocupado = si
        estado = "disabled" if si else "normal"
        self.btn_anon.configure(state=estado)
        self.btn_rev.configure(state=estado)
        self.root.configure(cursor="watch" if si else "")

    def _en_hilo(self, funcion):
        self._ocupar(True)

        def correr():
            try:
                funcion()
            except Exception as e:  # noqa: BLE001
                self.cola.put(("error", str(e) or e.__class__.__name__))
            finally:
                self.cola.put(("fin", None))
        threading.Thread(target=correr, daemon=True).start()

    def _procesar_cola(self):
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "log":
                    self.log(dato)
                elif tipo == "progreso":
                    i, n = dato
                    self.progreso.configure(maximum=max(n, 1), value=i)
                elif tipo == "error":
                    self.log("✖ " + dato)
                    messagebox.showerror("Anonimizador IA", dato)
                elif tipo == "info":
                    messagebox.showinfo("Anonimizador IA", dato)
                elif tipo == "carpeta":
                    self.ultima_carpeta = dato
                    self.btn_abrir.configure(state="normal")
                elif tipo == "tabla":
                    self.var_tabla.set(dato)
                    self.tabla_revertir = None
                    self.lbl_tabla.configure(text="")
                elif tipo == "fin":
                    self._ocupar(False)
        except queue.Empty:
            pass
        self.root.after(100, self._procesar_cola)

    # ---- acciones: anonimizar -------------------------------------------------
    def ejecutar_anonimizar(self):
        if self.ocupado:
            return
        rutas = [r for r in self.lista_anon.rutas]
        if not rutas:
            messagebox.showwarning("Anonimizador IA", "Primero agrega uno o más documentos.")
            return
        op = self._opciones()
        if not op.categorias and not op.siempre:
            messagebox.showwarning("Anonimizador IA", "Marca al menos un tipo de dato para anonimizar.")
            return
        p1, p2 = self.var_pass1.get(), self.var_pass2.get()
        if len(p1) < MIN_CONTRASENA:
            messagebox.showwarning("Anonimizador IA",
                                   f"La contraseña de la tabla debe tener al menos {MIN_CONTRASENA} caracteres.")
            return
        if p1 != p2:
            messagebox.showwarning("Anonimizador IA", "Las contraseñas no coinciden.")
            return
        self._guardar_preferencias()
        clave = (tuple(op.tipos()), tuple(op.excluir), tuple(op.siempre))

        def trabajo():
            if self.detector is None or self.detector_clave != clave:
                if any(c in op.categorias for c in ("personas", "organizaciones")):
                    self.cola.put(("log", "Cargando el modelo de lenguaje (puede tardar unos segundos)…"))
                self.detector = crear_detector(op)
                self.detector_clave = clave
            self.cola.put(("log", f"Anonimizando {len(rutas)} documento(s)…"))
            res, tablas = anonimizar(rutas, op, p1, detector=self.detector,
                                     avisar=lambda m: self.cola.put(("log", m)),
                                     progreso=lambda i, n: self.cola.put(("progreso", (i, n))))
            ok = [r for r in res if r.ok]
            for r in res:
                if r.ok:
                    extra = "".join(f"\n     + {os.path.basename(x)}" for x in r.extras)
                    self.cola.put(("log", f"✔ {os.path.basename(r.entrada)} → "
                                          f"{os.path.basename(r.salida)} ({r.reemplazos} reemplazos){extra}"))
                    for a in r.avisos:
                        self.cola.put(("log", "   ⚠ " + a))
                else:
                    self.cola.put(("log", f"✖ {os.path.basename(r.entrada)}: {r.error}"))
            for t in tablas:
                self.cola.put(("log", f"Tabla guardada (cifrada): {t}"))
            if ok:
                self.cola.put(("carpeta", os.path.dirname(ok[0].salida)))
                self.cola.put(("info",
                               f"Listo: {len(ok)} de {len(res)} documento(s) anonimizado(s).\n\n"
                               "• Entrega a la IA los archivos «_anonimizado».\n"
                               "• Guarda la tabla (.tabla) y su contraseña: la necesitarás para revertir.\n"
                               "• Usa «Copiar instrucción para la IA» y pégala junto al documento."))
                if tablas:
                    self.cola.put(("tabla", tablas[-1]))
        self._en_hilo(trabajo)

    def copiar_instruccion(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(INSTRUCCION_IA)
        self.log("Instrucción copiada. Pégala en el chat de la IA junto con el documento.")

    # ---- acciones: revertir ---------------------------------------------------
    def cargar_tabla_rev(self) -> bool:
        ruta = self.var_tabla.get().strip()
        if not ruta or not os.path.exists(ruta):
            messagebox.showwarning("Anonimizador IA", "Elige el archivo de la tabla (.tabla).")
            return False
        try:
            contrasena = self.var_pass_rev.get() if tabla_esta_cifrada(ruta) else None
            self.tabla_revertir = cargar_tabla(ruta, contrasena)
        except (ContrasenaIncorrecta, TablaInvalida) as e:
            self.tabla_revertir = None
            self.lbl_tabla.configure(text="")
            messagebox.showerror("Anonimizador IA", str(e))
            return False
        self.lbl_tabla.configure(text=f"✔ Tabla abierta ({len(self.tabla_revertir)} datos)")
        return True

    def _tabla_lista(self) -> bool:
        return self.tabla_revertir is not None or self.cargar_tabla_rev()

    def _informe(self, rev: Reversor) -> str:
        partes = [f"{sum(rev.restauradas.values())} etiqueta(s) restaurada(s)"]
        if rev.desconocidas:
            partes.append("⚠ etiquetas que no están en la tabla (revísalas a mano): "
                          + ", ".join(f"[{e}]" for e in sorted(rev.desconocidas)))
        return "\n".join(partes)

    def ejecutar_revertir(self):
        if self.ocupado or not self._tabla_lista():
            return
        rutas = list(self.lista_rev.rutas)
        if not rutas:
            messagebox.showwarning("Anonimizador IA", "Agrega los documentos que te devolvió la IA.")
            return
        tabla = self.tabla_revertir

        def trabajo():
            res, rev = revertir(rutas, tabla, progreso=lambda i, n: self.cola.put(("progreso", (i, n))))
            for r in res:
                if r.ok:
                    self.cola.put(("log", f"✔ {os.path.basename(r.entrada)} → {os.path.basename(r.salida)}"))
                else:
                    self.cola.put(("log", f"✖ {os.path.basename(r.entrada)}: {r.error}"))
            informe = self._informe(rev)
            self.cola.put(("log", informe))
            ok = [r for r in res if r.ok]
            if ok:
                self.cola.put(("carpeta", os.path.dirname(ok[0].salida)))
                self.cola.put(("info", f"Listo: {len(ok)} documento(s) revertido(s).\n\n{informe}"))
        self._en_hilo(trabajo)

    def revertir_texto(self):
        if not self._tabla_lista():
            return
        rev = Reversor(self.tabla_revertir)
        resultado = rev.revertir_texto(self.txt_entrada.get("1.0", "end-1c"))
        self.txt_salida.delete("1.0", "end")
        self.txt_salida.insert("1.0", resultado)
        self.log("Texto revertido: " + self._informe(rev).replace("\n", " · "))

    def copiar_resultado(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.txt_salida.get("1.0", "end-1c"))
        self.log("Resultado copiado al portapapeles.")

    def cerrar(self):
        if self.ocupado and not messagebox.askyesno("Anonimizador IA",
                                                    "Hay un proceso en curso. ¿Cerrar de todos modos?"):
            return
        self._guardar_preferencias()
        self.root.destroy()


def _poner_icono(root):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ruta = os.path.join(base, "recursos", "icono.png")
    try:
        if os.path.exists(ruta):
            root._icono = tk.PhotoImage(file=ruta).subsample(16)   # 64 px
            root.iconphoto(True, root._icono)
    except tk.TclError:
        pass


def main():
    if ES_WIN:
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
    try:
        root = TkinterDnD.Tk() if TkinterDnD is not None else tk.Tk()
    except Exception:  # noqa: BLE001 - si falla el arrastrar-soltar, ventana normal
        root = tk.Tk()
    _poner_icono(root)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
