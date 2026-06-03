#Requires -Version 5.1
# InoLabel build script for Windows (PowerShell native, ASCII-only)
# Usage (PowerShell):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\build.ps1

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$CONDA_ENV_NAME = "inolabel"
$APLICATIVO_DIR = "APLICATIVO"
$DIST_TEMP     = "dist\InoLabel-build"

function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Info($msg) { Write-Host "  [INFO] $msg" -ForegroundColor Cyan }
function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor White }
function Write-Fail($msg) { Write-Host "  [ERROR] $msg" -ForegroundColor Red; exit 1 }

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

New-Item -ItemType Directory -Force -Path "dist\logs" | Out-Null
$LOG_FILE = "dist\logs\build_{0}.log" -f (Get-Date -Format 'yyyyMMdd_HHmmss')
Start-Transcript -Path $LOG_FILE -Append | Out-Null

Write-Host ""
Write-Host "========================================"
Write-Host "        InoLabel - Build Script"
Write-Host "========================================"
Write-Host "  Target: windows"
Write-Host "  Date  : $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')"
Write-Host "  Log   : $LOG_FILE"
Write-Host ""

Write-Step "Checking prerequisites..."
if (-not (Test-Path "main.py")) { Write-Fail "main.py not found. Run build.ps1 from project root." }
if (-not (Test-Path "requirements.txt")) { Write-Fail "requirements.txt not found." }
if (-not (Test-Path "frontend\dist")) { Write-Fail "frontend\dist not found. Run npm run build inside frontend/." }
Write-Ok "Project root validated"
Write-Ok "frontend\dist found"

$aplicativoExe  = Join-Path $APLICATIVO_DIR "InoLabel\InoLabel.exe"
$bundleComplete = (Test-Path $aplicativoExe) -and (
    (Test-Path (Join-Path $APLICATIVO_DIR "InoLabel\frontend\dist")) -or
    (Test-Path (Join-Path $APLICATIVO_DIR "InoLabel\_internal\frontend\dist"))
)
$bundlePartial = (Test-Path (Join-Path $APLICATIVO_DIR "InoLabel")) -and (-not $bundleComplete)

if ($bundleComplete) {
    Write-Host ""
    Write-Ok "Build completo encontrado em: $APLICATIVO_DIR\InoLabel"
    Write-Host ""
    Write-Host "  Escolha uma opcao:"
    Write-Host "    1) Reconstruir (remove build atual e cria um novo)"
    Write-Host "    2) Manter build atual"
    Write-Host ""

    do {
        $choice = Read-Host "  Selecione [1/2]"
    } while ($choice -notin @("1", "2"))

    if ($choice -eq "1") {
        Write-Info "Removendo build anterior..."
        Remove-Item -Recurse -Force $DIST_TEMP -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force (Join-Path $APLICATIVO_DIR "InoLabel") -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force "build\InoLabel" -ErrorAction SilentlyContinue
        Remove-Item -Force "InoLabel.spec" -ErrorAction SilentlyContinue
        Write-Ok "Build anterior removido"
    } else {
        Write-Info "Usando build existente. Execute: $aplicativoExe"
        Stop-Transcript | Out-Null
        exit 0
    }
} elseif ($bundlePartial) {
    Write-Warn "Build parcial detectado em: $APLICATIVO_DIR\InoLabel"
    $answer = Read-Host "  Limpar e reconstruir? [y/n]"
    if ($answer -match "^[yY]") {
        Remove-Item -Recurse -Force $DIST_TEMP -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force (Join-Path $APLICATIVO_DIR "InoLabel") -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force "build\InoLabel" -ErrorAction SilentlyContinue
        Remove-Item -Force "InoLabel.spec" -ErrorAction SilentlyContinue
        Write-Ok "Build parcial removido"
    } else {
        Write-Fail "Build parcial mantido. Remova '$APLICATIVO_DIR\InoLabel' manualmente e rode novamente."
    }
} else {
    Write-Ok "Nenhum build anterior encontrado - iniciando build limpo"
}

Write-Step "Locating conda..."
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

$pathConda = Get-Command conda -ErrorAction SilentlyContinue
if ($pathConda) {
    $condaCandidates = @($pathConda.Source) + $condaCandidates
}

foreach ($candidate in $condaCandidates) {
    if ($candidate -and (Test-Path $candidate)) {
        $condaCmd = $candidate
        break
    }
}

if (-not $condaCmd) {
    Write-Fail "Conda not found. Install Miniconda and try again."
}

Write-Ok "Conda: $(& $condaCmd --version 2>&1)"
$condaBase = (& $condaCmd info --base 2>&1).Trim()
$pythonPath = Join-Path $condaBase "envs\$CONDA_ENV_NAME\python.exe"

Write-Step "Checking conda environment..."
$envList = & $condaCmd env list 2>&1
if ($envList -match "(?m)^$CONDA_ENV_NAME\s") {
    Write-Ok "Conda env '$CONDA_ENV_NAME' found"
} else {
    Write-Info "Creating conda env '$CONDA_ENV_NAME' with Python 3.9..."
    & $condaCmd create -n $CONDA_ENV_NAME python=3.9 -y
    if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to create env '$CONDA_ENV_NAME'." }
    Write-Ok "Conda env '$CONDA_ENV_NAME' created"
}

if (-not (Test-Path $pythonPath)) {
    Write-Fail "Python not found at '$pythonPath'."
}

$pyVersion = (& $pythonPath --version 2>&1).Trim()
Write-Ok $pyVersion

Write-Step "Checking free disk space..."
$drive = (Split-Path -Qualifier (Get-Location).Path).TrimEnd(':')
try {
    $freeGB = [math]::Round((Get-PSDrive $drive -ErrorAction Stop).Free / 1GB, 1)
    if ($freeGB -lt 4) {
        Write-Fail "Insufficient space: ${freeGB}GB available, 4GB required."
    }
    Write-Ok "Disk space: ${freeGB}GB available"
} catch {
    Write-Warn "Could not verify disk space"
}

Write-Step "Installing Python dependencies..."
Write-Host "  (this can take a while on first run)"

& $pythonPath -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to install requirements.txt" }
Write-Ok "requirements.txt installed"

& $pythonPath -m pip install "pyinstaller>=5.0"
if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to install PyInstaller" }
$piVersion = (& $pythonPath -m PyInstaller --version 2>&1).Trim()
Write-Ok "PyInstaller $piVersion"

Write-Step "Validating critical imports..."
$failedImports = @()
foreach ($pkg in @("fastapi", "uvicorn", "cv2", "PIL", "numpy", "ultralytics")) {
    & $pythonPath -c "import $pkg" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Import failed: $pkg"
        $failedImports += $pkg
    } else {
        Write-Ok "import $pkg"
    }
}

if ($failedImports.Count -gt 0) {
    Write-Info "Trying to reinstall failed packages..."
    foreach ($pkg in $failedImports) {
        Write-Info "Reinstalling $pkg..."
        & $pythonPath -m pip install --force-reinstall $pkg
        & $pythonPath -c "import $pkg" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "$pkg reinstalled"
        } else {
            Write-Warn "Still failing: $pkg"
        }
    }
}

Write-Step "Building executable with PyInstaller..."
Write-Host "  (slowest step - about 5 to 15 minutes)"
Write-Host ""

$pyiArgs = @(
    "--log-level", "INFO",
    "--noconfirm",
    "--onedir",
    "--windowed",
    "--name", "InoLabel",
    "--distpath", $APLICATIVO_DIR,
    "--add-data=assets;assets",
    "--add-data=frontend/dist;frontend/dist",
    "--hidden-import=cv2",
    "--hidden-import=ultralytics",
    "--hidden-import=scipy.spatial",
    "--hidden-import=scipy.optimize",
    "--hidden-import=scipy.sparse",
    "--hidden-import=scipy.linalg",
    "--hidden-import=lapx",
    "--hidden-import=fastapi",
    "--hidden-import=uvicorn.logging",
    "--hidden-import=uvicorn.loops",
    "--hidden-import=uvicorn.loops.auto",
    "--hidden-import=uvicorn.protocols",
    "--hidden-import=uvicorn.protocols.http",
    "--hidden-import=uvicorn.protocols.http.auto",
    "--hidden-import=uvicorn.protocols.websockets",
    "--hidden-import=uvicorn.protocols.websockets.auto",
    "--hidden-import=uvicorn.lifespan",
    "--hidden-import=uvicorn.lifespan.on",
    "--hidden-import=aiofiles",
    "--hidden-import=multipart",
    "--hidden-import=jose",
    "--hidden-import=filelock",
    "--hidden-import=websockets",
    "--hidden-import=pdb",
    "--hidden-import=doctest",
    "--hidden-import=unittest",
    "--hidden-import=unittest.mock",
    "--hidden-import=xmlrpc",
    "--hidden-import=xmlrpc.client",
    "--collect-all=ultralytics",
    "--collect-all=matplotlib",
    "--collect-all=uvicorn",
    "--collect-all=fastapi",
    "--collect-all=starlette",
    "--collect-all=app",
    "--collect-all=tracker",
    "--exclude-module=notebook",
    "--exclude-module=jupyter",
    "--exclude-module=ipykernel",
    "--exclude-module=pytest",
    "--exclude-module=_pytest",
    "--exclude-module=multiprocessing.dummy",
    "main.py"
)

& $pythonPath -m PyInstaller @pyiArgs
if ($LASTEXITCODE -ne 0) { Write-Fail "PyInstaller failed. Check log output above." }

Write-Step "Verifying build..."
$finalExe = Join-Path $APLICATIVO_DIR "InoLabel\InoLabel.exe"
if (-not (Test-Path $finalExe)) { Write-Fail "Executavel nao encontrado em '$finalExe'." }
Write-Ok "Executavel: $finalExe"

$finalBundle = Join-Path $APLICATIVO_DIR "InoLabel"
$bundleSizeMB = [math]::Round(
    (Get-ChildItem $finalBundle -Recurse -ErrorAction SilentlyContinue |
     Measure-Object -Property Length -Sum).Sum / 1MB
)
Write-Ok "Tamanho do bundle: ${bundleSizeMB}MB"

$frontendFound = $false
foreach ($candidate in @((Join-Path $finalBundle "frontend\dist"), (Join-Path $finalBundle "_internal\frontend\dist"))) {
    if (Test-Path $candidate) {
        Write-Ok "frontend/dist incluido em: $candidate"
        $frontendFound = $true
        break
    }
}
if (-not $frontendFound) { Write-Warn "frontend/dist nao encontrado no bundle. Interface do navegador pode nao ser servida." }

$assetsFound = $false
foreach ($candidate in @((Join-Path $finalBundle "assets"), (Join-Path $finalBundle "_internal\assets"))) {
    if (Test-Path $candidate) {
        Write-Ok "assets incluidos em: $candidate"
        $assetsFound = $true
        break
    }
}
if (-not $assetsFound) { Write-Warn "assets nao encontrados no bundle. Logo pode estar faltando." }

Write-Step "Verificando modulos criticos no bundle..."
foreach ($lib in @("cv2", "PIL", "fastapi")) {
    $found = Get-ChildItem $finalBundle -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*$lib*" } |
        Select-Object -First 1
    if ($found) { Write-Ok "$lib encontrado" } else { Write-Warn "$lib pode estar faltando" }
}

Write-Step "Criando pastas de usuario em APLICATIVO\InoLabel..."
New-Item -ItemType Directory -Force (Join-Path $finalBundle "dataset") | Out-Null
New-Item -ItemType Directory -Force (Join-Path $finalBundle "outputs") | Out-Null
Write-Ok "dataset\  criado (coloque suas imagens/videos aqui)"
Write-Ok "outputs\  criado (anotacoes serao salvas aqui)"
Write-Info "Para usar modelo YOLO: coloque model.pt em $finalBundle"

Write-Step "Criando atalho no Menu Iniciar..."
try {
    $shell = New-Object -ComObject WScript.Shell
    $startMenu = $shell.SpecialFolders("Programs")
    $lnk = $shell.CreateShortcut((Join-Path $startMenu "InoLabel.lnk"))
    $lnk.TargetPath = (Resolve-Path $finalExe).Path
    $lnk.WorkingDirectory = (Resolve-Path $finalBundle).Path
    $lnk.Description = "InoLabel - ferramenta de anotacao"
    $lnk.Save()
    Write-Ok "Atalho criado em: $startMenu\InoLabel.lnk"
    Write-Info "Pesquise por 'InoLabel' no Menu Iniciar"
} catch {
    Write-Warn "Nao foi possivel criar atalho: $_"
}

$elapsed = [math]::Round($stopwatch.Elapsed.TotalSeconds)
Stop-Transcript | Out-Null

Write-Host ""
Write-Host "========================================"
Write-Host "            Build complete"
Write-Host "========================================"
Write-Host ""
Write-Host "  Pasta  : $finalBundle"
Write-Host "  Tamanho: ${bundleSizeMB}MB"
Write-Host "  Tempo  : ${elapsed}s"
Write-Host "  Log    : $LOG_FILE"
Write-Host ""
Write-Host "  Execute com:"
Write-Host "    $finalExe"
Write-Host ""
Write-Host "  ESTRUTURA DO APLICATIVO:"
Write-Host "    $finalBundle\"
Write-Host "    |- InoLabel.exe   <- executavel principal"
Write-Host "    |- _internal\     <- dependencias (nao mexa)"
Write-Host "    |- dataset\       <- coloque suas imagens/videos aqui"
Write-Host "    |- outputs\       <- anotacoes salvas automaticamente"
Write-Host "    \- model.pt       <- modelo YOLO (opcional, coloque aqui)"
Write-Host ""
