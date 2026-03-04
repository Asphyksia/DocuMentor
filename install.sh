#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
#  DocuMentor — One-Command Installer
#  Installs OpenClaw (if needed) + custom workspace
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

# ── Step 1: Check/Install OpenClaw ──────────────────────
header "1/5 · Verificando OpenClaw..."

if command -v openclaw &>/dev/null; then
    OPENCLAW_VERSION=$(openclaw --version 2>/dev/null || echo "unknown")
    success "OpenClaw ya instalado (${OPENCLAW_VERSION})"
else
    info "OpenClaw no encontrado. Instalando..."
    curl -fsSL https://openclaw.ai/install.sh | bash

    if ! command -v openclaw &>/dev/null; then
        error "La instalación de OpenClaw falló. Instálalo manualmente: https://docs.openclaw.ai"
    fi
    success "OpenClaw instalado"
fi

# ── Step 2: Clone/Update repo ───────────────────────────
header "2/5 · Descargando workspace..."

if [[ -d "$INSTALL_DIR" ]]; then
    info "Directorio existente. Actualizando..."
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || warn "No se pudo actualizar. Continuando con versión actual."
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
success "Workspace descargado: $INSTALL_DIR"

# ── Step 3: Copy workspace to OpenClaw ──────────────────
header "3/5 · Instalando workspace personalizado..."

mkdir -p "$OPENCLAW_WORKSPACE"
mkdir -p "$OPENCLAW_WORKSPACE/skills"
mkdir -p "$OPENCLAW_WORKSPACE/memory"
mkdir -p "$OPENCLAW_WORKSPACE/documents"

# Copy workspace files (don't overwrite memory or user config if they exist)
cp -f "$INSTALL_DIR/workspace/SOUL.md" "$OPENCLAW_WORKSPACE/SOUL.md"
cp -f "$INSTALL_DIR/workspace/AGENTS.md" "$OPENCLAW_WORKSPACE/AGENTS.md"
cp -f "$INSTALL_DIR/workspace/TOOLS.md" "$OPENCLAW_WORKSPACE/TOOLS.md"
cp -f "$INSTALL_DIR/workspace/HEARTBEAT.md" "$OPENCLAW_WORKSPACE/HEARTBEAT.md"

# USER.md: only copy if it doesn't exist (preserve onboarding data)
[[ -f "$OPENCLAW_WORKSPACE/USER.md" ]] || cp "$INSTALL_DIR/workspace/USER.md" "$OPENCLAW_WORKSPACE/USER.md"

# Copy skills (always update)
cp -rf "$INSTALL_DIR/workspace/skills/"* "$OPENCLAW_WORKSPACE/skills/"

success "Workspace instalado en: $OPENCLAW_WORKSPACE"

# ── Step 4: API Key + Channel ───────────────────────────
header "4/5 · Configuración..."

CONFIG_FILE="$OPENCLAW_CONFIG_DIR/openclaw.json"

# Check if config already exists
if [[ -f "$CONFIG_FILE" ]]; then
    info "Configuración existente detectada."
    echo -n "  ¿Reconfigurar? [s/N]: "
    read -r reconfig
    if [[ "${reconfig,,}" != "s" && "${reconfig,,}" != "si" && "${reconfig,,}" != "sí" ]]; then
        info "Manteniendo configuración actual."
        SKIP_CONFIG=true
    fi
fi

if [[ "${SKIP_CONFIG:-}" != "true" ]]; then
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

    # Generate gateway token
    if command -v openssl &>/dev/null; then
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

# ── Step 5: Install Python deps + Start ─────────────────
header "5/5 · Instalando dependencias..."

# Install Python dependencies
if command -v pip3 &>/dev/null; then
    pip3 install -q pdfplumber openpyxl python-docx matplotlib streamlit pandas 2>/dev/null || \
    pip3 install --user -q pdfplumber openpyxl python-docx matplotlib streamlit pandas 2>/dev/null || \
    warn "No se pudieron instalar dependencias Python. Instálalas manualmente: pip3 install -r $INSTALL_DIR/dashboard/requirements.txt"
    success "Dependencias Python instaladas"
elif command -v pip &>/dev/null; then
    pip install -q pdfplumber openpyxl python-docx matplotlib streamlit pandas 2>/dev/null || \
    warn "No se pudieron instalar dependencias. Instálalas manualmente."
else
    warn "pip no encontrado. Instala Python 3 y luego: pip3 install -r $INSTALL_DIR/dashboard/requirements.txt"
fi

# Start/restart OpenClaw gateway
info "Iniciando OpenClaw Gateway..."
if command -v openclaw &>/dev/null; then
    openclaw gateway restart 2>/dev/null || openclaw gateway start 2>/dev/null || \
    warn "No se pudo iniciar el gateway automáticamente. Ejecuta: openclaw gateway start"
fi

# ── Done ────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✅ ¡Instalación completada!${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${NC}"
echo ""
echo "  📄 Workspace:  $OPENCLAW_WORKSPACE"
echo "  ⚙️  Config:     $CONFIG_FILE"
echo "  📊 Dashboard:  cd $INSTALL_DIR && streamlit run dashboard/app.py"
echo ""
echo "  🎓 DocuMentor está listo."
echo ""

if [[ -n "${CHANNEL:-}" ]]; then
    echo "  ⚠️  Añade tu ID de usuario a 'allowFrom' en el config."
    echo "     Luego reinicia: openclaw gateway restart"
    echo ""
fi

if [[ "${CHANNEL:-}" == "whatsapp" ]]; then
    echo "  📱 Para vincular WhatsApp: openclaw channels login"
    echo ""
fi

echo "  📖 Docs:     https://docs.openclaw.ai"
echo "  💬 Soporte:  https://discord.gg/clawd"
echo ""
echo "  Comandos útiles:"
echo "     openclaw gateway status    # Ver estado"
echo "     openclaw gateway restart   # Reiniciar"
echo "     openclaw gateway logs      # Ver logs"
echo ""
echo "  Para iniciar el dashboard:"
echo "     cd $INSTALL_DIR && streamlit run dashboard/app.py"
echo ""
