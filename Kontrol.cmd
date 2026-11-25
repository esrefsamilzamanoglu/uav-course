@echo off
setlocal
set "COURSE_PY=%~dp0haftalar\03\gercekci\.local\venv\Scripts\python.exe"
if not exist "%COURSE_PY%" (
  echo Once kok klasordeki Kur.cmd dosyasini calistirin.
  pause
  exit /b 1
)
"%COURSE_PY%" "%~dp0haftalar\03\gercekci\tools\check_install.py" %*
set "COURSE_EXIT=%errorlevel%"
pause
exit /b %COURSE_EXIT%
