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
echo "This will remove DocuMentor from your system."
echo ""
echo "What do you want to remove?"
echo ""
echo "  1) Everything (Docker containers, volumes, Hermes config, project files)"
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
# Step 1 — Stop and remove Docker containers + volumes
# ==============================================================================

echo -e "${CYAN}Stopping Docker services...${NC}"

if [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then
    cd "$SCRIPT_DIR"
    docker compose down -v --remove-orphans 2>/dev/null && \
        echo -e "  ${GREEN}✓${NC} Docker containers and volumes removed" || \
        echo -e "  ${YELLOW}⚠${NC}  Docker compose down failed (may not be running)"
fi

# Also stop SurfSense if running separately
if [ -f "$SCRIPT_DIR/SurfSense/docker/docker-compose.yml" ]; then
    cd "$SCRIPT_DIR/SurfSense/docker"
    docker compose down -v --remove-orphans 2>/dev/null && \
        echo -e "  ${GREEN}✓${NC} SurfSense containers and volumes removed" || true
    cd "$SCRIPT_DIR"
fi

# Remove Docker images built by DocuMentor
echo -e "${CYAN}Removing Docker images...${NC}"
docker images --filter "reference=*documenter*" -q 2>/dev/null | xargs -r docker rmi -f 2>/dev/null && \
    echo -e "  ${GREEN}✓${NC} DocuMentor images removed" || \
    echo -e "  ${YELLOW}⚠${NC}  No DocuMentor images found"

docker images --filter "reference=*surfsense*" -q 2>/dev/null | xargs -r docker rmi -f 2>/dev/null && \
    echo -e "  ${GREEN}✓${NC} SurfSense images removed" || \
    echo -e "  ${YELLOW}⚠${NC}  No SurfSense images found"

# Remove named volumes
echo -e "${CYAN}Removing Docker volumes...${NC}"
for vol in surfsense-postgres surfsense-redis surfsense-shared-temp; do
    docker volume rm "$vol" 2>/dev/null && \
        echo -e "  ${GREEN}✓${NC} Volume $vol removed" || true
done

echo ""

if [ "$CHOICE" = "2" ]; then
    echo -e "${GREEN}${BOLD}Docker cleanup complete.${NC}"
    echo "Project files are still at: $SCRIPT_DIR"
    exit 0
fi

# ==============================================================================
# Step 2 — Remove Hermes configuration
# ==============================================================================

echo -e "${CYAN}Removing Hermes configuration...${NC}"

HERMES_CONFIG="$HOME/.hermes/config.yaml"
if [ -f "$HERMES_CONFIG" ]; then
    # Check if config was created by DocuMentor
    if grep -q "documenter\|DocuMentor" "$HERMES_CONFIG" 2>/dev/null; then
        rm -f "$HERMES_CONFIG"
        echo -e "  ${GREEN}✓${NC} ~/.hermes/config.yaml removed"
    else
        echo -e "  ${YELLOW}⚠${NC}  ~/.hermes/config.yaml exists but wasn't created by DocuMentor — skipping"
    fi
fi

# Remove hermes symlink if it points to our installation
HERMES_BIN="$HOME/.local/bin/hermes"
if [ -L "$HERMES_BIN" ]; then
    TARGET=$(readlink -f "$HERMES_BIN" 2>/dev/null)
    if echo "$TARGET" | grep -q "DocuMentor\|documenter" 2>/dev/null; then
        rm -f "$HERMES_BIN"
        echo -e "  ${GREEN}✓${NC} hermes symlink removed"
    else
        echo -e "  ${YELLOW}⚠${NC}  hermes symlink exists but doesn't point to DocuMentor — skipping"
    fi
fi

echo ""

# ==============================================================================
# Step 3 — Remove temp files
# ==============================================================================

echo -e "${CYAN}Removing temporary files...${NC}"

TEMP_DIR="/tmp/documenter-uploads"
if [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
    echo -e "  ${GREEN}✓${NC} Temp uploads removed"
fi

# Clean any temp files created by the bridge
find /tmp -name "documenter-*" -delete 2>/dev/null && \
    echo -e "  ${GREEN}✓${NC} Temp files cleaned" || true

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
        echo -e "  ${YELLOW}⚠${NC}  .env kept — remember to delete it manually if needed"
    fi
    echo ""
fi

# ==============================================================================
# Step 5 — Remove project files
# ==============================================================================

echo -e "${RED}${BOLD}This will permanently delete all DocuMentor project files at:${NC}"
echo -e "  ${RED}$SCRIPT_DIR${NC}"
echo ""
read -rp "Are you sure? Type 'yes' to confirm: " CONFIRM

if [ "$CONFIRM" = "yes" ]; then
    # Move to parent directory before deleting
    cd "$(dirname "$SCRIPT_DIR")"
    rm -rf "$SCRIPT_DIR"
    echo ""
    echo -e "  ${GREEN}✓${NC} Project files removed"
else
    echo ""
    echo -e "  ${YELLOW}⚠${NC}  Project files kept at: $SCRIPT_DIR"
fi

echo ""
echo -e "${GREEN}${BOLD}DocuMentor has been uninstalled.${NC}"
echo ""
