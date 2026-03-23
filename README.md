# DocuMentor

**Agentic document intelligence platform for universities.**

Upload documents. Ask questions in natural language. Get interactive dashboards.
Everything runs locally — your data never leaves your infrastructure.

Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) · [SurfSense](https://github.com/MODSetter/SurfSense) · [RelayGPU](https://relay.opengpu.network)

---

## What it does

DocuMentor is a self-hosted AI agent that turns institutional documents into structured, queryable knowledge. It processes PDFs, spreadsheets, and Word documents — extracting tables, metrics, and summaries — then renders them as visual dashboards you can explore through natural language.

```
You  ──────────────────────────────────────────────────────────────►  Dashboard
      chat / Telegram                                                  KPIs · Charts · Tables
           │
           ▼
    DocuMentor Agent          Hermes Agent · SOUL.md personality
           │                  Persistent memory · Multi-language
           ▼
      MCP Wrapper             Bridges agent ↔ knowledge base
           │
           ▼
    SurfSense (RAG)           Hybrid search · 50+ file formats
    PostgreSQL + pgvector     Docling local parsing · No external APIs
           │
           ▼
    RelayGPU (LLM)            Affordable inference · OpenAI-compatible
    Claude Sonnet / Qwen      ~€0.01 per document
```

---

## Features

- **📄 50+ file formats** — PDF, Excel, CSV, Word, and more via Docling (runs locally)
- **🔍 Hybrid search** — semantic + full-text with Reciprocal Rank Fusion
- **📊 Auto-generated dashboards** — KPI cards, bar charts, line charts, data tables
- **💬 Natural language queries** — ask questions, get cited answers
- **🌍 Multi-language** — detects user language automatically, responds in kind
- **🤖 Conversational setup** — the agent guides you through installation interactively
- **🔒 Fully private** — no data sent to third parties, all processing local
- **🛡️ Prompt injection protection** — built-in input validation
- **👥 Team collaboration** — RBAC roles, shared search spaces, real-time chat

---

## Quick Start

### Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running
- Python 3.11+
- Node.js 18+ (for the dashboard)
- ~5 GB free disk space
- A [RelayGPU API key](https://relay.opengpu.network) — `relay_sk_...`

### Install

```bash
# 1. Clone the repo
git clone https://github.com/Asphyksia/DocuMentor
cd DocuMentor

# 2. Install Hermes Agent (without running the setup wizard)
cd DocuMentor/hermes-agent && ./setup-hermes.sh
source ~/.bashrc && cd ..

# 3. Start DocuMentor
hermes
```

> ⚠️ **Do not run `hermes setup`** — DocuMentor configures Hermes automatically from your `.env` file on first boot. Running the Hermes setup wizard will overwrite DocuMentor's configuration.

That's it. Hermes reads `SOUL.md` and `BOOTSTRAP.md` and walks you through the rest — SurfSense, the MCP wrapper, and the dashboard are all set up automatically during the first conversation.

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
├── SOUL.md                      # Agent personality, workflow, onboarding flow
├── BOOTSTRAP.md                 # First-boot setup instructions (read by agent)
├── DOCSTEMPLATES.md             # JSON output schemas by file type
├── README.md
├── LICENSE
├── backend/
│   ├── mcp_wrapper.py           # MCP server — exposes SurfSense as agent tools
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── DashboardRenderer.tsx    # Next.js component: JSON → charts & tables
├── hermes-agent/                # Hermes Agent (reference)
└── SurfSense/                   # SurfSense RAG backend (reference)
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

## Self-hosting infrastructure

For production deployment, a VPS with **4–8 GB RAM** is sufficient.

| Component | Cost |
|-----------|------|
| VPS (4–8 GB RAM) | ~€15/month |
| RelayGPU LLM | ~€0.01/document |
| Everything else | Free (open source) |

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
| Dashboard | Next.js + [Tremor](https://tremor.so) + Recharts |
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

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT — see [LICENSE](LICENSE)

---

*DocuMentor is an independent open-source project. Not affiliated with Nous Research, SurfSense, or RelayGPU.*
