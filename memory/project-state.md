# DocuMentor — Estado del proyecto
_Última actualización: 2026-03-23_

## Repositorio
https://github.com/Asphyksia/DocuMentor
Branch: main — token disponible para push

## Descripción
Plataforma agentica de gestión documental para universidades.
Stack: Hermes Agent + SurfSense (RAG) + RelayGPU + Next.js dashboard.

## Lo que está hecho ✅

### Archivos raíz
- `SOUL.md` — personalidad DocuMentor, workflow, onboarding, tools
- `BOOTSTRAP.md` — setup guiado por el agente, lee .env y escribe ~/.hermes/config.yaml
- `DOCSTEMPLATES.md` — schemas JSON por tipo: pdf / spreadsheet / docx / generic
- `README.md` — documentación completa en inglés
- `LICENSE` — MIT
- `.env.example` — 3 campos obligatorios, resto pre-rellenado
- `setup.sh` — script interactivo de instalación para usuarios no técnicos
- `docker-compose.yml` — orquesta SurfSense + MCP wrapper
- `.gitmodules` — hermes-agent y SurfSense como submodules

### backend/
- `mcp_wrapper.py` — servidor MCP (FastAPI), 6 tools:
  - surfsense_list_spaces, surfsense_create_space
  - surfsense_upload, surfsense_list_documents
  - surfsense_query, surfsense_extract_tables
- `requirements.txt` — fastapi, uvicorn, httpx, python-multipart
- `Dockerfile` — container para el wrapper
- `.env.example`
- `hermes-mcp-config.yaml`

### frontend/
- `DashboardRenderer.tsx` — renderiza JSON → KPI/bar/line/table/text
- `app/layout.tsx` — root layout Next.js 14
- `app/globals.css` — Tailwind
- `app/page.tsx` — página principal con upload zone + chat básico
- `app/api/upload-temp/route.ts` — guarda archivos en /tmp para el MCP
- `package.json` — Next.js 14 + Tremor + Recharts + TypeScript
- `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`

## Flujo de instalación actual
```
git clone + git submodule update --init --recursive
./setup.sh  ← pide 3 cosas: API key, password, modelo
            ← genera .env automáticamente
            ← instala Hermes (sin wizard)
            ← docker compose up -d
            ← npm install en frontend
hermes      ← lee SOUL.md + BOOTSTRAP.md
            ← configura ~/.hermes/config.yaml desde .env
            ← onboarding con usuario
```

## Problema actual identificado
El dashboard (localhost:3000), Hermes (terminal) y SurfSense (localhost:3929)
están desconectados entre sí. El usuario tiene que usar 3 interfaces distintas.

## Plan de desarrollo pendiente 🔴

### Fase 1 — Bridge Server (1 día)
Servidor intermediario que conecta el dashboard con Hermes vía WebSocket.
Archivo: `backend/bridge.py`
- WebSocket server en puerto 8001
- Recibe mensajes del dashboard (upload, query)
- Los pasa a Hermes como input
- Recibe output de Hermes (JSON dashboard)
- Lo reenvía al dashboard para renderizar
- Protocolo de mensajes:
  ```json
  { "type": "upload|query|result|status", "payload": {} }
  ```

### Fase 2 — UI unificada (2-3 días)
Rediseño completo del frontend como app de una sola URL.
Archivo: `frontend/app/page.tsx` (reescribir)
- Layout tipo app: sidebar izquierda + panel principal
- Sidebar: lista de documentos indexados
- Panel principal con pestañas:
  - 💬 Chat — chat con Hermes, mensajes con dashboards inline
  - 📊 Dashboard — vista del último análisis
  - 📁 Documentos — gestión de archivos subidos
  - ⚙️ Ajustes — modelo, API key, search spaces
- Animaciones con Framer Motion
- Drag & drop nativo para subir archivos
- Conexión al bridge server vía WebSocket
- Estado compartido (documentos, mensajes, status)

### Fase 3 — Tauri wrapper (futuro)
Empaquetar la web app como aplicación de escritorio nativa.
- `src-tauri/` en la raíz
- Una sola ventana sin chrome de browser
- Drag & drop a nivel de OS
- Acceso directo al sistema de archivos

## Decisiones técnicas importantes
- Hermes ignora OPENAI_API_KEY del entorno — solo lee ~/.hermes/config.yaml
- BOOTSTRAP.md escribe config.yaml desde .env en cada primer arranque
- NO correr `hermes setup` — sobreescribe la config de DocuMentor
- Endpoint OpenAI: https://relay.opengpu.network/v2/openai/v1
- Endpoint Anthropic: https://relay.opengpu.network/v2/anthropic/v1
- Modelos Claude requieren cambiar el base_url en .env
- Modelo por defecto: openai/gpt-5.4

## RelayGPU — Modelos disponibles (2026-03-23)
### OpenAI endpoint (/v2/openai/v1)
- openai/gpt-5.4: $2.50/$15.00 per 1M tokens
- openai/gpt-5.2: $1.75/$14.00
- moonshotai/kimi-k2.5: $0.55/$2.95
- deepseek-ai/DeepSeek-V3.1: $0.55/$1.66
- infercom/MiniMax-M2.5: $0.30/$1.20 (164K context)
- Qwen/Qwen3.5-397B-A17B-FP8: $0.20/$1.20
- Qwen/Qwen3-Coder: $1.30/$5.00
### Anthropic endpoint (/v2/anthropic/v1)
- anthropic/claude-sonnet-4-6: $3.00/$15.00
- anthropic/claude-opus-4-6: $5.00/$25.00

## Contacto / owner
- GitHub: Asphyksia
- Telegram: Maxi (@Ox8472309)
