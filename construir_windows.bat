@echo off
REM ==========================================================================
REM  Anonimizador IA - construye el programa e instalador para Windows
REM  Requisitos: Python 3.11 o 3.12 de python.org (marcar "Add python.exe to PATH")
REM  Opcional:   Inno Setup 6 (https://jrsoftware.org/isinfo.php) para el instalador .exe
REM ==========================================================================
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3.12) else (set PY=python)
%PY% --version >nul 2>nul || (set PY=python)
%PY% --version || (echo No se encontro Python. Instala Python 3.12 desde python.org & pause & exit /b 1)

echo.
echo [1/4] Creando entorno aislado...
if not exist .venv %PY% -m venv .venv || goto :error
call .venv\Scripts\activate.bat

echo [2/4] Instalando dependencias (requiere internet solo esta vez)...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller || goto :error
python -m spacy download es_core_news_md || goto :error

echo [3/4] Empaquetando la aplicacion...
pyinstaller --noconfirm AnonimizadorIA.spec || goto :error

echo [4/4] Creando instalador...
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    %ISCC% instalador_windows.iss || goto :error
    echo.
    echo LISTO. Instalador: %cd%\salida\AnonimizadorIA-Instalador.exe
) else (
    echo Inno Setup no esta instalado: se omite el instalador.
    echo.
    echo LISTO. Programa: %cd%\dist\AnonimizadorIA\AnonimizadorIA.exe
    echo Puedes copiar la carpeta dist\AnonimizadorIA a cualquier lugar.
)
pause
exit /b 0

:error
echo.
echo Hubo un error. Revisa los mensajes de arriba.
pause
exit /b 1
