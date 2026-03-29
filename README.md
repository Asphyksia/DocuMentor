<p align="center">
  <h1 align="center">📚 DocuMentor</h1>
  <p align="center">
    <strong>Intelligent document analysis platform for universities</strong>
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> · <a href="#architecture">Architecture</a> · <a href="#hermes-integration">Hermes Integration</a> · <a href="ARCHITECTURE.md">Full Architecture Docs</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white" alt="Docker Compose" />
    <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js 14" />
    <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
    <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+" />
  </p>
</p>

---

Upload documents. Ask questions in natural language. Get visual dashboards.
Self-hosted — designed for local deployment.

Built on [SurfSense](https://github.com/MODSetter/SurfSense) · [Hermes Agent](https://github.com/NousResearch/hermes-agent) · [RelayGPU](https://relay.opengpu.network)

---

## What is DocuMentor?

DocuMentor is a self-hosted document intelligence platform built for universities. It combines document parsing, RAG-powered search, and LLM inference into a single web interface with interactive dashboards.

**What it does:**
- Processes PDFs, spreadsheets, Word docs, PowerPoint, and more — extracting tables, metrics, and summaries
- Renders extracted data as interactive charts (bar, line, area, pie, KPIs)
- Lets you query documents in natural language with source-backed answers
- Optionally routes queries through [Hermes Agent](https://github.com/NousResearch/hermes-agent) for intelligent reasoning and multi-step tool use

**What it doesn't do (yet):**
- Multi-user auth / RBAC — it's single-user for now (auth planned)
- Offline queries — requires a live LLM provider
- Production hardening — functional for demos and evaluation (CORS, rate limiting, Hermes container in v0.5.0)

> DocuMentor orchestrates existing open-source tools (SurfSense for RAG, Docling for parsing, pgvector for search). Its value is the unified UI, the MCP tool layer, the bridge server, and the guided setup. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full picture.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│            Frontend (Next.js :3000)              │
│   Chat · Dashboard · Document Manager · Settings│
└────────────────────┬────────────────────────────┘
                     │ WebSocket
                     ▼
           ┌─────────────────┐
           │  Bridge (:8001)  │
           │  WebSocket GW    │──────────────────────┐
           └────────┬────────┘                       │
                    │ HTTP/SSE                        │
          ┌─────────▼──────────┐          ┌──────────▼──────────┐
          │  Hermes (:8002)    │          │  Direct MCP calls   │
          │  (dedicated        │          │  (CRUD: upload,     │
          │   container)       │          │   delete, list)     │
          └─────────┬──────────┘          └──────────┬──────────┘
                    │ MCP tool calls                  │
                    ▼                                 ▼
           ┌─────────────────┐
           │ MCP Wrapper     │
           │ (:8000)         │
           │ 25 tools        │
           └────────┬────────┘
                    │ REST API
                    ▼
           ┌─────────────────┐
           │ SurfSense       │
           │ (:8929)         │
           │ Hybrid search · │
           │ Docling · pgvec │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ LLM Provider    │
           │ (RelayGPU, etc) │
           └─────────────────┘
```

**Data flow summary:**
- **Queries** go through Hermes service (:8002, HTTP/SSE) for intelligent reasoning, or directly to MCP tools as fallback
- **CRUD operations** (upload, delete, list) always go directly to MCP — no AI overhead
- **Document parsing** runs locally via Docling inside Docker
- **Embeddings** generated locally with `sentence-transformers/all-MiniLM-L6-v2`

---

## Quick Start

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| [Docker](https://www.docker.com/products/docker-desktop/) | 20.10+ | Docker Compose v2 included |
| [Node.js](https://nodejs.org/) | 18+ | For the dashboard |
| [Git](https://git-scm.com/) | any | Submodule support required |
| [Python](https://www.python.org/) | 3.11+ | For bridge & MCP wrapper |
| Disk space | ~5 GB | Docker images + dependencies |
| LLM API key | — | [RelayGPU](https://relay.opengpu.network) recommended |

### Step by step

```bash
# 1. Clone with submodules
git clone --recursive https://github.com/Asphyksia/DocuMentor
cd DocuMentor

# 2. Option A: Interactive setup (recommended)
./setup.sh

# 2. Option B: Manual setup
cp .env.example .env
# Edit .env — fill in OPENAI_API_KEY, SECRET_KEY, SURFSENSE_PASSWORD (see below)

# 3. Start backend services
docker compose up -d

# 4. Start the dashboard
cd frontend
npm install
npm run dev

# 5. Open http://localhost:3000
```

> `setup.sh` checks requirements, asks for your API key and password, picks a model, generates `.env`, and starts everything. If you prefer manual control, use Option B.

---

## Hermes Integration

> **Optional but recommended.** Without Hermes, queries go directly to MCP tools (basic search). With Hermes, an AI agent reasons about your query, selects the right tools, and produces richer answers.

### Setup

Hermes runs as a **dedicated Docker container** (v0.5.0+). Just set the API key in `.env`:

```bash
# In .env, uncomment and fill in:
HERMES_API_KEY=your_api_key_here
HERMES_BASE_URL=https://relay.opengpu.network/v2/openai/v1  # or OpenRouter, etc.
HERMES_MODEL=openai/gpt-5.2                                  # with provider prefix

# Start/restart services
docker compose up -d --build hermes bridge
```

The MCP config for Hermes is pre-configured (`hermes-service/hermes-config.yaml`) — no manual setup needed.

### How it works

The bridge detects Hermes automatically via health check and routes queries through it:

1. User asks a question → Bridge POSTs to Hermes service (HTTP/SSE)
2. Hermes reasons about the query and decides which MCP tools to call
3. Tools execute against SurfSense via the MCP wrapper
4. Hermes streams the response back (SSE events: delta, tool, status, done)
5. Bridge forwards SSE events to the frontend via WebSocket

New WebSocket message types when Hermes is active:
- `stream` — streaming text tokens as they're generated
- `agent_status` — which tool is running (e.g., `surfsense_query`)

Without Hermes (container not running or unhealthy), the bridge falls back to direct MCP calls — still functional, just less intelligent. No code changes needed to switch.

---

## Environment Variables

All variables from `.env.example`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | LLM provider API key ([RelayGPU](https://relay.opengpu.network) recommended) |
| `OPENAI_BASE_URL` | — | `https://relay.opengpu.network/v2/openai/v1` | LLM API endpoint |
| `LLM_MODEL_NAME` | — | `openai/gpt-5.4` | Model for document analysis and queries |
| `SECRET_KEY` | ✅ | — | Random string for SurfSense (`openssl rand -base64 32`) |
| `ETL_SERVICE` | — | `DOCLING` | Document parser (DOCLING runs locally) |
| `EMBEDDING_MODEL` | — | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `AUTH_TYPE` | — | `LOCAL` | Authentication type |
| `SURFSENSE_BASE_URL` | — | `http://localhost:8929` | SurfSense backend URL |
| `SURFSENSE_EMAIL` | — | `admin@documenter.local` | SurfSense login email |
| `SURFSENSE_PASSWORD` | ✅ | — | SurfSense login password |
| `MCP_PORT` | — | `8000` | MCP wrapper port |
| `BRIDGE_PORT` | — | `8001` | Bridge WebSocket port |
| `DOCUMENTER_AUTH` | — | `true` | Enable/disable login authentication |
| `DOCUMENTER_EMAIL` | — | `admin@documenter.local` | Login email |
| `DOCUMENTER_PASSWORD` | ✅ | — | Login password (min 8 chars) |
| `HERMES_API_KEY` | ✅* | — | OpenRouter key for Hermes (*only if using Hermes) |
| `HERMES_BASE_URL` | — | `https://openrouter.ai/api/v1` | Hermes LLM endpoint |
| `HERMES_MODEL` | — | `qwen/qwen3-235b-a22b` | Model for Hermes Agent |
| `HERMES_MAX_ITERATIONS` | — | `20` | Max tool-calling rounds per query |
| `ALLOWED_ORIGINS` | — | `http://localhost:3000,http://127.0.0.1:3000` | CORS allowed origins (comma-separated) |
| `RATE_LIMIT_MAX` | — | `30` | Max requests per 60s per WebSocket connection |
| `NEXT_PUBLIC_BRIDGE_URL` | — | `ws://localhost:8001/ws` | Bridge WebSocket URL for frontend |
| `NEXT_PUBLIC_DEFAULT_SPACE_ID` | — | `1` | Default document space ID |

---

## Development

Run components individually for development/debugging:

### Bridge server

```bash
cd backend
pip install -r requirements.txt
python bridge.py
# Runs on http://localhost:8001
```

### MCP Wrapper

```bash
cd surfsense-skill
pip install -r requirements.txt  # if separate from backend
python mcp_server.py
# Runs on http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

> **Tip:** When running the bridge outside Docker, make sure `MCP_URL` in `.env` points to `http://localhost:8000` (not the Docker internal address).

### Backend services (SurfSense, PostgreSQL, Redis)

These always run via Docker:

```bash
docker compose up -d
```

---

## Project Structure

```
DocuMentor/
├── docker-compose.yml             # Orchestrates all services
├── .env.example                   # Config template
├── setup.sh                       # Interactive installer
├── uninstall.sh                   # Interactive uninstaller
├── hermes-config.example.yaml     # Hermes MCP config template
│
├── backend/
│   ├── bridge.py                  # WebSocket gateway v0.4.0 (10 handlers, CORS, rate limiting)
│   ├── Dockerfile.bridge          # Bridge container
│   ├── Dockerfile.mcp             # MCP wrapper container
│   └── requirements.txt
│
├── surfsense-skill/               # Git submodule — MCP tools (single source of truth)
│   └── mcp_server.py              # MCP server v0.4.0 (25 tools, dual protocol)
│
├── frontend/
│   ├── app/                       # Next.js pages and layout
│   ├── components/                # React components (+ shadcn/ui)
│   ├── hooks/useBridge.ts         # WebSocket client hook
│   ├── DashboardRenderer.tsx      # JSON → visual dashboards
│   └── lib/utils.ts
│
├── hermes-agent/                  # Git submodule — Nous Research
├── docs/                          # Audit reports and improvement plans
│
├── ARCHITECTURE.md                # Technical deep-dive
├── DOCSTEMPLATES.md               # Dashboard JSON schemas
├── HERMES_INTEGRATION_PLAN.md     # Hermes integration roadmap
├── CONTRIBUTING.md                # Contribution guidelines
└── LICENSE                        # MIT
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **RAG & search** | [SurfSense](https://github.com/MODSetter/SurfSense) — hybrid semantic + full-text search |
| **Document parsing** | [Docling](https://github.com/DS4SD/docling) (IBM) — runs locally via SurfSense |
| **Agent** | [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI reasoning & tool orchestration |
| **MCP tools** | [surfsense-skill](https://github.com/Asphyksia/surfsense-skill) — 25 MCP tools via [FastMCP](https://github.com/jlowin/fastmcp) |
| **LLM inference** | [RelayGPU](https://relay.opengpu.network) or any OpenAI-compatible provider |
| **Bridge** | FastAPI + WebSocket — real-time gateway |
| **Dashboard** | Next.js 14 + [shadcn/ui](https://ui.shadcn.com) + Recharts + Framer Motion |
| **Database** | PostgreSQL 17 + pgvector |
| **Task queue** | Redis + Celery |
| **Containers** | Docker Compose |

---

## Supported File Types

| Format | What's extracted |
|--------|-----------------|
| PDF | Summary · entities · tables · key paragraphs |
| Excel / CSV | Sheet data · calculated metrics · charts |
| Word (.docx) | Sections · tables · summary |
| PowerPoint (.pptx) | Slide overview · tables · charts |
| HTML | Content · headings · tables · links |
| Images (scanned) | OCR text · tables · form fields |

---

## Privacy & Data Flow

- **Parsing** — runs locally in Docker via Docling. No documents leave your machine for parsing.
- **Embeddings** — generated locally with `sentence-transformers/all-MiniLM-L6-v2`.
- **LLM queries** — document text (not raw files) is sent to the configured LLM provider for inference. With RelayGPU or OpenRouter, text leaves your machine. For full locality, use a local model via Ollama.
- **Storage** — PostgreSQL + pgvector, running in Docker on your machine.
- **No telemetry** — DocuMentor does not phone home or collect usage data.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `docker compose up` fails | Make sure Docker is running. On WSL2, enable "WSL 2 based engine" in Docker settings. |
| Frontend shows "Disconnected" | Create `frontend/.env.local` with `NEXT_PUBLIC_BRIDGE_URL=ws://localhost:8001/ws` |
| SurfSense containers restarting | Check `docker logs surfsense-backend`. Usually missing `.env` or wrong `SECRET_KEY`. |
| Upload times out | Large files take 30-60s for indexing. Check SurfSense logs for errors. |
| Bad dashboard JSON | Try a more capable model (e.g. `gpt-5.4`). Dashboard quality = model quality. |
| Hermes not activating | Verify `HERMES_API_KEY` is set and uncommented in `.env`, then `docker compose restart bridge`. |

---

## Updating

```bash
cd DocuMentor
git pull
git submodule update --init --recursive
docker compose up -d --build
```

Documents and configuration are preserved on update.

## Uninstalling

```bash
./uninstall.sh           # Linux / macOS / WSL2
```

Windows (no WSL): `docker compose down -v --remove-orphans`, then delete the folder.

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE) — see LICENSE file.

---

*DocuMentor is an independent open-source project. Not affiliated with Nous Research, SurfSense, or RelayGPU.*
