@echo off
REM Abre el Anonimizador sin empaquetar (la primera vez instala lo necesario).
cd /d "%~dp0"
if not exist .venv (
  echo Preparando por primera vez, espera unos minutos...
  py -3.12 -m venv .venv 2>nul || python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install -r requirements.txt
  python -m spacy download es_core_news_md
) else (
  call .venv\Scripts\activate.bat
)
start "" pythonw -m anonimizador
