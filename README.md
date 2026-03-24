# DocuMentor

**Document intelligence platform for universities.**

Upload documents. Ask questions in natural language. Get visual dashboards.
Self-hosted — designed for local deployment.

Built on [SurfSense](https://github.com/MODSetter/SurfSense) · [Hermes Agent](https://github.com/NousResearch/hermes-agent) · [RelayGPU](https://relay.opengpu.network)

---

## What it does

DocuMentor is a self-hosted integration layer that connects document parsing, RAG search, and LLM inference into a single web interface with visual dashboards. It processes PDFs, spreadsheets, and Word documents — extracting tables, metrics, and summaries — then renders them as interactive charts you can explore through natural language.

> **Note:** DocuMentor orchestrates existing open-source tools (SurfSense for RAG, Docling for parsing, pgvector for search). Its own value is the unified UI, the MCP tool layer, the bridge server, and the guided setup experience. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full picture.

```
┌──────────────────────────────────────────┐
│        localhost:3000 — Unified UI        │
│  ┌──────────┬───────────────────────────┐│
│  │          │  💬 Chat  📊 Dashboard ⚙️ ││
│  │  📁 Docs │                           ││
│  │          │  KPIs · Charts · Tables   ││
│  │          │  Pie · Area · Deltas      ││
│  └──────────┴───────────────────────────┘│
└──────────────────┬───────────────────────┘
                   │ WebSocket
                   ▼
          Bridge Server (:8001)
   Validated handlers · Status updates
                   │ JSON-RPC
                   ▼
     surfsense-skill MCP (:8000)
25 tools — docs · spaces · chat · reports
                   │ REST API
                   ▼
         SurfSense (:8929)
Hybrid search · 50+ formats · Docling
     PostgreSQL + pgvector
                   │
                   ▼
    LLM Provider (RelayGPU, etc.)
```

---

## Features

- **📄 Document processing** — PDF, Excel, CSV, Word via Docling (runs locally via SurfSense)
- **🔍 Hybrid search** — semantic + full-text with Reciprocal Rank Fusion (via SurfSense)
- **📊 Dashboard rendering** — KPI cards, bar/line/area/pie charts, data tables, metric deltas
- **💬 Natural language queries** — ask questions, get structured answers
- **🖥️ Unified single-page UI** — sidebar, chat, dashboard, and settings in one window
- **⚡ Real-time updates** — WebSocket bridge with live status (uploading → indexing → ready)
- **🎨 Dark UI** — shadcn/ui components, Framer Motion animations, drag & drop upload
- **🤖 Guided setup** — interactive `setup.sh` asks 3 questions and configures everything

### Current limitations

- **Single-user only** — no authentication, no RBAC, no multi-tenancy
- **LLM-dependent dashboards** — structured output quality depends on the model's JSON generation
- **No prompt injection protection** — input validation exists but is not a security boundary
- **Base64 uploads** — files are encoded in-browser, temporarily doubling memory usage (50MB limit enforced)
- **Requires live LLM** — offline operation is not supported for queries
- **Early stage** — functional for demos and evaluation, not production-hardened

See [ARCHITECTURE.md](ARCHITECTURE.md) for a complete list of known limitations and the security model.

---

## Quick Start

### Requirements

| Requirement | Details |
|-------------|---------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine on Linux) | For SurfSense, PostgreSQL, Redis |
| [Git](https://git-scm.com/downloads) | To clone the repo with submodules |
| [Node.js 18+](https://nodejs.org/) | For the Next.js dashboard |
| [Python 3.11+](https://www.python.org/downloads/) | For the MCP wrapper and bridge server |
| ~5 GB disk space | Docker images + dependencies |
| LLM API key | [RelayGPU](https://relay.opengpu.network) recommended (`relay_sk_...`) |

### Install

<details>
<summary><strong>🐧 Linux / 🍎 macOS / 🪟 Windows (WSL2)</strong></summary>

```bash
git clone --recursive https://github.com/Asphyksia/DocuMentor
cd DocuMentor
./setup.sh
```

> `setup.sh` auto-downloads submodules if you forget `--recursive`.

</details>

<details>
<summary><strong>🪟 Windows (PowerShell / Git Bash — no WSL)</strong></summary>

```powershell
git clone --recursive https://github.com/Asphyksia/DocuMentor
cd DocuMentor

# Copy and edit the environment file
copy .env.example .env
# Edit .env with your API key and password

# Start backend services
docker compose up -d

# Install and start the dashboard
cd frontend
npm install
npm run dev
```

</details>

### What setup.sh does

1. Checks requirements (Docker, Node.js, Python, disk space)
2. Asks for your API key and a vault password
3. Lets you pick your default AI model
4. Generates `.env` and symlinks it to `SurfSense/docker/.env`
5. Starts all services via Docker Compose
6. Installs dashboard dependencies

### Start

```bash
# Terminal 1 — Dashboard
cd frontend && npm run dev

# Terminal 2 — Agent (optional, for conversational setup)
hermes
```

Open **http://localhost:3000**.

> ⚠️ **Do not run `hermes setup`** — DocuMentor configures Hermes from `.env`. The Hermes wizard would overwrite DocuMentor's configuration.

---

## How it works

### Document upload flow

1. User drops file in UI → browser encodes as base64, sends via WebSocket
2. Bridge server validates payload (filename, size, search_space_id) and decodes to temp file
3. Bridge calls MCP wrapper → `surfsense_upload()` → SurfSense REST API
4. SurfSense indexes with Docling (parsing runs inside Docker, locally)
5. Bridge polls document status until ready (max 60s)
6. Bridge calls `surfsense_extract_tables()` → model generates structured JSON
7. Dashboard renders the JSON as charts and tables

### Natural language query flow

1. User types question → bridge calls `surfsense_query()`
2. MCP wrapper creates/reuses a thread, streams response from SurfSense
3. Response is parsed for structured JSON; falls back to text summary if parsing fails
4. Frontend renders inline in chat or dashboard panel

> Dashboard quality depends on the LLM's ability to produce valid JSON matching the schemas in [DOCSTEMPLATES.md](DOCSTEMPLATES.md). There is no server-side validation of model output — the frontend handles incomplete data gracefully.

---

## Supported file types

| Format | What's extracted |
|--------|-----------------|
| PDF | Summary · entities · tables · key paragraphs |
| Excel / CSV | Sheet data · calculated metrics · charts |
| Word (.docx) | Sections · tables · summary |
| PowerPoint (.pptx) | Slide overview · tables · charts |
| HTML | Page content · headings · tables · links |
| Images (scanned docs) | OCR text · detected tables · form fields |
| Other | Best-effort extraction via Docling |

---

## Dashboard views

| View | When used |
|------|-----------|
| **KPI cards** | Single metric highlights (totals, averages, percentages) |
| **Bar chart** | Comparisons between categories |
| **Line chart** | Trends over time |
| **Area chart** | Cumulative trends |
| **Pie chart** | Distribution breakdowns |
| **Metric delta** | Year-over-year or period comparisons with trend arrows |
| **Data table** | Raw tabular data |
| **Text summary** | Long-form content, sections, key extracts |

---

## Privacy & data flow

- **Document parsing**: Runs locally inside Docker via SurfSense + Docling. No documents are sent externally for parsing.
- **Embeddings**: Generated locally by SurfSense using `sentence-transformers/all-MiniLM-L6-v2`.
- **LLM queries**: Document text (not files) is sent to the configured LLM provider for inference. If using RelayGPU or OpenAI, this text leaves your machine. For full locality, use a local model via Ollama.
- **Storage**: PostgreSQL + pgvector, running in Docker on your machine.
- **No telemetry**: DocuMentor does not phone home or collect usage data.

> ⚠️ "Fully local" only applies if you use a local LLM. With cloud providers like RelayGPU, document text is sent for inference.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| RAG & search | [SurfSense](https://github.com/MODSetter/SurfSense) (submodule) |
| Document parsing | [Docling](https://github.com/DS4SD/docling) (IBM, via SurfSense) |
| Agent | [Hermes Agent](https://github.com/NousResearch/hermes-agent) (submodule, optional) |
| LLM inference | [RelayGPU](https://relay.opengpu.network) or any OpenAI-compatible provider |
| Database | PostgreSQL 17 + pgvector |
| Task queue | Redis + Celery |
| Dashboard | Next.js 14 + [shadcn/ui](https://ui.shadcn.com) + Recharts + [Framer Motion](https://www.framer.com/motion/) |
| Real-time layer | WebSocket bridge server (FastAPI) |
| Agent tools | [surfsense-skill](https://github.com/Asphyksia/surfsense-skill) (25 MCP tools, submodule) |

---

## Project structure

```
DocuMentor/
├── ARCHITECTURE.md                # Technical architecture, data flows, limitations
├── DOCSTEMPLATES.md               # Dashboard JSON schemas by file type
├── BOOTSTRAP.md                   # Hermes agent first-boot config
├── SOUL.md                        # Agent personality and workflow
├── setup.sh                       # Interactive installer
├── uninstall.sh                   # Interactive uninstaller
├── docker-compose.yml             # Orchestrates all backend services
├── .env.example                   # Config template (3 required fields)
├── backend/
│   ├── bridge.py                  # WebSocket gateway — 10 validated handlers
│   ├── mcp_wrapper.py             # MCP server — 25 tools for SurfSense
│   ├── documenter/                # Shared modules (client, errors)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                       # Next.js pages and layout
│   ├── components/                # React components
│   │   └── ui/                    # shadcn/ui base components
│   ├── hooks/useBridge.ts         # WebSocket client hook
│   ├── DashboardRenderer.tsx      # JSON → visual dashboards
│   └── lib/utils.ts
├── hermes-agent/                  # Git submodule (Nous Research)
├── SurfSense/                     # Git submodule (MODSetter)
└── surfsense-skill/               # Git submodule (own repo)
```

---

## External dependencies

DocuMentor depends on external projects that have their own release cycles:

| Dependency | Pinned via | Risk if it changes |
|---|---|---|
| SurfSense | Git submodule (specific commit) | API changes could break MCP wrapper |
| Hermes Agent | Git submodule (specific commit) | Config format changes could break BOOTSTRAP.md |
| RelayGPU | API endpoint in `.env` | Pricing/model changes — switch provider if needed |
| Docling | Bundled inside SurfSense | Transparent to DocuMentor |

Submodules are pinned to tested commits. Run `git submodule update --remote` to update (at your own risk — test after updating).

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `docker compose up` fails | Make sure Docker Desktop is running. On WSL2, enable "WSL 2 based engine" in Docker settings. |
| Frontend shows "Disconnected" | Create `frontend/.env.local` with `NEXT_PUBLIC_BRIDGE_URL=ws://localhost:8001/ws` and restart `npm run dev`. |
| SurfSense containers keep restarting | Check `docker logs surfsense-backend`. Usually missing `.env` or wrong `SECRET_KEY`. |
| Upload fails with timeout | Document indexing can take 30-60s for large files. If it consistently fails, check SurfSense logs. |
| "MCP wrapper not responding" | Run `curl http://localhost:8000/health`. If it fails, check `docker logs` for the MCP container. |
| Model returns bad dashboard JSON | Try a more capable model (e.g. `gpt-5.4` instead of cheaper options). Dashboard quality = model quality. |

---

## Models & cost

DocuMentor works with any OpenAI-compatible LLM provider. [RelayGPU](https://relay.opengpu.network) is preconfigured for affordable access to premium models.

Run `curl https://relay.opengpu.network/v2/models` for the live model list.

**Estimated cost:** €5–15/month for moderate use (hundreds of documents). ~€0.01 per document with `gpt-5.4`.

---

## Updating

```bash
cd DocuMentor
git pull
git submodule update --init --recursive
cd SurfSense/docker && docker compose pull && docker compose up -d
```

Your documents and configuration are preserved on update.

---

## Uninstalling

```bash
cd DocuMentor
./uninstall.sh   # Linux / macOS / WSL2
```

Windows (no WSL): `docker compose down -v --remove-orphans`, then delete the folder.

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE)

---

*DocuMentor is an independent open-source project. Not affiliated with Nous Research, SurfSense, or RelayGPU.*
