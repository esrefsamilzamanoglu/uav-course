@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Kur.ps1"
set "result=%errorlevel%"
echo.
pause
exit /b %result%
