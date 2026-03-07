#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
#  DocuMentor — Uninstaller
#  Removes DocuMentor workspace, repo, and optionally OpenClaw
# ─────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}ℹ ${NC}$1"; }
success() { echo -e "${GREEN}✓ ${NC}$1"; }
warn()    { echo -e "${YELLOW}⚠ ${NC}$1"; }

INSTALL_DIR="${HOME}/DocuMentor"
OPENCLAW_CONFIG_DIR="${HOME}/.openclaw"
OPENCLAW_WORKSPACE="${OPENCLAW_CONFIG_DIR}/workspace"

echo ""
echo -e "${BOLD}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  DocuMentor — Desinstalador                   ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Esto eliminará:${NC}"
echo "  • Repo local:   $INSTALL_DIR"
echo "  • Workspace:    $OPENCLAW_WORKSPACE"
echo "  • Documentos y datos indexados"
echo ""
echo -n "¿Continuar? [s/N]: "
read -r confirm
if [[ "${confirm,,}" != "s" && "${confirm,,}" != "si" && "${confirm,,}" != "sí" ]]; then
    echo "Cancelado."
    exit 0
fi

echo ""

# Stop gateway
if command -v openclaw &>/dev/null; then
    info "Deteniendo gateway..."
    openclaw gateway stop 2>/dev/null || true
    success "Gateway detenido"
fi

# Remove DocuMentor repo
if [[ -d "$INSTALL_DIR" ]]; then
    info "Eliminando repo: $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
    success "Repo eliminado"
fi

# Remove workspace
if [[ -d "$OPENCLAW_WORKSPACE" ]]; then
    info "Eliminando workspace: $OPENCLAW_WORKSPACE"
    rm -rf "$OPENCLAW_WORKSPACE"
    success "Workspace eliminado"
fi

# Remove OpenClaw config (but not OpenClaw itself)
echo ""
echo -n "¿Eliminar también la configuración de OpenClaw (~/.openclaw)? [s/N]: "
read -r confirm_config
if [[ "${confirm_config,,}" == "s" || "${confirm_config,,}" == "si" || "${confirm_config,,}" == "sí" ]]; then
    rm -rf "$OPENCLAW_CONFIG_DIR"
    success "Configuración de OpenClaw eliminada"
fi

# Optionally uninstall OpenClaw
echo ""
echo -n "¿Desinstalar también OpenClaw? [s/N]: "
read -r confirm_openclaw
if [[ "${confirm_openclaw,,}" == "s" || "${confirm_openclaw,,}" == "si" || "${confirm_openclaw,,}" == "sí" ]]; then
    if command -v openclaw &>/dev/null; then
        info "Desinstalando OpenClaw..."
        openclaw uninstall 2>/dev/null || npm uninstall -g openclaw 2>/dev/null || true
        success "OpenClaw desinstalado"
    else
        warn "OpenClaw no encontrado en PATH"
    fi
fi

echo ""
echo -e "${GREEN}${BOLD}Desinstalación completada.${NC}"
echo ""
