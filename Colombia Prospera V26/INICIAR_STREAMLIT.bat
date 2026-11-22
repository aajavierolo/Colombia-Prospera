@echo off
setlocal
cd /d "%~dp0"
title Altium V26 - Instalar e iniciar Streamlit
set "ALTIUM_CHECK="
if /i "%~1"=="--comprobar" set "ALTIUM_CHECK=-SoloComprobar"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_altium.ps1" -Modo Streamlit %ALTIUM_CHECK%
set "ALTIUM_EXIT=%ERRORLEVEL%"
if defined ALTIUM_CHECK exit /b %ALTIUM_EXIT%
if not "%ALTIUM_EXIT%"=="0" pause
exit /b %ALTIUM_EXIT%
