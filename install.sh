#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
#  DocuMentor — Installer
#  Step 1: Install OpenClaw (if needed)
#  Step 2: Copy DocuMentor workspace + skills
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
header "1/2 · OpenClaw..."

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
header "2/2 · Instalando workspace DocuMentor..."

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
