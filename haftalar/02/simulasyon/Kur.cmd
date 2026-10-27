@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\Kur.ps1"
set "course_exit=%errorlevel%"
if not "%course_exit%"=="0" echo Kurulum tamamlanamadi. Yukaridaki mesaji kontrol edin.
pause
exit /b %course_exit%
