#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
#  DocuMentor — One-Command Installer
#  Installs OpenClaw (if needed) + custom workspace + deps
# ─────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}ℹ ${NC}$1"; }
success() { echo -e "${GREEN}✓ ${NC}$1"; }
warn()    { echo -e "${YELLOW}⚠ ${NC}$1"; }
error()   { echo -e "${RED}✗ ${NC}$1"; exit 1; }
header()  { echo -e "\n${BOLD}$1${NC}\n"; }

REPO_URL="https://github.com/Asphyksia/DocuMentor.git"
INSTALL_DIR="${HOME}/DocuMentor"
OPENCLAW_CONFIG_DIR="${HOME}/.openclaw"
OPENCLAW_WORKSPACE="${OPENCLAW_CONFIG_DIR}/workspace"

# ── Banner ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  📄 DocuMentor — Instalador                   ║${NC}"
echo -e "${BOLD}║  Inteligencia documental con IA               ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: System dependencies ─────────────────────────
header "1/6 · Verificando dependencias del sistema..."

# Detect OS and package manager
install_system_deps() {
    if command -v apt-get &>/dev/null; then
        info "Detectado sistema Debian/Ubuntu"
        # Check if Python3 + pip exist
        local need_install=false
        if ! command -v python3 &>/dev/null; then
            need_install=true
        fi
        if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null 2>&1; then
            need_install=true
        fi
        if ! command -v git &>/dev/null; then
            need_install=true
        fi

        if [[ "$need_install" == "true" ]]; then
            info "Instalando dependencias del sistema (python3, pip, git)..."
            if command -v sudo &>/dev/null; then
                sudo apt-get update -qq
                sudo apt-get install -y -qq python3 python3-pip python3-venv git curl
            else
                apt-get update -qq
                apt-get install -y -qq python3 python3-pip python3-venv git curl
            fi
        fi
    elif command -v dnf &>/dev/null; then
        info "Detectado sistema Fedora/RHEL"
        if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
            sudo dnf install -y -q python3 python3-pip git curl
        fi
    elif command -v pacman &>/dev/null; then
        info "Detectado sistema Arch"
        if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
            sudo pacman -S --noconfirm --quiet python python-pip git curl
        fi
    elif command -v brew &>/dev/null; then
        info "Detectado macOS con Homebrew"
        if ! command -v python3 &>/dev/null; then
            brew install python3 git curl
        fi
    fi
}

install_system_deps

# Verify critical deps
command -v git &>/dev/null || error "git no encontrado. Instálalo manualmente."
command -v curl &>/dev/null || error "curl no encontrado. Instálalo manualmente."

if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    success "Python: $PYTHON_VERSION"
else
    warn "Python3 no encontrado. El dashboard y procesamiento de docs no funcionarán."
    warn "Instálalo manualmente: https://www.python.org/downloads/"
fi

if command -v pip3 &>/dev/null; then
    success "pip3 disponible"
elif python3 -m pip --version &>/dev/null 2>&1; then
    # pip available as module, create alias function
    pip3() { python3 -m pip "$@"; }
    success "pip disponible (como módulo)"
else
    warn "pip no encontrado. Se intentará instalar después."
fi

success "Dependencias del sistema OK"

# ── Step 2: Check/Install OpenClaw ──────────────────────
header "2/6 · Verificando OpenClaw..."

# Reload PATH in case a previous install added it
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/.nvm/current/bin:$PATH"
[[ -f "$HOME/.bashrc" ]] && source "$HOME/.bashrc" 2>/dev/null || true
[[ -f "$HOME/.profile" ]] && source "$HOME/.profile" 2>/dev/null || true

if command -v openclaw &>/dev/null; then
    OPENCLAW_VERSION=$(openclaw --version 2>/dev/null || echo "unknown")
    success "OpenClaw ya instalado (${OPENCLAW_VERSION})"
else
    info "OpenClaw no encontrado. Instalando..."
    echo ""
    curl -fsSL https://openclaw.ai/install.sh | bash

    # Reload PATH after install
    export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/.nvm/current/bin:$PATH"
    [[ -f "$HOME/.bashrc" ]] && source "$HOME/.bashrc" 2>/dev/null || true
    [[ -f "$HOME/.profile" ]] && source "$HOME/.profile" 2>/dev/null || true

    # Try to find openclaw if still not in PATH
    if ! command -v openclaw &>/dev/null; then
        # Search common locations
        for dir in "$HOME/.npm-global/bin" "$HOME/.local/bin" "/usr/local/bin" "$HOME/.nvm/versions/node"/*/bin; do
            if [[ -x "$dir/openclaw" ]]; then
                export PATH="$dir:$PATH"
                break
            fi
        done
    fi

    if ! command -v openclaw &>/dev/null; then
        error "No se encontró openclaw después de instalar. Cierra y abre una terminal nueva, luego ejecuta ./install.sh de nuevo."
    fi
    success "OpenClaw instalado"
fi

# ── Step 3: Clone/Update repo ───────────────────────────
header "3/6 · Descargando workspace..."

if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Directorio existente. Actualizando..."
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || warn "No se pudo actualizar. Continuando con versión actual."
else
    # Remove dir if exists but isn't a git repo
    [[ -d "$INSTALL_DIR" ]] && rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
success "Workspace descargado: $INSTALL_DIR"

# ── Step 4: Copy workspace to OpenClaw ──────────────────
header "4/6 · Instalando workspace personalizado..."

mkdir -p "$OPENCLAW_WORKSPACE"/{skills,memory,documents}

# Core workspace files (always overwrite — these are the "product")
for f in SOUL.md AGENTS.md TOOLS.md HEARTBEAT.md; do
    cp -f "$INSTALL_DIR/workspace/$f" "$OPENCLAW_WORKSPACE/$f"
done

# USER.md: only copy if it doesn't exist (preserve onboarding data)
[[ -f "$OPENCLAW_WORKSPACE/USER.md" ]] || cp "$INSTALL_DIR/workspace/USER.md" "$OPENCLAW_WORKSPACE/USER.md"

# MEMORY.md: never overwrite (user data)
[[ -f "$OPENCLAW_WORKSPACE/MEMORY.md" ]] || touch "$OPENCLAW_WORKSPACE/MEMORY.md"

# Copy skills (always update to latest version)
cp -rf "$INSTALL_DIR/workspace/skills/"* "$OPENCLAW_WORKSPACE/skills/"

success "Workspace instalado en: $OPENCLAW_WORKSPACE"

# ── Step 5: API Key + Channel ───────────────────────────
header "5/6 · Configuración..."

CONFIG_FILE="$OPENCLAW_CONFIG_DIR/openclaw.json"
SKIP_CONFIG=""

# Check if config already exists with our models
if [[ -f "$CONFIG_FILE" ]] && grep -q "relaygpu" "$CONFIG_FILE" 2>/dev/null; then
    info "Configuración de DocuMentor detectada."
    echo -n "  ¿Reconfigurar? [s/N]: "
    read -r reconfig
    if [[ "${reconfig,,}" != "s" && "${reconfig,,}" != "si" && "${reconfig,,}" != "sí" ]]; then
        info "Manteniendo configuración actual."
        SKIP_CONFIG=true
    fi
elif [[ -f "$CONFIG_FILE" ]]; then
    info "Configuración de OpenClaw existente (sin DocuMentor)."
    info "Se sobreescribirá con la configuración de DocuMentor."
    echo -n "  ¿Continuar? [S/n]: "
    read -r cont
    if [[ "${cont,,}" == "n" || "${cont,,}" == "no" ]]; then
        info "Saltando configuración. Configúralo manualmente en: $CONFIG_FILE"
        SKIP_CONFIG=true
    fi
fi

# Reuse existing gateway token if available
if [[ -f "$CONFIG_FILE" ]]; then
    EXISTING_TOKEN=$(grep -o '"token"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*"token"[[:space:]]*:[[:space:]]*"//' | sed 's/"//')
fi

if [[ "$SKIP_CONFIG" != "true" ]]; then
    # API Key
    echo ""
    echo "  🔑 API Key de OpenGPU Relay"
    echo "  Consigue una en: https://relaygpu.com"
    echo ""
    while true; do
        echo -n "  API Key: "
        read -r OPENGPU_API_KEY
        [[ -n "$OPENGPU_API_KEY" ]] && break
        warn "La API key no puede estar vacía"
    done

    # Channel
    echo ""
    echo "  💬 Canal de comunicación"
    echo "  1) Telegram (recomendado)"
    echo "  2) WhatsApp"
    echo "  3) Discord"
    echo "  4) Omitir por ahora"
    echo ""
    while true; do
        echo -n "  Opción [1]: "
        read -r ch_choice
        ch_choice=${ch_choice:-1}
        case $ch_choice in
            1)
                CHANNEL="telegram"
                echo ""
                echo "  Crea un bot con @BotFather en Telegram y pega el token:"
                echo -n "  Bot Token: "
                read -r CHANNEL_TOKEN
                break ;;
            2)
                CHANNEL="whatsapp"
                CHANNEL_TOKEN=""
                info "WhatsApp mostrará un QR después del setup"
                break ;;
            3)
                CHANNEL="discord"
                echo ""
                echo "  Crea un bot en https://discord.com/developers/applications"
                echo -n "  Bot Token: "
                read -r CHANNEL_TOKEN
                break ;;
            4)
                CHANNEL=""
                CHANNEL_TOKEN=""
                break ;;
            *) warn "Elige 1-4" ;;
        esac
    done

    # Reuse or generate gateway token
    if [[ -n "${EXISTING_TOKEN:-}" ]]; then
        GW_TOKEN="$EXISTING_TOKEN"
        info "Reutilizando token del gateway existente"
    elif command -v openssl &>/dev/null; then
        GW_TOKEN=$(openssl rand -hex 32)
    else
        GW_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    fi

    # Build channel config
    CHANNEL_JSON=""
    case "${CHANNEL:-}" in
        telegram)
            CHANNEL_JSON=$(cat <<CEOF
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "${CHANNEL_TOKEN}",
      "dmPolicy": "allowlist",
      "allowFrom": [],
      "groupPolicy": "allowlist",
      "streaming": "partial"
    }
  },
CEOF
) ;;
        discord)
            CHANNEL_JSON=$(cat <<CEOF
  "channels": {
    "discord": {
      "enabled": true,
      "botToken": "${CHANNEL_TOKEN}",
      "dmPolicy": "allowlist",
      "allowFrom": [],
      "groupPolicy": "allowlist"
    }
  },
CEOF
) ;;
        whatsapp)
            CHANNEL_JSON=$(cat <<CEOF
  "channels": {
    "whatsapp": {
      "enabled": true,
      "dmPolicy": "allowlist",
      "allowFrom": []
    }
  },
CEOF
) ;;
    esac

    # Write config
    cat > "$CONFIG_FILE" <<EOF
{
  "models": {
    "providers": {
      "relaygpu-anthropic": {
        "baseUrl": "https://relay.opengpu.network/v2/anthropic/v1/",
        "apiKey": "${OPENGPU_API_KEY}",
        "api": "anthropic-messages",
        "models": [
          {
            "id": "anthropic/claude-sonnet-4-6",
            "name": "Claude Sonnet 4-6 (OpenGPU)",
            "api": "anthropic-messages",
            "reasoning": true,
            "input": ["text"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 200000,
            "maxTokens": 64000
          }
        ]
      },
      "relaygpu-openai": {
        "baseUrl": "https://relay.opengpu.network/v2/openai/v1/",
        "apiKey": "${OPENGPU_API_KEY}",
        "api": "openai-completions",
        "models": [
          {
            "id": "moonshotai/kimi-k2.5",
            "name": "Kimi K2.5 (OpenGPU)",
            "api": "openai-completions",
            "reasoning": true,
            "input": ["text"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 128000,
            "maxTokens": 65536
          },
          {
            "id": "deepseek-ai/DeepSeek-V3.1",
            "name": "DeepSeek V3.1 (OpenGPU)",
            "api": "openai-completions",
            "reasoning": true,
            "input": ["text"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 128000,
            "maxTokens": 65536
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "relaygpu-openai/moonshotai/kimi-k2.5"
      },
      "workspace": "${OPENCLAW_WORKSPACE}"
    }
  },
${CHANNEL_JSON}
  "gateway": {
    "mode": "local",
    "auth": {
      "token": "${GW_TOKEN}"
    }
  }
}
EOF

    success "Configuración guardada: $CONFIG_FILE"
fi

# ── Step 6: Install Python deps + Start ─────────────────
header "6/6 · Instalando dependencias y arrancando..."

# Install Python dependencies
PYTHON_DEPS="pdfplumber openpyxl python-docx matplotlib streamlit pandas"
PIP_INSTALLED=false

if command -v pip3 &>/dev/null; then
    PIP_CMD="pip3"
elif python3 -m pip --version &>/dev/null 2>&1; then
    PIP_CMD="python3 -m pip"
else
    PIP_CMD=""
fi

if [[ -n "$PIP_CMD" ]]; then
    info "Instalando dependencias Python..."
    if $PIP_CMD install -q $PYTHON_DEPS 2>/dev/null; then
        PIP_INSTALLED=true
    elif $PIP_CMD install --user -q $PYTHON_DEPS 2>/dev/null; then
        PIP_INSTALLED=true
    elif $PIP_CMD install --break-system-packages -q $PYTHON_DEPS 2>/dev/null; then
        PIP_INSTALLED=true
    elif $PIP_CMD install --user --break-system-packages -q $PYTHON_DEPS 2>/dev/null; then
        PIP_INSTALLED=true
    fi

    if [[ "$PIP_INSTALLED" == "true" ]]; then
        success "Dependencias Python instaladas"
    else
        warn "No se pudieron instalar algunas dependencias."
        warn "Prueba manualmente: $PIP_CMD install $PYTHON_DEPS"
    fi
else
    warn "pip no disponible. Instala las dependencias manualmente:"
    warn "  pip3 install $PYTHON_DEPS"
fi

# Sync service token and start/restart gateway
info "Iniciando OpenClaw Gateway..."
if command -v openclaw &>/dev/null; then
    # Fix service if needed
    openclaw doctor --repair 2>/dev/null || true
    # Force install to sync token
    openclaw gateway install --force 2>/dev/null || true
    # Start or restart
    openclaw gateway restart 2>/dev/null || openclaw gateway start 2>/dev/null || \
    warn "No se pudo iniciar el gateway. Ejecuta: openclaw gateway start"
    success "Gateway iniciado"
fi

# ── Done ────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✅ ¡DocuMentor instalado correctamente!${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${NC}"
echo ""
echo "  📄 Workspace:  $OPENCLAW_WORKSPACE"
echo "  ⚙️  Config:     $CONFIG_FILE"
echo ""

if [[ -n "${CHANNEL:-}" && "${CHANNEL:-}" != "" ]]; then
    echo "  💬 Canal: ${CHANNEL}"
    echo ""
    echo "  ⚠️  IMPORTANTE: Añade tu ID de usuario a 'allowFrom' en:"
    echo "     $CONFIG_FILE"
    echo ""
    echo "     Cómo encontrar tu ID:"
    echo "     1. Manda un mensaje al bot"
    echo "     2. Mira los logs: openclaw gateway logs | tail -20"
    echo "     3. Busca tu ID numérico"
    echo "     4. Añádelo a allowFrom: [\"TU_ID\"]"
    echo "     5. Reinicia: openclaw gateway restart"
    echo ""
fi

if [[ "${CHANNEL:-}" == "whatsapp" ]]; then
    echo "  📱 Para vincular WhatsApp: openclaw channels login"
    echo ""
fi

# Gateway token display
if [[ -n "${GW_TOKEN:-}" ]]; then
    echo "  🔑 Token del dashboard: ${GW_TOKEN}"
    echo "     (guárdalo para acceder al dashboard web de OpenClaw)"
    echo ""
fi

echo "  📊 Iniciar dashboard visual:"
echo "     cd $INSTALL_DIR && streamlit run dashboard/app.py"
echo ""
echo "  🎓 DocuMentor está listo. ¡Manda un mensaje al bot para empezar!"
echo ""
echo "  ─────────────────────────────────────────────"
echo "  Comandos útiles:"
echo "     openclaw gateway status     # Ver estado"
echo "     openclaw gateway restart    # Reiniciar"
echo "     openclaw gateway logs       # Ver logs"
echo "     openclaw update             # Actualizar OpenClaw"
echo ""
echo "  📖 Docs:     https://docs.openclaw.ai"
echo "  💬 Soporte:  https://discord.gg/clawd"
echo ""
