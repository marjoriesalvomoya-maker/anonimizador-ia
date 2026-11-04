#!/bin/bash
# Abre el Anonimizador sin empaquetar (doble clic). La primera vez instala lo necesario.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Preparando por primera vez, espera unos minutos..."
  PY=python3.12; command -v $PY >/dev/null || PY=python3
  $PY -m venv .venv && source .venv/bin/activate
  python -m pip install -r requirements.txt && python -m spacy download es_core_news_md
else
  source .venv/bin/activate
fi
python -m anonimizador
