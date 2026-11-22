@echo off
setlocal
cd /d "%~dp0"
title Publicar Altium V26 y latest en Docker Hub
set "ALTIUM_CHECK="
if /i "%~1"=="--comprobar" set "ALTIUM_CHECK=-SoloComprobar"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0publicar_dockerhub.ps1" %ALTIUM_CHECK%
set "ALTIUM_EXIT=%ERRORLEVEL%"
if defined ALTIUM_CHECK exit /b %ALTIUM_EXIT%
pause
exit /b %ALTIUM_EXIT%
