param([switch]$SoloComprobar)
$ErrorActionPreference='Stop'
$script:RaizPublicacion=$PSScriptRoot
$script:ImagenPublicacion='javierolo123/cuentas:v26-sin-ia'
$script:ImagenLatest='javierolo123/cuentas:sin-ia'
Set-Location -LiteralPath $script:RaizPublicacion
function Ejecutar-Publicacion([string]$Programa,[string[]]$Parametros) {
    $ErrorActionPreference='Continue'
    & $Programa @Parametros
    if ($LASTEXITCODE -ne 0) { throw "Fallo el comando: $Programa $($Parametros -join ' ')" }
}
function Construir-ConRegistro([string]$Docker) {
    $carpetaLog=Join-Path $script:RaizPublicacion '.altium'
    New-Item -ItemType Directory -Force -Path $carpetaLog | Out-Null
    $script:RegistroPublicacion=Join-Path $carpetaLog 'publicacion_v26.log'
    "Construccion de $script:ImagenPublicacion - $(Get-Date -Format s)" | Set-Content -LiteralPath $script:RegistroPublicacion -Encoding UTF8
    $ErrorActionPreference='Continue'
    & $Docker build --progress=plain --tag $script:ImagenPublicacion $script:RaizPublicacion 2>&1 | Tee-Object -FilePath $script:RegistroPublicacion -Append | ForEach-Object { Write-Host $_ }
    $codigoConstruccion=$LASTEXITCODE
    if ($codigoConstruccion -ne 0) { throw "No se pudo construir la imagen. El error completo quedo en: $script:RegistroPublicacion" }
}
function Capturar-Publicacion([string]$Programa,[string[]]$Parametros) {
    $ErrorActionPreference='Continue'
    $texto=@(& $Programa @Parametros 2>&1)
    return [pscustomobject]@{Codigo=$LASTEXITCODE; Texto=($texto -join [Environment]::NewLine)}
}
try {
    foreach ($archivo in @('app.py','requirements.txt','Dockerfile','.dockerignore','streamlit-docker.toml','validar_imagen_publica.py')) {
        if (-not (Test-Path -LiteralPath (Join-Path $script:RaizPublicacion $archivo))) { throw "Falta $archivo. Conserva el BAT dentro de la carpeta completa de Altium." }
    }
    $dockerfile=Get-Content -LiteralPath (Join-Path $script:RaizPublicacion 'Dockerfile') -Raw
    if ($dockerfile -match '(?im)^\s*(?:COPY|ADD)\s+\.\s') { throw 'El Dockerfile copia toda la carpeta. Limita la copia al codigo y recursos antes de publicar.' }
    $comando=Get-Command 'docker.exe' -ErrorAction SilentlyContinue
    $docker=if ($comando) { $comando.Source } else { $null }
    if (-not $docker) {
        foreach ($ruta in @((Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'),(Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'))) {
            if (Test-Path -LiteralPath $ruta) { $docker=$ruta; break }
        }
    }
    if (-not $docker) { throw 'Instala Docker Desktop y vuelve a ejecutar este BAT.' }
    if ($SoloComprobar) {
        Write-Host "Preparacion correcta para $script:ImagenPublicacion y $script:ImagenLatest. Sin construir ni publicar."
        exit 0
    }
    $info=Capturar-Publicacion $docker @('info')
    if ($info.Codigo -ne 0) { throw 'Docker Desktop no responde. Abre Docker Desktop, espera a que este listo y ejecuta este BAT de nuevo.' }
    Write-Host "Construyendo $script:ImagenPublicacion ..." -ForegroundColor Cyan
    Construir-ConRegistro $docker
    Write-Host 'Comprobando el contenido de la imagen...' -ForegroundColor Cyan
    Ejecutar-Publicacion $docker @('run','--rm','--network','none','--entrypoint','python',$script:ImagenPublicacion,'/usr/local/lib/altium/validar_imagen_publica.py')
    $nombrePrueba='altium-v26-hub-prueba-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
    try {
        Ejecutar-Publicacion $docker @('run','--detach','--name',$nombrePrueba,$script:ImagenPublicacion)
        $sano=$false
        for ($i=0; $i -lt 60; $i++) {
            $estado=Capturar-Publicacion $docker @('inspect','--format','{{.State.Health.Status}}',$nombrePrueba)
            if ($estado.Codigo -ne 0) { break }
            if ($estado.Texto.Trim() -eq 'healthy') { $sano=$true; break }
            if ($estado.Texto.Trim() -eq 'unhealthy') { break }
            Start-Sleep -Seconds 2
        }
        if (-not $sano) {
            & $docker logs --tail=40 $nombrePrueba
            throw 'La imagen no paso la prueba de arranque de Streamlit. No se publica.'
        }
    } finally {
        $limpieza=Capturar-Publicacion $docker @('rm','--force',$nombrePrueba)
    }
    # Ambas etiquetas apuntan exactamente a la misma imagen que paso las pruebas.
    Ejecutar-Publicacion $docker @('tag',$script:ImagenPublicacion,$script:ImagenLatest)
    Write-Host "Publicando $script:ImagenPublicacion ..." -ForegroundColor Cyan
    $ErrorActionPreference='Continue'
    $mensajes=@(& $docker push $script:ImagenPublicacion 2>&1 | ForEach-Object { Write-Host $_; $_ })
    $codigoPush=$LASTEXITCODE
    $ErrorActionPreference='Stop'
    if ($codigoPush -ne 0) {
        if (($mensajes -join ' ') -match '(?i)denied|unauthorized|insufficient_scope|authentication required') {
            Write-Host 'Inicia sesion con javierolo123. Introduce tu token de Docker Hub cuando Docker lo solicite; no lo compartas por chat.' -ForegroundColor Yellow
            Ejecutar-Publicacion $docker @('login','--username','javierolo123')
            Ejecutar-Publicacion $docker @('push',$script:ImagenPublicacion)
        } else { throw 'No se completo la subida. Revisa el mensaje anterior y vuelve a ejecutar este BAT.' }
    }
    Write-Host "Publicando $script:ImagenLatest ..." -ForegroundColor Cyan
    Ejecutar-Publicacion $docker @('push',$script:ImagenLatest)
    Write-Host "PUBLICACION COMPLETADA: $script:ImagenPublicacion y $script:ImagenLatest" -ForegroundColor Green
    Write-Host 'https://hub.docker.com/r/javierolo123/cuentas/tags?name=v26-sin-ia'
    exit 0
} catch {
    Write-Host "No se publico la imagen: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
