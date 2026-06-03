#Requires -Version 5.1
# InoLabel build script for Windows (PowerShell native)
# Usage: powershell -ExecutionPolicy Bypass -File build.ps1

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$CONDA_ENV_NAME = "inolabel"
$DIST_DIR       = "dist\InoLabel-windows"
$BUNDLE_DIR     = "$DIST_DIR\InoLabel"
$EXE_PATH       = "$BUNDLE_DIR\InoLabel.exe"

function Write-Ok($msg)   { Write-Host "  [OK] $msg"    -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [AVISO] $msg" -ForegroundColor Yellow }
function Write-Info($msg) { Write-Host "  [INFO] $msg"  -ForegroundColor Cyan }
function Write-Step($msg) { Write-Host "`n==> $msg"     -ForegroundColor White }
function Write-Fail($msg) { Write-Host "  [ERRO] $msg"  -ForegroundColor Red; exit 1 }

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# ── Log file ──────────────────────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path "dist\logs" | Out-Null
$LOG_FILE = "dist\logs\build_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-Transcript -Path $LOG_FILE -Append | Out-Null

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════╗"
Write-Host "║        InoLabel — Build Script       ║"
Write-Host "╚══════════════════════════════════════╝"
Write-Host "  Alvo : windows"
Write-Host "  Data : $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')"
Write-Host "  Log  : $LOG_FILE"
Write-Host ""

# ── Verificar raiz do projeto ─────────────────────────────────────────────────
Write-Step "Verificando pre-requisitos..."

if (-not (Test-Path "main.py"))         { Write-Fail "main.py nao encontrado. Execute build.ps1 a partir da raiz do projeto." }
if (-not (Test-Path "requirements.txt")){ Write-Fail "requirements.txt nao encontrado." }
if (-not (Test-Path "frontend\dist"))   { Write-Fail "frontend\dist nao encontrado. Execute 'npm run build' dentro de frontend/ antes de buildar." }
Write-Ok "Raiz do projeto"
Write-Ok "frontend\dist encontrado"

# ── Verificar build existente ─────────────────────────────────────────────────
$bundleComplete = (Test-Path $EXE_PATH) -and (
    (Test-Path "$BUNDLE_DIR\frontend\dist") -or (Test-Path "$BUNDLE_DIR\_internal\frontend\dist")
)
$bundlePartial = (Test-Path $BUNDLE_DIR) -and (-not $bundleComplete)

if ($bundleComplete) {
    Write-Host ""
    Write-Ok "Build completo encontrado em: $BUNDLE_DIR"
    Write-Host ""
    Write-Host "  O que voce deseja fazer?"
    Write-Host "    1) Reinstalar (apaga o build atual e gera um novo)"
    Write-Host "    2) Continuar usando o build existente"
    Write-Host ""
    do {
        $choice = Read-Host "  Escolha [1/2]"
    } while ($choice -notin @("1", "2"))

    if ($choice -eq "1") {
        Write-Info "Removendo build anterior..."
        Remove-Item -Recurse -Force $DIST_DIR -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force "build\InoLabel" -ErrorAction SilentlyContinue
        Remove-Item -Force "InoLabel.spec" -ErrorAction SilentlyContinue
        Write-Ok "Build anterior removido."
    } else {
        Write-Info "Usando build existente. Para rodar: $EXE_PATH"
        Stop-Transcript | Out-Null
        exit 0
    }
} elseif ($bundlePartial) {
    Write-Warn "Instalacao incompleta detectada em: $BUNDLE_DIR"
    $answer = Read-Host "  Limpar e reconstruir? [s/n]"
    if ($answer -match "^[sS]") {
        Remove-Item -Recurse -Force $DIST_DIR -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force "build\InoLabel" -ErrorAction SilentlyContinue
        Remove-Item -Force "InoLabel.spec" -ErrorAction SilentlyContinue
        Write-Ok "Build parcial removido."
    } else {
        Write-Fail "Build corrompido mantido. Remova '$DIST_DIR' manualmente e tente novamente."
    }
} else {
    Write-Ok "Nenhum build anterior — iniciando build limpo."
}

# ── Localizar conda ───────────────────────────────────────────────────────────
$condaCmd = $null
$condaCandidates = @(
    $env:CONDA_EXE,
    "$env:USERPROFILE\miniconda3\Scripts\conda.exe",
    "$env:USERPROFILE\Miniconda3\Scripts\conda.exe",
    "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
    "$env:USERPROFILE\Anaconda3\Scripts\conda.exe",
    "C:\ProgramData\miniconda3\Scripts\conda.exe",
    "C:\ProgramData\Miniconda3\Scripts\conda.exe",
    "C:\ProgramData\anaconda3\Scripts\conda.exe"
)

# Also check PATH
$pathConda = Get-Command conda -ErrorAction SilentlyContinue
if ($pathConda) { $condaCandidates = @($pathConda.Source) + $condaCandidates }

foreach ($candidate in $condaCandidates) {
    if ($candidate -and (Test-Path $candidate)) {
        $condaCmd = $candidate
        break
    }
}

if (-not $condaCmd) {
    Write-Fail "Conda nao encontrado. Instale o Miniconda em https://docs.conda.io/en/latest/miniconda.html e tente novamente."
}
Write-Ok "Conda: $(& $condaCmd --version 2>&1)"

$condaBase = (& $condaCmd info --base 2>&1).Trim()
$pythonPath = "$condaBase\envs\$CONDA_ENV_NAME\python.exe"

# ── Criar ambiente conda se ausente ──────────────────────────────────────────
$envList = & $condaCmd env list 2>&1
if ($envList -match "(?m)^$CONDA_ENV_NAME\s") {
    Write-Ok "Ambiente conda '$CONDA_ENV_NAME' encontrado."
} else {
    Write-Info "Criando ambiente '$CONDA_ENV_NAME' com Python 3.9..."
    & $condaCmd create -n $CONDA_ENV_NAME python=3.9 -y
    if ($LASTEXITCODE -ne 0) { Write-Fail "Falha ao criar ambiente '$CONDA_ENV_NAME'." }
    Write-Ok "Ambiente '$CONDA_ENV_NAME' criado."
}

if (-not (Test-Path $pythonPath)) {
    Write-Fail "Python nao encontrado em '$pythonPath'. Verifique a instalacao do conda."
}
$pyVersion = (& $pythonPath --version 2>&1).Trim()
Write-Ok $pyVersion

# ── Verificar espaco em disco ─────────────────────────────────────────────────
$drive = (Split-Path -Qualifier (Get-Location).Path).TrimEnd(':')
try {
    $freeGB = [math]::Round((Get-PSDrive $drive -ErrorAction Stop).Free / 1GB, 1)
    if ($freeGB -lt 4) { Write-Fail "Espaco insuficiente: ${freeGB}GB disponivel, 4GB necessario." }
    Write-Ok "Espaco em disco: ${freeGB}GB disponivel"
} catch {
    Write-Warn "Nao foi possivel verificar espaco em disco."
}

# ── Instalar dependencias Python ──────────────────────────────────────────────
Write-Step "Instalando dependencias Python..."
Write-Host "  (pode levar alguns minutos na primeira vez...)"

& $pythonPath -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Fail "Falha ao instalar requirements.txt" }
Write-Ok "requirements.txt instalado"

& $pythonPath -m pip install "pyinstaller>=5.0"
if ($LASTEXITCODE -ne 0) { Write-Fail "Falha ao instalar PyInstaller" }
$piVersion = (& $pythonPath -m PyInstaller --version 2>&1).Trim()
Write-Ok "PyInstaller $piVersion"

# ── Validar imports criticos ──────────────────────────────────────────────────
Write-Step "Validando imports criticos..."
$failedImports = @()
foreach ($pkg in @("fastapi", "uvicorn", "cv2", "PIL", "numpy", "ultralytics")) {
    & $pythonPath -c "import $pkg" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Falha ao importar '$pkg'"
        $failedImports += $pkg
    } else {
        Write-Ok "import $pkg"
    }
}

if ($failedImports.Count -gt 0) {
    Write-Info "Tentando reinstalar pacotes com falha..."
    foreach ($pkg in $failedImports) {
        Write-Info "Reinstalando $pkg..."
        & $pythonPath -m pip install --force-reinstall $pkg
        & $pythonPath -c "import $pkg" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Ok "$pkg reinstalado" } else { Write-Warn "Falha ao reinstalar $pkg" }
    }
}

# ── Build com PyInstaller ─────────────────────────────────────────────────────
Write-Step "Gerando executavel com PyInstaller..."
Write-Host "  (etapa mais demorada — 5-15 minutos dependendo da maquina)"
Write-Host ""

& $pythonPath -m PyInstaller `
    --log-level INFO `
    --noconfirm `
    --onedir `
    --windowed `
    --name "InoLabel" `
    --distpath $DIST_DIR `
    "--add-data=assets;assets" `
    "--add-data=frontend/dist;frontend/dist" `
    "--hidden-import=cv2" `
    "--hidden-import=ultralytics" `
    "--hidden-import=scipy.spatial" `
    "--hidden-import=scipy.optimize" `
    "--hidden-import=scipy.sparse" `
    "--hidden-import=scipy.linalg" `
    "--hidden-import=cython_bbox" `
    "--hidden-import=lap" `
    "--hidden-import=fastapi" `
    "--hidden-import=uvicorn.logging" `
    "--hidden-import=uvicorn.loops" `
    "--hidden-import=uvicorn.loops.auto" `
    "--hidden-import=uvicorn.protocols" `
    "--hidden-import=uvicorn.protocols.http" `
    "--hidden-import=uvicorn.protocols.http.auto" `
    "--hidden-import=uvicorn.protocols.websockets" `
    "--hidden-import=uvicorn.protocols.websockets.auto" `
    "--hidden-import=uvicorn.lifespan" `
    "--hidden-import=uvicorn.lifespan.on" `
    "--hidden-import=aiofiles" `
    "--hidden-import=multipart" `
    "--hidden-import=jose" `
    "--hidden-import=filelock" `
    "--hidden-import=websockets" `
    "--hidden-import=pdb" `
    "--hidden-import=doctest" `
    "--hidden-import=unittest" `
    "--hidden-import=unittest.mock" `
    "--hidden-import=xmlrpc" `
    "--hidden-import=xmlrpc.client" `
    "--collect-all=ultralytics" `
    "--collect-all=matplotlib" `
    "--collect-all=uvicorn" `
    "--collect-all=fastapi" `
    "--collect-all=starlette" `
    "--collect-all=tracker" `
    "--exclude-module=notebook" `
    "--exclude-module=jupyter" `
    "--exclude-module=ipykernel" `
    "--exclude-module=pytest" `
    "--exclude-module=_pytest" `
    "--exclude-module=multiprocessing.dummy" `
    main.py

if ($LASTEXITCODE -ne 0) { Write-Fail "PyInstaller falhou. Veja o log acima para detalhes." }

# ── Verificacao pos-build ─────────────────────────────────────────────────────
Write-Step "Verificando build..."

if (-not (Test-Path $EXE_PATH)) { Write-Fail "Executavel nao encontrado em '$EXE_PATH' — build falhou." }
Write-Ok "Executavel: $EXE_PATH"

$bundleSizeMB = [math]::Round(
    (Get-ChildItem $BUNDLE_DIR -Recurse -ErrorAction SilentlyContinue |
     Measure-Object -Property Length -Sum).Sum / 1MB
)
Write-Ok "Tamanho do bundle: ${bundleSizeMB}MB"

$frontendFound = $false
foreach ($candidate in @("$BUNDLE_DIR\frontend\dist", "$BUNDLE_DIR\_internal\frontend\dist")) {
    if (Test-Path $candidate) {
        Write-Ok "frontend/dist incluido em: $candidate"
        $frontendFound = $true
        break
    }
}
if (-not $frontendFound) { Write-Warn "frontend/dist nao encontrado — UI do navegador nao sera servida." }

$assetsFound = $false
foreach ($candidate in @("$BUNDLE_DIR\assets", "$BUNDLE_DIR\_internal\assets")) {
    if (Test-Path $candidate) {
        Write-Ok "assets/ incluido em: $candidate"
        $assetsFound = $true
        break
    }
}
if (-not $assetsFound) { Write-Warn "assets/ nao encontrado no bundle — logo pode nao aparecer." }

Write-Step "Verificando modulos criticos no bundle..."
foreach ($lib in @("cv2", "PIL", "fastapi")) {
    $found = Get-ChildItem $BUNDLE_DIR -Recurse -ErrorAction SilentlyContinue |
             Where-Object { $_.Name -like "*$lib*" } |
             Select-Object -First 1
    if ($found) { Write-Ok "$lib presente" } else { Write-Warn "$lib possivelmente ausente no bundle" }
}

# ── Atalho no Menu Iniciar ────────────────────────────────────────────────────
Write-Step "Registrando InoLabel no Menu Iniciar..."
try {
    $shell    = New-Object -ComObject WScript.Shell
    $startMenu = $shell.SpecialFolders("Programs")
    $lnk      = $shell.CreateShortcut("$startMenu\InoLabel.lnk")
    $lnk.TargetPath       = (Resolve-Path $EXE_PATH).Path
    $lnk.WorkingDirectory = (Resolve-Path $BUNDLE_DIR).Path
    $lnk.Description      = "Ferramenta de anotacao de imagens e videos — Inovisao"

    $iconCandidates = @(
        "$BUNDLE_DIR\_internal\assets\inolabellogo.png",
        "$BUNDLE_DIR\assets\inolabellogo.png"
    )
    foreach ($ico in $iconCandidates) {
        if (Test-Path $ico) { $lnk.IconLocation = "$ico,0"; break }
    }

    $lnk.Save()
    Write-Ok "Atalho criado em: $startMenu\InoLabel.lnk"
    Write-Info "Clique em Iniciar e pesquise 'InoLabel' para abrir."
} catch {
    Write-Warn "Nao foi possivel criar atalho: $_"
    Write-Warn "Tente rodar o script como Administrador."
}

# ── Sumario final ─────────────────────────────────────────────────────────────
$elapsed = [math]::Round($stopwatch.Elapsed.TotalSeconds)
Stop-Transcript | Out-Null

Write-Host ""
Write-Host "╔══════════════════════════════════════╗"
Write-Host "║           Build concluido!           ║"
Write-Host "╚══════════════════════════════════════╝"
Write-Host ""
Write-Host "  Saida   : $BUNDLE_DIR"
Write-Host "  Tamanho : ${bundleSizeMB}MB"
Write-Host "  Tempo   : ${elapsed}s"
Write-Host "  Log     : $LOG_FILE"
Write-Host ""
Write-Host "  Para rodar:"
Write-Host "    $BUNDLE_DIR\InoLabel.exe"
Write-Host ""
Write-Host "  IMPORTANTE: coloque model.pt e dataset/ ao lado do executavel."
Write-Host ""
