@echo off
setlocal
cd /d "%~dp0"
call "%~dp0INSTALAR_DOCKER.bat"
exit /b %ERRORLEVEL%
