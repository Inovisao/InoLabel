#!/usr/bin/env bash
# InoLabel build script — verifies dependencies and builds a self-contained executable.
# Usage:
#   bash build.sh           # auto-detect OS
#   bash build.sh --os linux
#   bash build.sh --os windows

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  [OK]${NC} $*"; }
warn() { echo -e "${YELLOW}  [AVISO]${NC} $*"; }
fail() { echo -e "${RED}  [ERRO]${NC} $*"; exit 1; }
info() { echo -e "${BLUE}  [INFO]${NC} $*"; }
step() { echo -e "\n${BOLD}==> $*${NC}"; }

# ── Timing ────────────────────────────────────────────────────────────────────
BUILD_START=$(date +%s)
PHASE_START=$BUILD_START

elapsed_since() {
    local now; now=$(date +%s)
    echo $(( now - $1 ))s
}

phase_done() {
    local elapsed; elapsed=$(elapsed_since "$PHASE_START")
    echo -e "  ${BLUE}(${elapsed})${NC}"
    PHASE_START=$(date +%s)
}

# ── Build log ─────────────────────────────────────────────────────────────────
LOG_DIR="dist/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/build_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1
info "Log salvo em: $LOG_FILE"

# ── Lockfile (previne builds concorrentes) ────────────────────────────────────
LOCKFILE="/tmp/inolabel_build.lock"
if [[ -f "$LOCKFILE" ]]; then
    LOCK_PID=$(cat "$LOCKFILE" 2>/dev/null || echo "?")
    fail "Outro build ja esta rodando (PID $LOCK_PID). Remova $LOCKFILE se isso for um engano."
fi
echo $$ > "$LOCKFILE"

# ── Cleanup ao sair (Ctrl+C ou erro) ─────────────────────────────────────────
cleanup() {
    rm -f "$LOCKFILE"
    if [[ "${BUILD_FAILED:-0}" == "1" ]]; then
        echo ""
        warn "Build interrompido. Arquivos temporarios podem ter ficado em build/ e dist/."
        warn "Rode 'bash build.sh' novamente para recomecar — o script detecta builds corrompidos."
    fi
}
trap cleanup EXIT
trap 'BUILD_FAILED=1; exit 1' INT TERM

# ── Parse args ────────────────────────────────────────────────────────────────
TARGET_OS=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --os) TARGET_OS="$2"; shift 2 ;;
        *) fail "Argumento desconhecido: $1. Use --os linux ou --os windows." ;;
    esac
done

# ── Auto-detect OS ────────────────────────────────────────────────────────────
if [[ -z "$TARGET_OS" ]]; then
    case "$(uname -s)" in
        Linux*)               TARGET_OS="linux" ;;
        Darwin*)              TARGET_OS="mac" ;;
        CYGWIN*|MINGW*|MSYS*) TARGET_OS="windows" ;;
        *) fail "SO nao reconhecido. Use --os linux ou --os windows." ;;
    esac
fi

if [[ "$TARGET_OS" == "windows" ]]; then
    EXE_NAME="InoLabel.exe"
    SEPARATOR=";"
else
    EXE_NAME="InoLabel"
    SEPARATOR=":"
fi

DIST_DIR="dist/InoLabel-$TARGET_OS"
BUNDLE_DIR="$DIST_DIR/InoLabel"
EXE_PATH="$BUNDLE_DIR/$EXE_NAME"

ask_yes_no() {
    local prompt="$1"
    while true; do
        echo -en "  ${prompt} [s/n] "
        read -r answer
        case "$answer" in
            s|S|sim|Sim|SIM) return 0 ;;
            n|N|nao|Nao|NAO) return 1 ;;
            *) echo "  Responda s (sim) ou n (nao)." ;;
        esac
    done
}

_clean_build() {
    info "Removendo build anterior em $DIST_DIR ..."
    rm -rf "$DIST_DIR"
    [[ -d "build/InoLabel" ]] && rm -rf "build/InoLabel" && info "Cache build/ removido."
    [[ -f "InoLabel.spec" ]]  && rm -f  "InoLabel.spec"  && info "InoLabel.spec removido."
    ok "Build anterior removido."
}

_build_is_complete() {
    # Executable exists AND assets are present (PyInstaller 6+ puts them in _internal/)
    [[ -f "$EXE_PATH" ]] && \
    { [[ -d "$BUNDLE_DIR/assets" ]] || [[ -d "$BUNDLE_DIR/_internal/assets" ]]; }
}

_build_is_partial() {
    [[ -d "$BUNDLE_DIR" ]] && ! _build_is_complete
}

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║        InoLabel — Build Script       ║"
echo "╚══════════════════════════════════════╝"
echo "  Alvo : $TARGET_OS"
echo "  Data : $(date '+%d/%m/%Y %H:%M:%S')"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# FASE 0 — Verificar instalação existente
# ══════════════════════════════════════════════════════════════════════════════
step "Verificando instalacao existente..."

if _build_is_complete; then
    echo ""
    ok "Build completo encontrado em: $BUNDLE_DIR"
    info "Tamanho: $(du -sh "$BUNDLE_DIR" 2>/dev/null | cut -f1)"
    echo ""
    echo "  O que voce deseja fazer?"
    echo "    1) Reinstalar (apaga o build atual e gera um novo)"
    echo "    2) Continuar usando o build existente"
    echo ""
    while true; do
        echo -n "  Escolha [1/2]: "
        read -r choice
        case "$choice" in
            1) _clean_build; break ;;
            2)
                echo ""
                info "Usando build existente. Para rodar: $EXE_PATH"
                echo ""
                exit 0
                ;;
            *) echo "  Digite 1 ou 2." ;;
        esac
    done

elif _build_is_partial; then
    echo ""
    warn "Instalacao incompleta ou corrompida detectada em: $BUNDLE_DIR"
    CORRUPTION_DETAILS=()
    [[ ! -f "$EXE_PATH" ]]          && CORRUPTION_DETAILS+=("executavel '$EXE_NAME' ausente")
    [[ ! -d "$BUNDLE_DIR/assets" ]] && CORRUPTION_DETAILS+=("pasta 'assets/' ausente")
    echo "  Problemas encontrados:"
    for d in "${CORRUPTION_DETAILS[@]}"; do echo -e "    ${RED}✗${NC} $d"; done
    echo ""
    if ask_yes_no "Limpar e reconstruir?"; then
        _clean_build
    else
        fail "Build corrompido mantido. Remova manualmente '$DIST_DIR' e rode novamente."
    fi
else
    ok "Nenhum build anterior — iniciando build limpo."
fi

phase_done

# ══════════════════════════════════════════════════════════════════════════════
# FASE 1 — Verificação de pré-requisitos
# ══════════════════════════════════════════════════════════════════════════════
step "Verificando pre-requisitos..."

# Diretório correto
[[ -f "main.py" ]]          || fail "main.py nao encontrado. Execute build.sh a partir da raiz do projeto."
[[ -f "requirements.txt" ]] || fail "requirements.txt nao encontrado."
ok "Raiz do projeto"

# ── Conda: instalar se ausente ────────────────────────────────────────────────
CONDA_ENV_NAME="inolabel"

_install_miniconda() {
    info "Baixando Miniconda..."
    local installer
    if [[ "$TARGET_OS" == "linux" ]]; then
        installer="/tmp/miniconda_installer.sh"
        curl -fsSL "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" -o "$installer"
    elif [[ "$TARGET_OS" == "mac" ]]; then
        installer="/tmp/miniconda_installer.sh"
        curl -fsSL "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh" -o "$installer"
    else
        fail "Instale o Miniconda manualmente em https://docs.conda.io/en/latest/miniconda.html e rode novamente."
    fi
    bash "$installer" -b -p "$HOME/miniconda3"
    rm -f "$installer"
    # Ativar conda na sessao atual
    # shellcheck disable=SC1091
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda init bash &>/dev/null || true
    ok "Miniconda instalado em $HOME/miniconda3"
}

# Localizar conda (pode estar em paths nao-padrao)
CONDA_CMD=""
for candidate in \
    "$(command -v conda 2>/dev/null)" \
    "$HOME/miniconda3/bin/conda" \
    "$HOME/anaconda3/bin/conda" \
    "/opt/conda/bin/conda"; do
    if [[ -x "$candidate" ]]; then
        CONDA_CMD="$candidate"
        break
    fi
done

if [[ -z "$CONDA_CMD" ]]; then
    warn "Conda nao encontrado. Instalando Miniconda automaticamente..."
    _install_miniconda
    CONDA_CMD="$HOME/miniconda3/bin/conda"
fi

# Garantir que conda esta disponivel no PATH desta sessao
CONDA_BASE=$("$CONDA_CMD" info --base 2>/dev/null)
# shellcheck disable=SC1091
source "$CONDA_BASE/etc/profile.d/conda.sh" 2>/dev/null || true
ok "Conda: $("$CONDA_CMD" --version)"

# ── Ambiente conda: criar se ausente ─────────────────────────────────────────
if "$CONDA_CMD" env list | grep -qE "^${CONDA_ENV_NAME}\s"; then
    ok "Ambiente conda '$CONDA_ENV_NAME' encontrado."
else
    info "Ambiente conda '$CONDA_ENV_NAME' nao encontrado. Criando com Python 3.9..."
    "$CONDA_CMD" create -n "$CONDA_ENV_NAME" python=3.9 -y 2>&1 | \
        grep -E "^(Collecting|Downloading|Installing|Successfully|Preparing|Executing)" | \
        while IFS= read -r line; do echo "  $line"; done
    ok "Ambiente '$CONDA_ENV_NAME' criado com Python 3.9."
fi

# ── Ativar o ambiente e usar o Python dele ────────────────────────────────────
conda activate "$CONDA_ENV_NAME" 2>/dev/null || true
PYTHON="$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=$(conda run -n "$CONDA_ENV_NAME" which python 2>/dev/null)
[[ -x "$PYTHON" ]] || fail "Nao foi possivel localizar o Python do ambiente '$CONDA_ENV_NAME'."

PYTHON_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")
PYTHON_VERSION="${PYTHON_MAJOR}.${PYTHON_MINOR}"

if [[ "$PYTHON_MAJOR" -ne 3 || "$PYTHON_MINOR" -lt 9 || "$PYTHON_MINOR" -gt 10 ]]; then
    fail "Python $PYTHON_VERSION no ambiente '$CONDA_ENV_NAME' nao e compativel (necessario 3.9 ou 3.10)."
fi
ok "Python $PYTHON_VERSION (ambiente: $CONDA_ENV_NAME)"

info "Ambiente ativo: ${CONDA_DEFAULT_ENV:-$CONDA_ENV_NAME}"

# Tkinter
if ! $PYTHON -c "import tkinter" &>/dev/null 2>&1; then
    warn "Tkinter nao encontrado — interface grafica nao funcionara."
    [[ "$TARGET_OS" == "linux" ]] && echo "       Instale: sudo apt-get install python3-tk"
else
    ok "Tkinter"
fi

# pip — garante versao compativel com Python 3.9 (pip>=24 requer Python 3.10+)
_pip_ok() { $PYTHON -m pip --version &>/dev/null 2>&1; }
_pip_broken() {
    $PYTHON -m pip --version 2>&1 | grep -q "slots" || \
    $PYTHON -c "import pip" 2>&1 | grep -q "slots"
}

if ! _pip_ok || _pip_broken; then
    info "pip ausente ou incompativel com Python 3.9 — corrigindo..."
    # Usar ensurepip para obter um pip funcional minimo
    $PYTHON -m ensurepip --default-pip &>/dev/null 2>&1 || true
    # Forcar versao compativel com Python 3.9 (pip<24 nao usa slots=True)
    $PYTHON -m pip install "pip>=21.3,<24" --upgrade --quiet 2>/dev/null || \
        "$CONDA_CMD" install -n "$CONDA_ENV_NAME" "pip>=21.3,<24" -y --quiet &>/dev/null || \
        fail "Nao foi possivel instalar pip compativel no ambiente '$CONDA_ENV_NAME'."
    _pip_ok || fail "pip ainda nao funciona apos reinstalacao."
fi
ok "pip $($PYTHON -m pip --version 2>/dev/null | awk '{print $2}')"

# Linux: gcc, cmake
if [[ "$TARGET_OS" == "linux" ]]; then
    MISSING_TOOLS=()
    for cmd in gcc cmake; do
        if ! command -v "$cmd" &>/dev/null; then
            MISSING_TOOLS+=("$cmd")
            warn "$cmd ausente — necessario para 'lap' e 'cython-bbox'."
        else
            ok "$cmd ($(command -v $cmd))"
        fi
    done
    if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
        echo "    Instale: sudo apt-get install build-essential python3-dev cmake"
        fail "Ferramentas de compilacao ausentes."
    fi
    # libGL
    if ! ldconfig -p 2>/dev/null | grep -q "libGL.so"; then
        warn "libGL ausente — instale: sudo apt-get install libgl1"
    else
        ok "libGL"
    fi
fi

# Versao minima do PyInstaller
MIN_PYINSTALLER="5.0"
if $PYTHON -m PyInstaller --version &>/dev/null 2>&1; then
    PI_VERSION=$($PYTHON -m PyInstaller --version 2>&1)
    PI_MAJOR=$(echo "$PI_VERSION" | cut -d. -f1)
    if [[ "$PI_MAJOR" -lt 5 ]]; then
        warn "PyInstaller $PI_VERSION e muito antigo (minimo $MIN_PYINSTALLER). Sera atualizado."
        $PYTHON -m pip install "pyinstaller>=$MIN_PYINSTALLER" --quiet
    fi
fi

# Espaco em disco (bundle ~2GB, precisa ~4GB livres para build)
REQUIRED_MB=4096
if command -v df &>/dev/null; then
    AVAILABLE_MB=$(df -m . | awk 'NR==2 {print $4}')
    if [[ "$AVAILABLE_MB" -lt "$REQUIRED_MB" ]]; then
        fail "Espaco insuficiente: ${AVAILABLE_MB}MB disponivel, ${REQUIRED_MB}MB necessario."
    fi
    ok "Espaco em disco: ${AVAILABLE_MB}MB disponivel"
fi

phase_done

# ══════════════════════════════════════════════════════════════════════════════
# FASE 2 — Instalação e validação de dependências Python
# ══════════════════════════════════════════════════════════════════════════════
step "Instalando dependencias Python..."
echo "  (pode levar alguns minutos na primeira vez...)"
echo ""

$PYTHON -m pip install -r requirements.txt --progress-bar on 2>&1 | \
    grep -E "^(Collecting|Downloading|Installing|Successfully|Requirement already)" | \
    while IFS= read -r line; do echo "  $line"; done
ok "requirements.txt instalado"

if ! $PYTHON -m PyInstaller --version &>/dev/null 2>&1; then
    echo "  Instalando PyInstaller..."
    $PYTHON -m pip install "pyinstaller>=$MIN_PYINSTALLER" --progress-bar on 2>&1 | \
        grep -E "^(Collecting|Downloading|Installing|Successfully|Requirement already)" | \
        while IFS= read -r line; do echo "  $line"; done
fi
PI_VERSION=$($PYTHON -m PyInstaller --version 2>&1)
ok "PyInstaller $PI_VERSION"

# Validar imports criticos — garante que os pacotes nao estao so instalados mas funcionam
step "Validando imports criticos..."
IMPORT_ERRORS=()
for pkg in "tkinter" "cv2" "PIL" "numpy" "ultralytics"; do
    if ! $PYTHON -c "import $pkg" &>/dev/null 2>&1; then
        IMPORT_ERRORS+=("$pkg")
        warn "Falha ao importar '$pkg' — pacote pode estar corrompido."
    else
        ok "import $pkg"
    fi
done
if [[ ${#IMPORT_ERRORS[@]} -gt 0 ]]; then
    echo ""
    echo "  Tentando reinstalar pacotes com falha..."
    for pkg in "${IMPORT_ERRORS[@]}"; do
        info "Reinstalando $pkg..."
        $PYTHON -m pip install --force-reinstall "$pkg" --quiet && ok "$pkg reinstalado" || warn "Falha ao reinstalar $pkg"
    done
    # Verificar novamente
    STILL_BROKEN=()
    for pkg in "${IMPORT_ERRORS[@]}"; do
        $PYTHON -c "import $pkg" &>/dev/null 2>&1 || STILL_BROKEN+=("$pkg")
    done
    [[ ${#STILL_BROKEN[@]} -gt 0 ]] && fail "Pacotes ainda com falha apos reinstalacao: ${STILL_BROKEN[*]}"
fi

phase_done

# ══════════════════════════════════════════════════════════════════════════════
# FASE 3 — Build
# ══════════════════════════════════════════════════════════════════════════════
step "Gerando executavel com PyInstaller..."
echo "  (etapa mais demorada — 5-15 minutos dependendo da maquina)"
echo ""

# Modulos excluidos para reduzir tamanho do bundle
# REGRA: nao excluir nada que ultralytics/torch possam importar dinamicamente
# matplotlib NAO esta aqui — ultralytics/models/yolo/semantic usa internamente
EXCLUDES=(
    notebook jupyter ipykernel
    pytest _pytest
    tkinter.test turtle
    multiprocessing.dummy
)
EXCLUDE_ARGS=()
for mod in "${EXCLUDES[@]}"; do
    EXCLUDE_ARGS+=("--exclude-module" "$mod")
done

STRIP_ARG=()
[[ "$TARGET_OS" == "linux" ]] && STRIP_ARG=("--strip")

$PYTHON -m PyInstaller \
    --log-level INFO \
    --noconfirm \
    --onedir \
    --windowed \
    --name "InoLabel" \
    --distpath "$DIST_DIR" \
    --add-data "assets${SEPARATOR}assets" \
    --add-data "app/ui/theme${SEPARATOR}app/ui/theme" \
    --hidden-import "PIL._tkinter_finder" \
    --hidden-import "cv2" \
    --hidden-import "ultralytics" \
    --hidden-import "scipy.spatial" \
    --hidden-import "scipy.optimize" \
    --hidden-import "scipy.sparse" \
    --hidden-import "scipy.linalg" \
    --hidden-import "cython_bbox" \
    --hidden-import "lap" \
    --hidden-import "pdb" \
    --hidden-import "doctest" \
    --hidden-import "unittest" \
    --hidden-import "unittest.mock" \
    --hidden-import "xmlrpc" \
    --hidden-import "xmlrpc.client" \
    --collect-all "ultralytics" \
    --collect-all "matplotlib" \
    --collect-all "tkinter" \
    --collect-all "tracker" \
    "${EXCLUDE_ARGS[@]}" \
    "${STRIP_ARG[@]}" \
    main.py

phase_done

# ══════════════════════════════════════════════════════════════════════════════
# FASE 4 — Verificação pós-build
# ══════════════════════════════════════════════════════════════════════════════
step "Verificando build..."

# Executavel existe e tem permissao de execucao
[[ -f "$EXE_PATH" ]] || fail "Executavel nao encontrado em $EXE_PATH — build falhou."
[[ "$TARGET_OS" != "windows" ]] && chmod +x "$EXE_PATH"
ok "Executavel: $EXE_PATH"
ok "Tamanho do bundle: $(du -sh "$BUNDLE_DIR" 2>/dev/null | cut -f1)"

# Assets incluidos — PyInstaller 6+ coloca em _internal/, versoes antigas na raiz
ASSETS_FOUND=0
for assets_candidate in "$BUNDLE_DIR/assets" "$BUNDLE_DIR/_internal/assets"; do
    if [[ -d "$assets_candidate" ]]; then
        ok "assets/ incluido em: $assets_candidate"
        ASSETS_FOUND=1
        break
    fi
done
[[ "$ASSETS_FOUND" -eq 0 ]] && warn "assets/ nao encontrado no bundle — logo pode nao aparecer."

# Modulos criticos presentes no bundle
step "Verificando modulos criticos no bundle..."
CRITICAL_MISSING=()
for lib in "cv2" "PIL" "tkinter"; do
    if ! find "$BUNDLE_DIR" \( -name "${lib}*" -o -name "*${lib}*" \) 2>/dev/null | grep -q .; then
        CRITICAL_MISSING+=("$lib")
    else
        ok "$lib presente"
    fi
done
[[ ${#CRITICAL_MISSING[@]} -gt 0 ]] && warn "Modulos possivelmente ausentes: ${CRITICAL_MISSING[*]}"

# Smoke test — inicializa o processo e verifica que nao crashou imediatamente
step "Smoke test do executavel..."
if [[ "$TARGET_OS" != "windows" ]] && command -v timeout &>/dev/null; then
    # Roda com DISPLAY falso para nao abrir janela; espera 3s e verifica exit code
    # Exit code 1 = erro de import/crash; outros = normal (janela nao abriu = esperado)
    SMOKE_OUTPUT=$(DISPLAY=:99 timeout 3s "$EXE_PATH" 2>&1 || true)
    if echo "$SMOKE_OUTPUT" | grep -qiE "ModuleNotFoundError|ImportError|Traceback"; then
        warn "Smoke test detectou erro de import:"
        echo "$SMOKE_OUTPUT" | grep -iE "ModuleNotFoundError|ImportError|No module" | head -5 | while IFS= read -r line; do echo "    $line"; done
        warn "O executavel pode nao funcionar corretamente."
    else
        ok "Smoke test passou — sem erros de import"
    fi
else
    info "Smoke test ignorado (Windows ou 'timeout' indisponivel)."
fi

phase_done

# ══════════════════════════════════════════════════════════════════════════════
# FASE 5 — Registrar no sistema (atalho na lista de aplicativos)
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$TARGET_OS" == "linux" ]]; then
    step "Registrando InoLabel na lista de aplicativos (Linux)..."

    ABS_EXE=$(realpath "$EXE_PATH")
    ABS_ICON=$(realpath "$BUNDLE_DIR/_internal/assets/inovisao.png" 2>/dev/null || \
               realpath "$BUNDLE_DIR/assets/inovisao.png" 2>/dev/null || \
               realpath "assets/inovisao.png" 2>/dev/null || echo "")

    DESKTOP_DIR="$HOME/.local/share/applications"
    DESKTOP_FILE="$DESKTOP_DIR/inolabel.desktop"
    mkdir -p "$DESKTOP_DIR"

    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=InoLabel
GenericName=Anotador de Imagens
Comment=Ferramenta de anotacao de imagens e videos — Laboratorio Inovisao
Exec=$ABS_EXE
Icon=$ABS_ICON
Terminal=false
Categories=Science;Education;Graphics;
Keywords=anotacao;dataset;visao computacional;yolo;tracking;
StartupNotify=true
StartupWMClass=InoLabel
EOF

    chmod 644 "$DESKTOP_FILE"

    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi

    ok "Atalho criado: $DESKTOP_FILE"
    [[ -n "$ABS_ICON" ]] && ok "Icone: $ABS_ICON" || warn "Icone nao encontrado — atalho sem imagem."
    info "Pressione Super e pesquise 'InoLabel' para abrir."

elif [[ "$TARGET_OS" == "windows" ]]; then
    step "Registrando InoLabel no Menu Iniciar (Windows)..."

    if ! command -v powershell.exe &>/dev/null && ! command -v powershell &>/dev/null; then
        warn "PowerShell nao encontrado — atalho do Menu Iniciar nao foi criado."
        warn "Crie manualmente um atalho para: $(cygpath -w "$EXE_PATH" 2>/dev/null || echo "$EXE_PATH")"
    else
        PS=$(command -v powershell.exe 2>/dev/null || command -v powershell)

        # Converter paths para formato Windows
        WIN_EXE=$(cygpath -w "$(realpath "$EXE_PATH")" 2>/dev/null || echo "$EXE_PATH")
        WIN_ICON=$(cygpath -w "$(realpath "$BUNDLE_DIR/_internal/assets/inovisao.png" 2>/dev/null || \
                                 realpath "$BUNDLE_DIR/assets/inovisao.png" 2>/dev/null || \
                                 echo "")" 2>/dev/null || echo "")

        # Criar atalho .lnk no Menu Iniciar do usuario
        "$PS" -NoProfile -NonInteractive -Command "
            \$shell    = New-Object -ComObject WScript.Shell
            \$startMenu = \$shell.SpecialFolders('Programs')
            \$lnk      = \$shell.CreateShortcut(\"\$startMenu\\InoLabel.lnk\")
            \$lnk.TargetPath       = '$WIN_EXE'
            \$lnk.WorkingDirectory = Split-Path '$WIN_EXE'
            \$lnk.Description      = 'Ferramenta de anotacao de imagens e videos — Inovisao'
            $([ -n "$WIN_ICON" ] && echo "\$lnk.IconLocation = '$WIN_ICON,0'")
            \$lnk.Save()
            Write-Host 'Atalho criado em:' \$startMenu
        " 2>&1 | while IFS= read -r line; do echo "  $line"; done

        if [[ $? -eq 0 ]]; then
            ok "Atalho criado no Menu Iniciar."
            info "Clique em Iniciar e pesquise 'InoLabel' para abrir."
        else
            warn "Falha ao criar atalho — tente executar o build como Administrador."
        fi
    fi
fi

phase_done

# ══════════════════════════════════════════════════════════════════════════════
# Sumario final
# ══════════════════════════════════════════════════════════════════════════════
TOTAL=$(elapsed_since "$BUILD_START")
echo ""
echo "╔══════════════════════════════════════╗"
echo "║           Build concluido!           ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Saida   : $BUNDLE_DIR"
echo "  Tamanho : $(du -sh "$BUNDLE_DIR" 2>/dev/null | cut -f1)"
echo "  Tempo   : $TOTAL"
echo "  Log     : $LOG_FILE"
echo ""
echo "  Para rodar:"
if [[ "$TARGET_OS" == "windows" ]]; then
    echo "    $BUNDLE_DIR\\$EXE_NAME"
else
    echo "    $BUNDLE_DIR/$EXE_NAME"
fi
echo ""
echo "  IMPORTANTE: coloque model.pt e dataset/ ao lado do executavel."
echo ""
