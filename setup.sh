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
echo -e "Agentic document intelligence platform"
echo ""
echo "This script will:"
echo "  1. Configure your API key and credentials"
echo "  2. Install Hermes Agent"
echo "  3. Start all services (SurfSense + MCP wrapper)"
echo "  4. Launch the dashboard"
echo ""
read -p "Press Enter to continue..."
echo ""

# ==============================================================================
# Step 0 — Pre-flight checks
# ==============================================================================

echo -e "${CYAN}Checking requirements...${NC}"

ERRORS=0

# Git submodules (must be first — everything depends on these)
if [ ! -f "$SCRIPT_DIR/SurfSense/docker/docker-compose.yml" ] || [ ! -d "$SCRIPT_DIR/hermes-agent" ] || [ -z "$(ls -A "$SCRIPT_DIR/SurfSense" 2>/dev/null)" ]; then
    echo -e "  ${YELLOW}↻${NC} Downloading submodules (SurfSense + Hermes Agent)..."
    git submodule update --init --recursive --force
    if [ ! -f "$SCRIPT_DIR/SurfSense/docker/docker-compose.yml" ]; then
        echo -e "  ${RED}✗${NC} Failed to download SurfSense submodule"
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
    echo "    Install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
    ERRORS=$((ERRORS + 1))
else
    if ! docker info &> /dev/null; then
        echo -e "  ${RED}✗${NC} Docker is not running — please start Docker Desktop"
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
    echo "    Install from: https://python.org"
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
for PORT in 8000 8929 3000; do
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
# Step 1 — Collect credentials (only what's needed)
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

# Password for SurfSense
echo -e "Choose a ${CYAN}password${NC} for your document vault (SurfSense)."
while true; do
    read -rsp "  Password (min 8 characters): " VAULT_PASSWORD
    echo ""
    if [ ${#VAULT_PASSWORD} -ge 8 ]; then
        echo -e "  ${GREEN}✓${NC} Password set"
        break
    else
        echo -e "  ${RED}✗${NC} Password too short — minimum 8 characters"
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

# ==============================================================================
# Step 2 — Generate .env
# ==============================================================================

echo -e "${CYAN}Generating configuration...${NC}"

# Generate a random SECRET_KEY
SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")

cat > "$SCRIPT_DIR/.env" << EOF
# DocuMentor Configuration
# Generated by setup.sh on $(date)
# To change the model, edit LLM_MODEL_NAME and restart with: docker compose restart

# RelayGPU
OPENAI_API_KEY=${API_KEY}
OPENAI_BASE_URL=https://relay.opengpu.network/v2/openai/v1
LLM_MODEL_NAME=${LLM_MODEL}

# SurfSense
SECRET_KEY=${SECRET_KEY}
ETL_SERVICE=DOCLING
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
AUTH_TYPE=LOCAL

# MCP Wrapper
SURFSENSE_BASE_URL=http://localhost:8929
SURFSENSE_EMAIL=admin@documenter.local
SURFSENSE_PASSWORD=${VAULT_PASSWORD}
MCP_PORT=8000

# Dashboard
NEXT_PUBLIC_MCP_URL=http://localhost:8000
NEXT_PUBLIC_DEFAULT_SPACE_ID=1
EOF

# SurfSense needs its own .env in its docker directory
# Create a symlink so both point to the same config
ln -sf "$SCRIPT_DIR/.env" "$SCRIPT_DIR/SurfSense/docker/.env"

echo -e "  ${GREEN}✓${NC} .env created"
echo ""

# ==============================================================================
# Step 3 — Install Hermes Agent
# ==============================================================================

echo -e "${CYAN}Installing Hermes Agent...${NC}"

if command -v hermes &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Hermes already installed"
else
    if [ -f "$SCRIPT_DIR/hermes-agent/setup-hermes.sh" ]; then
        # Run setup but skip the interactive wizard at the end
        # by passing a non-Y answer automatically
        echo "n" | bash "$SCRIPT_DIR/hermes-agent/setup-hermes.sh"

        # Reload PATH
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "  ${GREEN}✓${NC} Hermes installed"
    else
        echo -e "  ${RED}✗${NC} hermes-agent not found — run: git submodule update --init"
        exit 1
    fi
fi

echo ""

# ==============================================================================
# Step 4 — Start Docker services
# ==============================================================================

echo -e "${CYAN}Starting services (this may take a few minutes on first run)...${NC}"
echo "  Downloading Docker images..."
echo ""

docker compose up -d

echo ""
echo -e "  Waiting for SurfSense to be ready..."

# Poll health endpoint up to 3 minutes
MAX_WAIT=180
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8929/health &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} SurfSense is ready"
        break
    fi
    sleep 5
    WAITED=$((WAITED + 5))
    echo -ne "  Waiting... (${WAITED}s / ${MAX_WAIT}s)\r"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo -e "  ${YELLOW}⚠${NC}  SurfSense is taking longer than expected"
    echo "    Check logs with: docker compose logs backend"
fi

# Check MCP wrapper
if curl -sf http://localhost:8000/health &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} MCP wrapper is ready"
else
    echo -e "  ${YELLOW}⚠${NC}  MCP wrapper not responding — check: docker compose logs mcp-wrapper"
fi

echo ""

# ==============================================================================
# Step 5 — Install dashboard dependencies
# ==============================================================================

echo -e "${CYAN}Installing dashboard...${NC}"

if [ -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo -e "  ${GREEN}✓${NC} Dependencies already installed"
else
    cd "$SCRIPT_DIR/frontend"
    npm install --silent
    cd "$SCRIPT_DIR"
    echo -e "  ${GREEN}✓${NC} Dashboard dependencies installed"
fi

echo ""

# ==============================================================================
# Done
# ==============================================================================

echo -e "${GREEN}${BOLD}Setup complete!${NC}"
echo ""
echo "  Dashboard:   http://localhost:3000"
echo "  SurfSense:   http://localhost:8929"
echo "  MCP tools:   http://localhost:8000"
echo ""
echo -e "${BOLD}Start DocuMentor:${NC}"
echo ""
echo "  # Terminal 1 — Dashboard"
echo "  cd frontend && npm run dev"
echo ""
echo "  # Terminal 2 — Agent"
echo "  hermes"
echo ""
echo -e "${CYAN}Tip:${NC} To change the AI model, edit LLM_MODEL_NAME in .env"
echo "     then run: docker compose restart mcp-wrapper && hermes"
echo ""
