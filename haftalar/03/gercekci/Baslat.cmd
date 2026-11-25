@echo off
set "ROTA_PY=%~dp0.local\venv\Scripts\python.exe"
if not exist "%ROTA_PY%" (
  echo Once Kur.cmd dosyasini calistirin.
  pause
  exit /b 1
)
"%ROTA_PY%" -u "%~dp0backend\server.py" --open
if errorlevel 1 pause
