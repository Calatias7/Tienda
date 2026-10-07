@echo off
REM Abre el Cuaderno de la Tienda. La primera vez instala lo necesario.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Preparando el programa por primera vez...
  python -m venv .venv || (echo No se encontro Python. Instalalo desde https://www.python.org & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || (pause & exit /b 1)
)
".venv\Scripts\python.exe" run.py %*
pause
