@echo off
setlocal
cd /d "%~dp0"
call "%~dp0INICIAR_STREAMLIT.bat"
exit /b %ERRORLEVEL%
