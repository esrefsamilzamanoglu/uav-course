@echo off
setlocal
set "PYTHONUTF8=1"
if not exist "%~dp0.local\venv\Scripts\python.exe" (
  echo Once Kur.cmd dosyasini calistirin.
  pause
  exit /b 1
)
"%~dp0.local\venv\Scripts\python.exe" -u "%~dp0tools\reconstruct_gaussian.py" --viewer
pause
