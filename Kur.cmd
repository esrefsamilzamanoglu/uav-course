@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Kur.ps1" -OnkosullariKur -MissionPlannerKur %*
set "COURSE_EXIT=%errorlevel%"
if not "%COURSE_EXIT%"=="0" pause
exit /b %COURSE_EXIT%
