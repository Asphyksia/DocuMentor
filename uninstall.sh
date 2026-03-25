#!/bin/bash
# ==============================================================================
# DocuMentor Uninstaller
# ==============================================================================
# Removes DocuMentor and all its components from your system.
# Usage: ./uninstall.sh
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

echo ""
echo -e "${BOLD}DocuMentor Uninstaller${NC}"
echo ""
echo "What do you want to remove?"
echo ""
echo "  1) Everything (Docker, Hermes, project files)"
echo "  2) Docker only (containers + volumes — keep project files)"
echo "  3) Cancel"
echo ""
read -rp "Select [1-3]: " CHOICE
echo ""

if [ "$CHOICE" = "3" ] || [ -z "$CHOICE" ]; then
    echo "Cancelled."
    exit 0
fi

# ==============================================================================
# Step 1 — Stop and remove Docker
# ==============================================================================

echo -e "${CYAN}Stopping Docker services...${NC}"

if [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then
    cd "$SCRIPT_DIR"
    docker compose down -v --remove-orphans 2>/dev/null && \
        echo -e "  ${GREEN}✓${NC} DocuMentor containers and volumes removed" || \
        echo -e "  ${YELLOW}⚠${NC}  Docker compose down failed (may not be running)"
fi

# Also stop SurfSense if running separately
if [ -f "$SCRIPT_DIR/SurfSense/docker/docker-compose.yml" ]; then
    cd "$SCRIPT_DIR/SurfSense/docker"
    docker compose down -v --remove-orphans 2>/dev/null && \
        echo -e "  ${GREEN}✓${NC} SurfSense containers removed" || true
    cd "$SCRIPT_DIR"
fi

# Remove Docker images
echo -e "${CYAN}Removing Docker images...${NC}"
for pattern in "*documenter*" "*surfsense*" "*mcp-wrapper*"; do
    docker images --filter "reference=$pattern" -q 2>/dev/null | xargs -r docker rmi -f 2>/dev/null || true
done
echo -e "  ${GREEN}✓${NC} Docker images cleaned"

# Remove named volumes
for vol in surfsense-postgres surfsense-redis surfsense-shared-temp upload-tmp; do
    docker volume rm "$vol" 2>/dev/null || true
done

# Prune dangling
docker image prune -f &>/dev/null || true
echo -e "  ${GREEN}✓${NC} Docker cleanup complete"

echo ""

if [ "$CHOICE" = "2" ]; then
    echo -e "${GREEN}${BOLD}Docker cleanup complete.${NC}"
    echo "Project files still at: $SCRIPT_DIR"
    exit 0
fi

# ==============================================================================
# Step 2 — Remove Hermes configuration
# ==============================================================================

echo -e "${CYAN}Removing Hermes configuration...${NC}"

HERMES_CONFIG="${HERMES_HOME:-$HOME/.hermes}/config.yaml"
if [ -f "$HERMES_CONFIG" ]; then
    if grep -q "surfsense\|documenter\|DocuMentor" "$HERMES_CONFIG" 2>/dev/null; then
        rm -f "$HERMES_CONFIG"
        echo -e "  ${GREEN}✓${NC} ~/.hermes/config.yaml removed"
    else
        echo -e "  ${YELLOW}⚠${NC}  ~/.hermes/config.yaml not created by DocuMentor — skipping"
    fi
else
    echo -e "  ${GREEN}✓${NC} No Hermes config found"
fi

# Remove hermes symlink if ours
HERMES_BIN="$HOME/.local/bin/hermes"
if [ -L "$HERMES_BIN" ]; then
    TARGET=$(readlink -f "$HERMES_BIN" 2>/dev/null)
    if echo "$TARGET" | grep -qi "documenter\|hermes-agent" 2>/dev/null; then
        rm -f "$HERMES_BIN"
        echo -e "  ${GREEN}✓${NC} hermes symlink removed"
    fi
fi

echo ""

# ==============================================================================
# Step 3 — Remove temp files
# ==============================================================================

echo -e "${CYAN}Removing temporary files...${NC}"
rm -rf /tmp/documenter-uploads 2>/dev/null || true
find /tmp -name "documenter-*" -delete 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Temp files cleaned"

echo ""

# ==============================================================================
# Step 4 — Remove .env (contains API key)
# ==============================================================================

if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${YELLOW}Your .env file contains your API key.${NC}"
    read -rp "Delete .env? [y/N]: " DELETE_ENV
    if [[ "$DELETE_ENV" =~ ^[Yy]$ ]]; then
        rm -f "$SCRIPT_DIR/.env"
        echo -e "  ${GREEN}✓${NC} .env removed"
    else
        echo -e "  ${YELLOW}⚠${NC}  .env kept"
    fi
    echo ""
fi

# ==============================================================================
# Step 5 — Remove project files
# ==============================================================================

echo -e "${RED}${BOLD}This will permanently delete:${NC}"
echo -e "  ${RED}$SCRIPT_DIR${NC}"
echo ""
read -rp "Type 'yes' to confirm: " CONFIRM

if [ "$CONFIRM" = "yes" ]; then
    cd "$(dirname "$SCRIPT_DIR")"
    rm -rf "$SCRIPT_DIR"
    echo ""
    echo -e "  ${GREEN}✓${NC} Project files removed"
else
    echo ""
    echo -e "  ${YELLOW}⚠${NC}  Project files kept"
fi

echo ""
echo -e "${GREEN}${BOLD}DocuMentor has been uninstalled.${NC}"
echo ""
