#!/bin/bash
# ==========================================================================
#  Anonimizador IA — construye la aplicación (.app) y el instalador (.dmg) para Mac
#  Requisito: Python 3.11 o 3.12 de python.org (incluye tkinter)
#  Uso:  bash construir_mac.sh
# ==========================================================================
set -e
cd "$(dirname "$0")"

PY=""
for c in python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null && "$c" -c "import tkinter" 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "No se encontró Python con tkinter. Instala Python 3.12 desde https://www.python.org/downloads/macos/"
  exit 1
fi
echo "Usando $($PY --version)"

echo "[1/4] Creando entorno aislado..."
[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate

echo "[2/4] Instalando dependencias (requiere internet solo esta vez)..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt pyinstaller
python -m spacy download es_core_news_md

echo "[3/4] Empaquetando la aplicación..."
pyinstaller --noconfirm AnonimizadorIA.spec

echo "[4/4] Creando el instalador .dmg..."
mkdir -p salida dmg_tmp
rm -rf dmg_tmp/*
cp -R "dist/Anonimizador IA.app" dmg_tmp/
ln -sf /Applications dmg_tmp/Aplicaciones
ARQ=$(uname -m)
rm -f "salida/AnonimizadorIA-Mac-$ARQ.dmg"
hdiutil create -volname "Anonimizador IA" -srcfolder dmg_tmp -ov -format UDZO \
  "salida/AnonimizadorIA-Mac-$ARQ.dmg"
rm -rf dmg_tmp

echo
echo "LISTO: salida/AnonimizadorIA-Mac-$ARQ.dmg"
echo "Ábrelo y arrastra «Anonimizador IA» a Aplicaciones."
echo "La primera vez: clic derecho sobre la app → Abrir (no está firmada por Apple)."
