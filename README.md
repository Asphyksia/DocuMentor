# DocuMentor

**Agentic document intelligence platform for universities.**

Upload documents. Ask questions in natural language. Get interactive dashboards.
Everything runs locally — your data never leaves your infrastructure.

Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) · [SurfSense](https://github.com/MODSetter/SurfSense) · [RelayGPU](https://relay.opengpu.network)

---

## What it does

DocuMentor is a self-hosted AI agent that turns institutional documents into structured, queryable knowledge. It processes PDFs, spreadsheets, and Word documents — extracting tables, metrics, and summaries — then renders them as visual dashboards you can explore through natural language.

```
                    ┌──────────────────────────────────────────┐
                    │        localhost:3000 — Unified UI        │
                    │  ┌──────────┬───────────────────────────┐│
                    │  │          │  💬 Chat  📊 Dashboard ⚙️ ││
                    │  │  📁 Docs │                           ││
                    │  │          │    KPIs · Charts · Tables  ││
                    │  └──────────┴───────────────────────────┘│
                    └──────────────────┬───────────────────────┘
                                       │ WebSocket
                                       ▼
                              Bridge Server (:8001)
                          Real-time status updates
                                       │ JSON-RPC
                                       ▼
                              MCP Wrapper (:8000)
                          6 tools for document ops
                                       │ REST API
                                       ▼
                             SurfSense (:8929)
                    Hybrid search · 50+ formats · Docling
                         PostgreSQL + pgvector
                                       │
                                       ▼
                        RelayGPU (OpenGPU Network)
                    Affordable LLM inference · ~€0.01/doc
```

---

## Features

- **📄 50+ file formats** — PDF, Excel, CSV, Word, and more via Docling (runs locally)
- **🔍 Hybrid search** — semantic + full-text with Reciprocal Rank Fusion
- **📊 Auto-generated dashboards** — KPI cards, bar charts, line charts, data tables
- **💬 Natural language queries** — ask questions, get cited answers
- **🖥️ Unified single-page UI** — sidebar, chat, dashboard, and settings in one window
- **⚡ Real-time updates** — WebSocket bridge with live status (uploading → indexing → ready)
- **🎨 Modern dark UI** — Framer Motion animations, drag & drop upload, responsive
- **🌍 Multi-language** — detects user language automatically, responds in kind
- **🤖 Conversational setup** — the agent guides you through installation interactively
- **🔒 Fully private** — no data sent to third parties, all processing local
- **🛡️ Prompt injection protection** — built-in input validation
- **👥 Team collaboration** — RBAC roles, shared search spaces, real-time chat

---

## Quick Start

### Requirements

| Requirement | Windows | macOS | Linux |
|-------------|---------|-------|-------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | ✅ | ✅ | ✅ (or Docker Engine) |
| [Git](https://git-scm.com/downloads) | ✅ | ✅ (preinstalled or via Xcode) | ✅ (preinstalled) |
| [Node.js 18+](https://nodejs.org/) | ✅ | ✅ | ✅ |
| [Python 3.11+](https://www.python.org/downloads/) | ✅ | ✅ | ✅ |
| Disk space | ~5 GB | ~5 GB | ~5 GB |
| [RelayGPU API key](https://relay.opengpu.network) | `relay_sk_...` | `relay_sk_...` | `relay_sk_...` |

> 💡 **Windows users:** Use [Git Bash](https://gitforwindows.org/), [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install), or PowerShell. WSL2 is recommended for best Docker performance.

### Install

<details>
<summary><strong>🐧 Linux / 🍎 macOS</strong></summary>

```bash
git clone --recursive https://github.com/Asphyksia/DocuMentor
cd DocuMentor
./setup.sh
```

> `setup.sh` auto-downloads submodules if you forget `--recursive`.

</details>

<details>
<summary><strong>🪟 Windows (WSL2 — recommended)</strong></summary>

```bash
# Inside WSL2 terminal (Ubuntu recommended)
git clone --recursive https://github.com/Asphyksia/DocuMentor
cd DocuMentor
./setup.sh
```

> Make sure Docker Desktop has **WSL2 backend** enabled (Settings → General → "Use the WSL 2 based engine").

</details>

<details>
<summary><strong>🪟 Windows (PowerShell / Git Bash — no WSL)</strong></summary>

```powershell
git clone --recursive https://github.com/Asphyksia/DocuMentor
cd DocuMentor

# Copy and edit the environment file
copy .env.example .env
# Edit .env with your API key and password (use notepad, VS Code, etc.)

# Start backend services
docker compose up -d

# Install and start the dashboard
cd frontend
npm install
npm run dev
```

> Without WSL, `setup.sh` won't run natively. The manual steps above do the same thing — just edit `.env` before starting.

</details>

### What setup.sh does

1. Checks requirements (Docker, Node.js, Python, disk space)
2. Asks for your RelayGPU API key and a vault password
3. Lets you pick your default AI model
4. Generates the `.env` automatically
5. Installs Hermes Agent
6. Starts all services via Docker
7. Installs dashboard dependencies

### Start DocuMentor

```bash
# Terminal 1 — Dashboard
cd frontend && npm run dev

# Terminal 2 — Agent
hermes
```

Open **http://localhost:3000** — that's it.

> ⚠️ **Do not run `hermes setup`** — DocuMentor configures Hermes automatically from your `.env`. Running the Hermes wizard will overwrite DocuMentor's configuration.

### Platform notes

| Platform | Docker networking | Shell scripts | Notes |
|----------|-------------------|---------------|-------|
| **Linux** | Native — best performance | ✅ Native | Recommended for production |
| **macOS** | Docker Desktop VM — good | ✅ Native | Apple Silicon and Intel supported |
| **Windows + WSL2** | Near-native via WSL2 backend | ✅ Bash in WSL | Recommended Windows setup |
| **Windows native** | Docker Desktop — works | ❌ Use manual steps | No `setup.sh`; edit `.env` manually |

---

## How it works

### Document processing pipeline

1. You send a file → agent calls `surfsense_upload()`
2. SurfSense indexes it with Docling — parsing runs 100% locally
3. Agent calls `surfsense_extract_tables()` to pull structured data
4. If numeric data is detected, `execute_code()` runs pandas analysis
5. Output is formatted as JSON following [DOCSTEMPLATES.md](DOCSTEMPLATES.md)
6. Dashboard renders KPIs, charts, and tables from the JSON automatically

### Natural language queries

1. You ask a question → agent calls `surfsense_query()`
2. Hybrid search across all indexed documents (semantic + full-text)
3. Cited response formatted as dashboard-ready JSON
4. Agent suggests follow-up actions ("To compare with 2024, upload that report")

---

## Supported file types

| Format | Extracted |
|--------|-----------|
| PDF | Summary · entities · tables · key paragraphs |
| Excel / CSV | Sheet data · calculated metrics · charts |
| Word (.docx) | Sections · tables · summary |
| Other | Best-effort extraction via Docling |

---

## Dashboard views

| View | When used |
|------|-----------|
| **KPI cards** | Single metric highlights (totals, averages, percentages) |
| **Bar chart** | Comparisons between categories |
| **Line chart** | Trends over time |
| **Data table** | Raw tabular data with pagination |
| **Text summary** | Long-form content, sections, key extracts |

---

## Models & cost

DocuMentor uses [RelayGPU](https://relay.opengpu.network) — premium models at reduced cost.
Run `curl https://relay.opengpu.network/v2/models` and `curl https://relay.opengpu.network/v2/pricing` for the live list.

### OpenAI-compatible endpoint
`https://relay.opengpu.network/v2/openai/v1`

| Model | Input | Output | Best for |
|-------|-------|--------|----------|
| `openai/gpt-5.4` ⭐ default | $2.50/1M | $15.00/1M | Best quality, complex analysis |
| `openai/gpt-5.2` | $1.75/1M | $14.00/1M | General purpose |
| `moonshotai/kimi-k2.5` | $0.55/1M | $2.95/1M | Multilingual, daily use |
| `deepseek-ai/DeepSeek-V3.1` | $0.55/1M | $1.66/1M | Budget, good reasoning |
| `infercom/MiniMax-M2.5` | $0.30/1M | $1.20/1M | 164K context window |
| `Qwen/Qwen3.5-397B-A17B-FP8` | $0.20/1M | $1.20/1M | Cheapest large model |
| `Qwen/Qwen3-Coder` | $1.30/1M | $5.00/1M | Code generation |

### Anthropic-compatible endpoint
`https://relay.opengpu.network/v2/anthropic/v1`

| Model | Input | Output | Best for |
|-------|-------|--------|----------|
| `anthropic/claude-sonnet-4-6` | $3.00/1M | $15.00/1M | Deep analysis, long documents |
| `anthropic/claude-opus-4-6` | $5.00/1M | $25.00/1M | Maximum quality |

> ⚠️ Anthropic models require changing `OPENAI_BASE_URL` to the Anthropic endpoint in `.env`.

**Estimated monthly cost:** €5–15 for moderate use (hundreds of documents/month).
**Per document:** ~€0.01 average with `gpt-5.4` default.

---

## Project structure

```
DocuMentor/
├── SOUL.md                        # Agent personality, workflow, onboarding
├── BOOTSTRAP.md                   # First-boot setup (read by agent)
├── DOCSTEMPLATES.md               # JSON output schemas by file type
├── setup.sh                       # Interactive installer for non-technical users
├── docker-compose.yml             # Orchestrates SurfSense + MCP + Bridge
├── .env.example                   # Single config file (3 required fields)
├── README.md
├── LICENSE
├── backend/
│   ├── mcp_wrapper.py             # MCP server — 6 tools for SurfSense
│   ├── bridge.py                  # WebSocket bridge — connects UI to MCP
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx             # Root layout (dark theme)
│   │   ├── globals.css            # Tailwind + custom styles
│   │   └── page.tsx               # Main app — sidebar + tabs + chat
│   ├── components/
│   │   ├── AppHeader.tsx          # Logo, animated tabs, connection status
│   │   ├── ChatPanel.tsx          # Chat with inline dashboards
│   │   ├── DocSidebar.tsx         # Document list sidebar
│   │   ├── SettingsPanel.tsx      # Knowledge base management
│   │   └── UploadModal.tsx        # Drag & drop upload with progress
│   ├── hooks/
│   │   └── useBridge.ts           # WebSocket client hook
│   ├── DashboardRenderer.tsx      # JSON → KPI/bar/line/table/text
│   └── package.json               # Next.js 14 + Tremor + Framer Motion
├── hermes-agent/                  # Hermes Agent (git submodule)
└── SurfSense/                     # SurfSense RAG (git submodule)
```

---

## Privacy & security

- Documents are stored and indexed locally via PostgreSQL + pgvector
- Only text is sent to the LLM for inference — no document storage on third-party servers
- Embeddings are generated locally by SurfSense
- Prompt injection protection built into the agent layer
- RBAC access control for team deployments
- You own your data

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Agent | [Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research) |
| RAG & search | [SurfSense](https://github.com/MODSetter/SurfSense) |
| Document parsing | [Docling](https://github.com/DS4SD/docling) (IBM, local) |
| LLM inference | [RelayGPU](https://relay.opengpu.network) |
| Database | PostgreSQL 17 + pgvector |
| Task queue | Redis + Celery |
| Dashboard | Next.js + [Tremor](https://tremor.so) + Recharts + [Framer Motion](https://www.framer.com/motion/) |
| Real-time layer | WebSocket bridge server (FastAPI) |
| Agent tools | MCP (Model Context Protocol) |

---

## Updating

```bash
cd DocuMentor

# Update DocuMentor (agent config, templates, MCP wrapper)
git pull

# Update SurfSense and Hermes Agent to latest
git submodule update --remote

# Restart services
cd SurfSense/docker && docker compose pull && docker compose up -d
```

Your documents and configuration are preserved on update.

---

## Uninstalling

**Linux / macOS / WSL2:**
```bash
cd DocuMentor
./uninstall.sh
```

**Windows (no WSL):**
```powershell
cd DocuMentor
docker compose down -v --remove-orphans
# Then delete the DocuMentor folder manually
```

The uninstaller (Linux/macOS/WSL2) lets you choose what to remove:
1. **Everything** — Docker containers, volumes, Hermes config, project files
2. **Docker only** — containers and volumes, keep project files
3. **Cancel**

It will ask for confirmation before deleting your `.env` (contains API key) and project files.

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT — see [LICENSE](LICENSE)

---

*DocuMentor is an independent open-source project. Not affiliated with Nous Research, SurfSense, or RelayGPU.*
