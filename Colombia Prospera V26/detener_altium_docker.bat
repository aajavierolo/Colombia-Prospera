@echo off
setlocal
cd /d "%~dp0"
set "ALTIUM_DOCKER=docker"
if exist "%ProgramFiles%\Docker\Docker\resources\bin\docker.exe" set "ALTIUM_DOCKER=%ProgramFiles%\Docker\Docker\resources\bin\docker.exe"
if exist "%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\docker.exe" set "ALTIUM_DOCKER=%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\docker.exe"
echo Deteniendo Altium en Docker. Los datos se conservan.
"%ALTIUM_DOCKER%" compose --project-name altium-v26-simple --file "%~dp0docker-compose.yml" down
if errorlevel 1 (
    echo No se pudo detener el proyecto. Inicia Docker Desktop y vuelve a intentarlo.
    pause
    exit /b 1
)
echo Proyecto detenido.
pause
