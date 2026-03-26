#!/usr/bin/env bash
# =============================================================================
# configure-llm.sh — Auto-configure SurfSense LLM settings
# =============================================================================
# Called by setup.sh after services are running. Creates an LLM config in
# SurfSense using the same API key/model from .env so users don't have to
# manually configure it through the SurfSense UI.
#
# Usage: ./scripts/configure-llm.sh
# Requires: .env with OPENAI_API_KEY, OPENAI_BASE_URL
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "❌ .env not found. Run setup first."
    exit 1
fi

SURFSENSE_URL="${SURFSENSE_BASE_URL:-http://localhost:8929}"
SURFSENSE_EMAIL="${SURFSENSE_EMAIL:-admin@documenter.app}"
SURFSENSE_PASSWORD="${SURFSENSE_PASSWORD:-changeme}"
LLM_API_KEY="${OPENAI_API_KEY:-}"
LLM_BASE_URL="${OPENAI_BASE_URL:-}"
LLM_MODEL="${LLM_MODEL:-openai/gpt-5.2}"
SEARCH_SPACE_ID="${DEFAULT_SEARCH_SPACE_ID:-1}"

if [ -z "$LLM_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set in .env — skipping LLM configuration"
    exit 0
fi

echo "🔧 Configuring SurfSense LLM settings..."

# Wait for SurfSense to be ready
echo "   Waiting for SurfSense..."
for i in $(seq 1 30); do
    if curl -sf "${SURFSENSE_URL}/health" >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

# Authenticate
echo "   Authenticating..."
AUTH_RESPONSE=$(curl -sf -X POST "${SURFSENSE_URL}/api/v1/auth/jwt/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${SURFSENSE_EMAIL}&password=${SURFSENSE_PASSWORD}" 2>&1) || {
    echo "❌ Failed to authenticate with SurfSense"
    exit 1
}

TOKEN=$(echo "$AUTH_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null) || {
    echo "❌ Failed to parse auth token"
    exit 1
}

AUTH_HEADER="Authorization: Bearer ${TOKEN}"

# Check if an LLM config already exists for this space
echo "   Checking existing LLM configs..."
EXISTING=$(curl -sf -X GET \
    "${SURFSENSE_URL}/api/v1/new-llm-configs?search_space_id=${SEARCH_SPACE_ID}" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" 2>/dev/null) || EXISTING="[]"

CONFIG_COUNT=$(echo "$EXISTING" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null) || CONFIG_COUNT=0

if [ "$CONFIG_COUNT" -gt 0 ]; then
    echo "   ✅ LLM config already exists ($CONFIG_COUNT found). Skipping creation."
    echo "   To reconfigure, delete existing configs in SurfSense UI → Settings → LLM"
    exit 0
fi

# Create LLM config
echo "   Creating LLM config (provider=OPENAI, model=${LLM_MODEL})..."

# Strip openai/ prefix for SurfSense model name (litellm handles provider prefix internally)
MODEL_NAME="${LLM_MODEL#openai/}"

CREATE_RESPONSE=$(curl -sf -X POST "${SURFSENSE_URL}/api/v1/new-llm-configs" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"DocuMentor Default\",
        \"description\": \"Auto-configured by DocuMentor setup\",
        \"provider\": \"OPENAI\",
        \"model_name\": \"${MODEL_NAME}\",
        \"api_key\": \"${LLM_API_KEY}\",
        \"api_base\": \"${LLM_BASE_URL}\",
        \"search_space_id\": ${SEARCH_SPACE_ID},
        \"system_instructions\": \"\",
        \"use_default_system_instructions\": true,
        \"citations_enabled\": true
    }" 2>&1) || {
    echo "❌ Failed to create LLM config"
    echo "   Response: $CREATE_RESPONSE"
    exit 1
}

CONFIG_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null) || {
    echo "⚠️  Config created but couldn't parse ID. You may need to set it as active manually."
    exit 0
}

echo "   Config created (id=$CONFIG_ID). Setting as active..."

# Set as active LLM for both agent and document summary
curl -sf -X PUT \
    "${SURFSENSE_URL}/api/v1/search-spaces/${SEARCH_SPACE_ID}/llm-preferences" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{
        \"agent_llm_id\": ${CONFIG_ID},
        \"document_summary_llm_id\": ${CONFIG_ID}
    }" >/dev/null 2>&1 || {
    echo "⚠️  Config created but couldn't set as active. Set it manually in SurfSense UI."
    exit 0
}

echo "   ✅ SurfSense LLM configured!"
echo "      Provider: OPENAI (litellm-compatible)"
echo "      Model: ${MODEL_NAME}"
echo "      Base URL: ${LLM_BASE_URL}"
echo "      Space: ${SEARCH_SPACE_ID}"
