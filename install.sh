#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
#  DocuMentor — Installer
#  Step 1: Install OpenClaw (if needed)
#  Step 2: Copy DocuMentor workspace + skills
#  Step 3: Configure API key + channel
#  Python deps are installed by the bot on first conversation.
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

echo ""
echo -e "${BOLD}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  DocuMentor — Instalador                      ║${NC}"
echo -e "${BOLD}║  Inteligencia documental con IA               ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Install OpenClaw ────────────────────────────
header "1/3 · OpenClaw..."

export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"
[[ -f "$HOME/.bashrc" ]] && source "$HOME/.bashrc" 2>/dev/null || true
[[ -f "$HOME/.profile" ]] && source "$HOME/.profile" 2>/dev/null || true

if command -v openclaw &>/dev/null; then
    OPENCLAW_VERSION=$(openclaw --version 2>/dev/null || echo "unknown")
    success "OpenClaw ya instalado (${OPENCLAW_VERSION})"
else
    info "Instalando OpenClaw..."
    curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard

    export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"
    [[ -f "$HOME/.bashrc" ]] && source "$HOME/.bashrc" 2>/dev/null || true

    for dir in "$HOME/.npm-global/bin" "$HOME/.local/bin" "/usr/local/bin"; do
        if [[ -x "$dir/openclaw" ]]; then
            export PATH="$dir:$PATH"
            break
        fi
    done

    if ! command -v openclaw &>/dev/null; then
        error "OpenClaw no encontrado tras instalar. Abre una terminal nueva y ejecuta: bash install.sh"
    fi
    success "OpenClaw instalado"
fi

# ── Step 2: Clone repo + copy workspace ─────────────────
header "2/3 · Instalando workspace DocuMentor..."

if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Actualizando repo existente..."
    cd "$INSTALL_DIR" && git pull --ff-only 2>/dev/null || true
else
    [[ -d "$INSTALL_DIR" ]] && rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
success "Repo: $INSTALL_DIR"

mkdir -p "$OPENCLAW_WORKSPACE"/{skills,memory,documents}

for f in SOUL.md AGENTS.md TOOLS.md HEARTBEAT.md; do
    cp -f "$INSTALL_DIR/workspace/$f" "$OPENCLAW_WORKSPACE/$f"
done
[[ -f "$OPENCLAW_WORKSPACE/USER.md" ]] || cp "$INSTALL_DIR/workspace/USER.md" "$OPENCLAW_WORKSPACE/USER.md"
[[ -f "$OPENCLAW_WORKSPACE/MEMORY.md" ]] || touch "$OPENCLAW_WORKSPACE/MEMORY.md"
cp -rf "$INSTALL_DIR/workspace/skills/"* "$OPENCLAW_WORKSPACE/skills/"

for residual in BOOTSTRAP.md IDENTITY.md; do
    [[ -f "$OPENCLAW_WORKSPACE/$residual" ]] && rm -f "$OPENCLAW_WORKSPACE/$residual" || true
done
success "Workspace instalado en: $OPENCLAW_WORKSPACE"

# ── Step 3: Configure API key + Channel ─────────────────
header "3/3 · Configuración..."

CONFIG_FILE="$OPENCLAW_CONFIG_DIR/openclaw.json"
SKIP_CONFIG=""

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
    echo -n "  ¿Sobreescribir con config de DocuMentor? [S/n]: "
    read -r cont
    if [[ "${cont,,}" == "n" || "${cont,,}" == "no" ]]; then
        info "Manteniendo configuración actual."
        SKIP_CONFIG=true
    fi
fi

# Reuse existing gateway token
EXISTING_TOKEN=""
if [[ -f "$CONFIG_FILE" ]]; then
    EXISTING_TOKEN=$(grep -o '"token"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*"token"[[:space:]]*:[[:space:]]*"//' | sed 's/"//')
fi

if [[ "$SKIP_CONFIG" != "true" ]]; then
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

    echo ""
    echo "  💬 Canal de comunicación"
    echo "  1) Telegram (recomendado)"
    echo "  2) WhatsApp"
    echo "  3) Discord"
    echo "  4) Omitir por ahora"
    echo ""
    CHANNEL=""
    CHANNEL_TOKEN=""
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
            4) break ;;
            *) warn "Elige 1-4" ;;
        esac
    done

    # Gateway token
    if [[ -n "${EXISTING_TOKEN:-}" ]]; then
        GW_TOKEN="$EXISTING_TOKEN"
    elif command -v openssl &>/dev/null; then
        GW_TOKEN=$(openssl rand -hex 32)
    else
        GW_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    fi

    # Build channel JSON
    CHANNEL_JSON=""
    case "${CHANNEL:-}" in
        telegram)
            CHANNEL_JSON=$(printf '  "channels": {\n    "telegram": {\n      "enabled": true,\n      "botToken": "%s",\n      "dmPolicy": "allowlist",\n      "allowFrom": [],\n      "groupPolicy": "allowlist",\n      "streaming": "partial"\n    }\n  },' "$CHANNEL_TOKEN")
            ;;
        discord)
            CHANNEL_JSON=$(printf '  "channels": {\n    "discord": {\n      "enabled": true,\n      "botToken": "%s",\n      "dmPolicy": "allowlist",\n      "allowFrom": [],\n      "groupPolicy": "allowlist"\n    }\n  },' "$CHANNEL_TOKEN")
            ;;
        whatsapp)
            CHANNEL_JSON=$(printf '  "channels": {\n    "whatsapp": {\n      "enabled": true,\n      "dmPolicy": "allowlist",\n      "allowFrom": []\n    }\n  },')
            ;;
    esac

    # Write config
    cat > "$CONFIG_FILE" << CONFIGEOF
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
            "input": ["text"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 128000,
            "maxTokens": 65536
          },
          {
            "id": "deepseek-ai/DeepSeek-V3.1",
            "name": "DeepSeek V3.1 (OpenGPU)",
            "api": "openai-completions",
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
CONFIGEOF

    success "Configuración guardada: $CONFIG_FILE"

    if [[ -n "${CHANNEL:-}" ]]; then
        echo ""
        warn "IMPORTANTE: Añade tu ID de usuario a 'allowFrom' en:"
        echo "     $CONFIG_FILE"
        echo ""
        echo "     1. Manda un mensaje al bot"
        echo "     2. Mira los logs: openclaw gateway logs | tail -20"
        echo "     3. Busca tu ID numérico"
        echo "     4. Añádelo a allowFrom y reinicia: openclaw gateway restart"
    fi
fi

# ── Start gateway ───────────────────────────────────────
if command -v openclaw &>/dev/null; then
    openclaw doctor --repair 2>/dev/null || true
    openclaw gateway install --force 2>/dev/null || true
    openclaw gateway restart 2>/dev/null || openclaw gateway start 2>/dev/null || true
fi

# ── Done ────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✅ DocuMentor instalado${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${NC}"
echo ""
echo "  Abre OpenClaw y habla con el bot."
echo "  El asistente se configurará y preparará todo en la primera conversación."
echo ""
echo "  openclaw dashboard    ← abre el panel de control"
echo "  openclaw gateway logs ← ver logs"
echo ""
