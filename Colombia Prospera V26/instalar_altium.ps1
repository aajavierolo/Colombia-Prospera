param(
    [ValidateSet('Streamlit','Docker')][string]$Modo = 'Streamlit',
    [switch]$SoloComprobar
)
$ErrorActionPreference = 'Stop'
$script:RaizAltium = $PSScriptRoot
$script:EstadoAltium = Join-Path $script:RaizAltium '.altium'
Set-Location -LiteralPath $script:RaizAltium

function Paso([string]$Texto) { Write-Host "`n$Texto" -ForegroundColor Cyan }
function Ejecutar([string]$Programa, [string[]]$Parametros) {
    & $Programa @Parametros
    if ($LASTEXITCODE -ne 0) { throw "El comando termino con codigo $LASTEXITCODE : $Programa $($Parametros -join ' ')" }
}
function Codigo-Silencioso([string]$Programa, [string[]]$Parametros) {
    $ErrorActionPreference = 'Continue'
    & $Programa @Parametros *> $null
    return $LASTEXITCODE
}
function Capturar-Programa([string]$Programa, [string[]]$Parametros) {
    $ErrorActionPreference = 'Continue'
    $salida = @(& $Programa @Parametros 2>$null)
    return [pscustomobject]@{Codigo=$LASTEXITCODE; Salida=($salida -join '')}
}
function Buscar-Programa([string]$Nombre, [string[]]$Rutas) {
    $command = Get-Command $Nombre -ErrorAction SilentlyContinue
    if ($command -and (Test-Path -LiteralPath $command.Source)) { return $command.Source }
    foreach ($ruta in $Rutas) { if ($ruta -and (Test-Path -LiteralPath $ruta)) { return $ruta } }
    return $null
}
function Instalar-Paquete([string]$Id, [string]$Nombre) {
    $winget = Buscar-Programa 'winget.exe' @()
    if (-not $winget) { throw "Falta $Nombre. Instala App Installer de Microsoft Store para habilitar winget, o instala $Nombre desde su sitio oficial, y vuelve a ejecutar este BAT." }
    Paso "Instalando $Nombre. Windows puede solicitar tu autorizacion."
    Ejecutar $winget @('install','--exact','--id',$Id,'--source','winget')
}
function Buscar-Python {
    $candidatos = @()
    $py = Buscar-Programa 'py.exe' @()
    if ($py) {
        $candidatos += [pscustomobject]@{Programa=$py; Prefijo=@('-3.12')}
        $candidatos += [pscustomobject]@{Programa=$py; Prefijo=@('-3.11')}
    }
    foreach ($ruta in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:ProgramFiles 'Python312\python.exe')
    )) {
        if (Test-Path -LiteralPath $ruta) { $candidatos += [pscustomobject]@{Programa=$ruta; Prefijo=@()} }
    }
    foreach ($normal in @(Get-Command 'python.exe' -All -ErrorAction SilentlyContinue)) {
        if ($normal.Source -and $normal.Source -notmatch 'WindowsApps') {
            $candidatos += [pscustomobject]@{Programa=$normal.Source; Prefijo=@()}
        }
    }
    foreach ($candidato in $candidatos) {
        $comando = @($candidato.Prefijo) + @('-c','import sys; sys.exit(0 if (3,11)<=sys.version_info[:2]<(3,13) else 1)')
        try {
            & $candidato.Programa @comando 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidato }
        } catch { }
    }
    return $null
}
function Preparar-Streamlit {
    $python = Buscar-Python
    if (-not $python) {
        Instalar-Paquete 'Python.Python.3.12' 'Python 3.12'
        $python = Buscar-Python
    }
    if (-not $python) { throw 'Python 3.11/3.12 no esta disponible. Cierra esta ventana y vuelve a abrir el BAT.' }
    Ejecutar $python.Programa (@($python.Prefijo) + @((Join-Path $script:RaizAltium 'preparar_altium.py')))
}
function Buscar-Docker {
    return (Buscar-Programa 'docker.exe' @(
        (Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe')
    ))
}
function Buscar-DockerDesktop {
    return (Buscar-Programa 'Docker Desktop.exe' @(
        (Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\Docker Desktop.exe')
    ))
}
function Puerto-Libre([int]$Inicio=8502) {
    for ($puerto=$Inicio; $puerto -le 8520; $puerto++) {
        $oyente = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$puerto)
        try { $oyente.Start(); return $puerto } catch { } finally { $oyente.Stop() }
    }
    throw 'No hay puertos libres entre 8502 y 8520.'
}
function Web-Lista([string]$Url) {
    $peticion = [System.Net.HttpWebRequest]::Create($Url + '/_stcore/health')
    $peticion.Proxy = $null
    $peticion.Timeout = 2000
    $respuesta = $null
    try { $respuesta = $peticion.GetResponse(); return [int]$respuesta.StatusCode -eq 200 } catch { return $false } finally { if ($respuesta) { $respuesta.Dispose() } }
}
function Preparar-Docker {
    $docker = Buscar-Docker
    if (-not $docker) {
        Instalar-Paquete 'Docker.DockerDesktop' 'Docker Desktop'
        $docker = Buscar-Docker
    }
    if (-not $docker) { throw 'Docker Desktop requiere completar su instalacion o reiniciar Windows. Despues ejecuta este BAT de nuevo.' }
    if ((Codigo-Silencioso $docker @('info')) -ne 0) {
        $desktop = Buscar-DockerDesktop
        if ($desktop) {
            Paso 'Iniciando Docker Desktop...'
            Start-Process -FilePath $desktop -WindowStyle Hidden | Out-Null
        }
    }
    $listo=$false
    for ($i=0; $i -lt 60; $i++) {
        if ((Codigo-Silencioso $docker @('info')) -eq 0) { $listo=$true; break }
        if ($i % 10 -eq 0) { Write-Host 'Esperando a Docker Desktop. Si muestra una configuracion inicial, completala.' }
        Start-Sleep -Seconds 2
    }
    if (-not $listo) { throw 'Docker no arranca. Abre Docker Desktop y completa su configuracion. Si pide WSL 2 o reiniciar Windows, hazlo y ejecuta el BAT otra vez. No se modificaron las funciones de Windows automaticamente.' }
    Ejecutar $docker @('compose','version')
    $compose = @('compose','--project-name','altium-v26-simple','--file',(Join-Path $script:RaizAltium 'docker-compose.yml'))
    # Reutilizar el puerto del mismo proyecto si ya esta funcionando.
    $consultaPuerto = Capturar-Programa $docker ($compose + @('port','altium-financiero','8501'))
    if ($consultaPuerto.Codigo -eq 0 -and $consultaPuerto.Salida -match '127\.0\.0\.1:(\d+)') {
        $puerto = [int]$Matches[1]
    } else { $puerto = Puerto-Libre }
    $env:ALTIUM_DOCKER_PORT = [string]$puerto
    Ejecutar $docker ($compose + @('config','--quiet'))
    Paso 'Construyendo y abriendo Altium con Docker...'
    Ejecutar $docker ($compose + @('up','-d','--build','--wait','--wait-timeout','180','altium-financiero'))
    $url = 'http://127.0.0.1:' + $puerto
    if (-not (Web-Lista $url)) {
        & $docker @compose logs --tail=35 altium-financiero
        throw "El contenedor no responde todavia en $url. Revisa los mensajes anteriores."
    }
    Write-Host "`nAltium listo: $url" -ForegroundColor Green
    Write-Host 'Puedes cerrar esta ventana. Los contenedores seguiran funcionando.'
    Write-Host 'Para detenerlos: detener_altium_docker.bat. Los datos se conservan.'
    Start-Process $url
}

try {
    foreach ($archivo in @('app.py','requirements.txt','preparar_altium.py','iniciar_streamlit.py','Dockerfile','docker-compose.yml')) {
        if (-not (Test-Path -LiteralPath (Join-Path $script:RaizAltium $archivo))) { throw "Falta $archivo. Conserva los BAT dentro de la carpeta completa de Altium." }
    }
    if ($SoloComprobar) {
        Write-Host 'Archivos de Altium: correctos. No se instalaron programas ni se inicio ningun servicio.'
        Write-Host "Modo seleccionado: $Modo"
        exit 0
    }
    New-Item -ItemType Directory -Force -Path $script:EstadoAltium | Out-Null
    Write-Host "ALTIUM FINANCIERO V26 - $Modo" -ForegroundColor Cyan
    Write-Host 'Primer uso: descarga de Python y dependencias. Despues se reutiliza lo instalado.'
    if ($Modo -eq 'Streamlit') { Preparar-Streamlit } else { Preparar-Docker }
    exit 0
} catch {
    Write-Host "`nNo se completo la preparacion: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Puedes corregir el problema y ejecutar el mismo BAT otra vez; conserva tu Excel.'
    exit 1
}
