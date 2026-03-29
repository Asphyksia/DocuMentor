#!/bin/bash
# ==============================================================================
# DocuMentor Setup Script
# ==============================================================================
# Guides the user through first-time configuration and starts all services.
# Usage: ./setup.sh
# ==============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

clear
echo ""
echo -e "${BOLD}Welcome to DocuMentor${NC}"
echo -e "Intelligent document analysis platform"
echo ""
echo "This script will:"
echo "  1. Check requirements"
echo "  2. Configure your API key and credentials"
echo "  3. Install Hermes Agent (optional)"
echo "  4. Start all services (SurfSense + MCP + Bridge)"
echo "  5. Install and launch the dashboard"
echo ""
read -p "Press Enter to continue..."
echo ""

# ==============================================================================
# Step 0 — Pre-flight checks
# ==============================================================================

echo -e "${CYAN}Checking requirements...${NC}"

ERRORS=0

# Git submodules
if [ ! -f "$SCRIPT_DIR/SurfSense/docker/docker-compose.yml" ] || \
   [ ! -f "$SCRIPT_DIR/surfsense-skill/mcp_server.py" ] || \
   [ -z "$(ls -A "$SCRIPT_DIR/SurfSense" 2>/dev/null)" ]; then
    echo -e "  ${YELLOW}↻${NC} Downloading submodules..."
    git submodule update --init --recursive --force
    if [ ! -f "$SCRIPT_DIR/SurfSense/docker/docker-compose.yml" ]; then
        echo -e "  ${RED}✗${NC} Failed to download submodules"
        echo "    Try manually: git submodule update --init --recursive"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "  ${GREEN}✓${NC} Submodules downloaded"
    fi
else
    echo -e "  ${GREEN}✓${NC} Submodules present"
fi

# Docker
if ! command -v docker &> /dev/null; then
    echo -e "  ${RED}✗${NC} Docker not found"
    echo "    Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    ERRORS=$((ERRORS + 1))
else
    if ! docker info &> /dev/null; then
        echo -e "  ${RED}✗${NC} Docker is not running"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "  ${GREEN}✓${NC} Docker"
    fi
fi

# Node.js
if ! command -v node &> /dev/null; then
    echo -e "  ${RED}✗${NC} Node.js not found"
    echo "    Install from: https://nodejs.org (LTS version)"
    ERRORS=$((ERRORS + 1))
else
    NODE_VERSION=$(node --version)
    echo -e "  ${GREEN}✓${NC} Node.js $NODE_VERSION"
fi

# Python
if ! command -v python3 &> /dev/null; then
    echo -e "  ${RED}✗${NC} Python 3 not found"
    ERRORS=$((ERRORS + 1))
else
    PYTHON_VERSION=$(python3 --version)
    echo -e "  ${GREEN}✓${NC} $PYTHON_VERSION"
fi

# Disk space (~5GB needed)
FREE_GB=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {gsub("G",""); print $4}')
if [ "$FREE_GB" -lt 5 ]; then
    echo -e "  ${YELLOW}⚠${NC}  Only ${FREE_GB}GB free — DocuMentor needs ~5GB"
else
    echo -e "  ${GREEN}✓${NC} Disk space (${FREE_GB}GB free)"
fi

# Port checks
for PORT in 8000 8001 8929 3000; do
    if lsof -i :$PORT &> /dev/null 2>&1; then
        echo -e "  ${YELLOW}⚠${NC}  Port $PORT is in use — may cause conflicts"
    fi
done

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo -e "${RED}Please fix the issues above before continuing.${NC}"
    exit 1
fi

echo ""

# ==============================================================================
# Step 1 — Collect credentials
# ==============================================================================

echo -e "${BOLD}Configuration${NC}"
echo ""

# RelayGPU API key
echo -e "You need a ${CYAN}RelayGPU API key${NC} to use AI models."
echo -e "Get one free at: ${CYAN}https://relay.opengpu.network${NC}"
echo ""

while true; do
    read -rsp "  Enter your RelayGPU API key (relay_sk_...): " API_KEY
    echo ""
    if [[ "$API_KEY" == relay_sk_* ]]; then
        echo -e "  ${GREEN}✓${NC} API key accepted"
        break
    else
        echo -e "  ${RED}✗${NC} Key must start with relay_sk_ — try again"
    fi
done

echo ""

# Login credentials
echo -e "Choose ${CYAN}login credentials${NC} for DocuMentor."
echo -e "  (This protects your instance from unauthorized access)"
echo ""

read -rp "  Email [admin@documenter.local]: " AUTH_EMAIL_INPUT
AUTH_EMAIL="${AUTH_EMAIL_INPUT:-admin@documenter.local}"
echo -e "  ${GREEN}✓${NC} Email: $AUTH_EMAIL"

while true; do
    read -rsp "  Password (min 8 characters): " VAULT_PASSWORD
    echo ""
    if [ ${#VAULT_PASSWORD} -ge 8 ]; then
        echo -e "  ${GREEN}✓${NC} Password set"
        break
    else
        echo -e "  ${RED}✗${NC} Password too short"
    fi
done

echo ""

# Model selection
echo -e "Choose your default AI model:"
echo "  1) openai/gpt-5.4         — Best quality       (\$2.50/\$15.00 per 1M tokens)"
echo "  2) moonshotai/kimi-k2.5   — Multilingual       (\$0.55/\$2.95 per 1M tokens)"
echo "  3) deepseek-ai/DeepSeek-V3.1 — Budget option   (\$0.55/\$1.66 per 1M tokens)"
echo "  4) Qwen/Qwen3.5-397B-A17B-FP8 — Cheapest large (\$0.20/\$1.20 per 1M tokens)"
echo ""
read -rp "  Select [1-4, default=1]: " MODEL_CHOICE
echo ""

case "$MODEL_CHOICE" in
    2) LLM_MODEL="moonshotai/kimi-k2.5" ;;
    3) LLM_MODEL="deepseek-ai/DeepSeek-V3.1" ;;
    4) LLM_MODEL="Qwen/Qwen3.5-397B-A17B-FP8" ;;
    *) LLM_MODEL="openai/gpt-5.4" ;;
esac

echo -e "  ${GREEN}✓${NC} Model: $LLM_MODEL"
echo ""

# Hermes (optional)
echo -e "Do you want to enable ${CYAN}Hermes Agent${NC}? (intelligent query routing)"
echo "  With Hermes: AI reasons about your question and decides which tools to use"
echo "  Without: queries go directly to the search engine (faster, less intelligent)"
echo ""
read -rp "  Enable Hermes? [Y/n]: " ENABLE_HERMES
echo ""

HERMES_ENABLED=true
if [[ "$ENABLE_HERMES" =~ ^[Nn]$ ]]; then
    HERMES_ENABLED=false
    echo -e "  ${GREEN}✓${NC} Hermes disabled — using direct queries"
else
    echo -e "  ${GREEN}✓${NC} Hermes enabled"
fi

echo ""

# ==============================================================================
# Step 2 — Generate .env
# ==============================================================================

echo -e "${CYAN}Generating configuration...${NC}"

SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")

HERMES_SECTION=""
if [ "$HERMES_ENABLED" = true ]; then
    HERMES_SECTION="
# Hermes Agent (intelligent query routing)
HERMES_API_KEY=${API_KEY}
HERMES_BASE_URL=https://relay.opengpu.network/v2/openai/v1
HERMES_MODEL=${LLM_MODEL}
HERMES_MAX_ITERATIONS=20"
fi

cat > "$SCRIPT_DIR/.env" << EOF
# DocuMentor Configuration
# Generated by setup.sh on $(date)

# RelayGPU
OPENAI_API_KEY=${API_KEY}
OPENAI_BASE_URL=https://relay.opengpu.network/v2/openai/v1
LLM_MODEL_NAME=${LLM_MODEL}

# SurfSense core
SECRET_KEY=${SECRET_KEY}
ETL_SERVICE=DOCLING
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
AUTH_TYPE=LOCAL

# MCP Wrapper
SURFSENSE_BASE_URL=http://backend:8000
SURFSENSE_EMAIL=admin@documenter.app
SURFSENSE_PASSWORD=${VAULT_PASSWORD}
MCP_PORT=8000

# Bridge
BRIDGE_PORT=8001

# Authentication
DOCUMENTER_AUTH=true
DOCUMENTER_EMAIL=${AUTH_EMAIL}
DOCUMENTER_PASSWORD=${VAULT_PASSWORD}
${HERMES_SECTION}

# Dashboard
NEXT_PUBLIC_BRIDGE_URL=ws://localhost:8001/ws
NEXT_PUBLIC_DEFAULT_SPACE_ID=1
EOF

# SurfSense needs its own .env in its docker directory
ln -sf "$SCRIPT_DIR/.env" "$SCRIPT_DIR/SurfSense/docker/.env" 2>/dev/null || \
    cp "$SCRIPT_DIR/.env" "$SCRIPT_DIR/SurfSense/docker/.env"

echo -e "  ${GREEN}✓${NC} .env created"
echo ""

# ==============================================================================
# Step 3 — Install Hermes Agent (optional)
# ==============================================================================

if [ "$HERMES_ENABLED" = true ]; then
    echo -e "${CYAN}Installing Hermes Agent...${NC}"

    HERMES_DIR="$SCRIPT_DIR/hermes-agent"
    HERMES_VENV="$HERMES_DIR/venv"
    HERMES_BIN="$HERMES_VENV/bin/hermes"

    if [ -x "$HERMES_BIN" ]; then
        echo -e "  ${GREEN}✓${NC} Hermes already installed"
    elif [ ! -d "$HERMES_DIR" ] || [ ! -f "$HERMES_DIR/pyproject.toml" ]; then
        echo -e "  ${RED}✗${NC} hermes-agent submodule not found"
        echo "    Run: git submodule update --init --recursive"
        exit 1
    else
        # Find Python 3.11+
        PYTHON_CMD=""
        for candidate in python3.11 python3.12 python3.13 python3; do
            if command -v "$candidate" &> /dev/null; then
                PY_VER=$($candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
                PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
                PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
                if [ "$PY_MAJOR" = "3" ] && [ "$PY_MINOR" -ge 11 ]; then
                    PYTHON_CMD="$candidate"
                    echo -e "  ${GREEN}✓${NC} Python $PY_VER found"
                    break
                fi
            fi
        done

        if [ -z "$PYTHON_CMD" ]; then
            echo -e "  ${RED}✗${NC} Python 3.11+ not found"
            exit 1
        fi

        echo -e "  ${CYAN}↻${NC} Creating virtual environment..."
        rm -rf "$HERMES_VENV"
        $PYTHON_CMD -m venv "$HERMES_VENV"

        "$HERMES_VENV/bin/pip" install --quiet --upgrade pip
        "$HERMES_VENV/bin/pip" install --quiet "setuptools>=61,<82" wheel

        # Pin litellm to safe version
        "$HERMES_VENV/bin/pip" install --quiet "litellm>=1.75.5,<1.82.7" || true

        echo -e "  ${CYAN}↻${NC} Installing Hermes (this may take a minute)..."
        cd "$HERMES_DIR"
        "$HERMES_VENV/bin/pip" install -e "." 2>&1 || {
            echo -e "  ${RED}✗${NC} Hermes installation failed"
            exit 1
        }

        # Install MCP support (required for HTTP MCP servers)
        "$HERMES_VENV/bin/pip" install --quiet "mcp[cli]>=1.0.0" || true

        # Install mini-swe-agent if present
        if [ -f "mini-swe-agent/pyproject.toml" ]; then
            "$HERMES_VENV/bin/pip" install --quiet -e "./mini-swe-agent" 2>/dev/null || true
        fi

        cd "$SCRIPT_DIR"

        if [ -x "$HERMES_BIN" ]; then
            echo -e "  ${GREEN}✓${NC} Hermes installed"
        else
            echo -e "  ${RED}✗${NC} Hermes binary not found after install"
            exit 1
        fi

        # Symlink
        mkdir -p "$HOME/.local/bin"
        ln -sf "$HERMES_BIN" "$HOME/.local/bin/hermes"
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "  ${GREEN}✓${NC} hermes command available"
    fi

    # Configure Hermes MCP connection
    HERMES_CONFIG_DIR="${HERMES_HOME:-$HOME/.hermes}"
    HERMES_CONFIG="$HERMES_CONFIG_DIR/config.yaml"
    mkdir -p "$HERMES_CONFIG_DIR"

    if [ ! -f "$HERMES_CONFIG" ]; then
        cat > "$HERMES_CONFIG" << 'HERMESCONF'
# DocuMentor MCP server configuration
mcp_servers:
  surfsense:
    url: "http://localhost:8000/mcp/"
    timeout: 120
    connect_timeout: 30
HERMESCONF
        echo -e "  ${GREEN}✓${NC} Hermes MCP config created"
    else
        echo -e "  ${GREEN}✓${NC} Hermes config exists"
    fi

    echo ""
fi

# ==============================================================================
# Step 4 — Start Docker services
# ==============================================================================

echo -e "${CYAN}Starting services...${NC}"
echo ""

docker compose up -d --build

echo ""
echo -e "  Waiting for SurfSense to be ready..."

# Poll health endpoint (max 3 minutes)
MAX_WAIT=180
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8929/health &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} SurfSense is ready"
        break
    fi
    sleep 5
    WAITED=$((WAITED + 5))
    printf "  Waiting... (%ds / %ds)\r" $WAITED $MAX_WAIT
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo -e "  ${YELLOW}⚠${NC}  SurfSense is taking longer than expected"
    echo "    Check: docker compose logs backend"
fi

# Register admin user (idempotent)
SURFSENSE_EMAIL="admin@documenter.app"
REGISTER_BODY="{\"email\":\"${SURFSENSE_EMAIL}\",\"password\":\"${VAULT_PASSWORD}\"}"
REGISTER_RESP=$(curl -sf -X POST http://localhost:8929/auth/register \
    -H "Content-Type: application/json" \
    -d "$REGISTER_BODY" 2>/dev/null || true)

if echo "$REGISTER_RESP" | grep -q '"id"'; then
    echo -e "  ${GREEN}✓${NC} Admin user registered"
elif echo "$REGISTER_RESP" | grep -q 'ALREADY_EXISTS'; then
    echo -e "  ${GREEN}✓${NC} Admin user already exists"
else
    echo -e "  ${YELLOW}⚠${NC}  Could not register admin user"
fi

# Check MCP wrapper
sleep 3
if curl -sf http://localhost:8000/health &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} MCP wrapper is ready"
else
    echo -e "  ${YELLOW}⚠${NC}  MCP wrapper not responding — check: docker compose logs mcp-wrapper"
fi

# Check Bridge
if curl -sf http://localhost:8001/health &> /dev/null; then
    BRIDGE_INFO=$(curl -sf http://localhost:8001/health)
    HERMES_STATUS=$(echo "$BRIDGE_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('hermes', False))" 2>/dev/null || echo "false")
    if [ "$HERMES_STATUS" = "True" ] || [ "$HERMES_STATUS" = "true" ]; then
        echo -e "  ${GREEN}✓${NC} Bridge is ready (Hermes: enabled)"
    else
        echo -e "  ${GREEN}✓${NC} Bridge is ready (Hermes: disabled — direct MCP mode)"
    fi
else
    echo -e "  ${YELLOW}⚠${NC}  Bridge not responding — check: docker compose logs bridge"
fi

echo ""

# ==============================================================================
# Step 5 — Install and start dashboard
# ==============================================================================

echo -e "${CYAN}Installing dashboard...${NC}"

# Frontend env
if [ ! -f "$SCRIPT_DIR/frontend/.env.local" ]; then
    cat > "$SCRIPT_DIR/frontend/.env.local" << ENVLOCAL
NEXT_PUBLIC_BRIDGE_URL=ws://localhost:8001/ws
NEXT_PUBLIC_DEFAULT_SPACE_ID=1
ENVLOCAL
    echo -e "  ${GREEN}✓${NC} Frontend config created"
fi

cd "$SCRIPT_DIR/frontend"
npm install --silent 2>/dev/null
echo -e "  ${GREEN}✓${NC} Dashboard dependencies installed"

echo ""

# ==============================================================================
# Done
# ==============================================================================

echo -e "${GREEN}${BOLD}Setup complete!${NC}"
echo ""
echo "  ┌────────────────────────────────────────┐"
echo "  │  Dashboard:   http://localhost:3000     │"
echo "  │  Bridge:      http://localhost:8001     │"
echo "  │  MCP tools:   http://localhost:8000     │"
echo "  │  SurfSense:   http://localhost:8929     │"
echo "  └────────────────────────────────────────┘"
echo ""
echo -e "${BOLD}To start the dashboard:${NC}"
echo ""
echo "  cd frontend && npm run dev"
echo ""
if [ "$HERMES_ENABLED" = true ]; then
    echo -e "${BOLD}To use Hermes Agent standalone:${NC}"
    echo ""
    echo "  hermes"
    echo ""
fi
echo -e "${CYAN}Tip:${NC} To change the AI model, edit LLM_MODEL_NAME in .env"
echo "     then run: docker compose restart"
echo ""
