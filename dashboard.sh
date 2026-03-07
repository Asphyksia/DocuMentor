#!/usr/bin/env bash
# DocuMentor Dashboard Launcher (Linux/macOS)
# Finds the venv automatically and launches Streamlit

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DASHBOARD="$SCRIPT_DIR/dashboard/app.py"

# Check common venv locations
for VENV in "$HOME/.openclaw/workspace/.venv" "$SCRIPT_DIR/.venv" "$HOME/DocuMentor/.venv"; do
    if [[ -f "$VENV/bin/streamlit" ]]; then
        exec "$VENV/bin/streamlit" run "$DASHBOARD"
    fi
done

# Fallback: try system streamlit
if command -v streamlit &>/dev/null; then
    exec streamlit run "$DASHBOARD"
fi

echo ""
echo "  [!] Streamlit no encontrado."
echo "  Habla con el bot primero para que instale las dependencias."
echo "  O ejecuta manualmente: pip install streamlit"
echo ""
