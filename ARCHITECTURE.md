# Architecture

> Last updated: 2026-03-26

## What DocuMentor is

DocuMentor is an **intelligent document analysis platform** for universities that connects:

1. **SurfSense** — document ingestion, chunking, embedding, hybrid search
2. **Hermes Agent** — AI reasoning with tool-use capabilities (dedicated container)
3. **MCP Wrapper** — 25 tools exposing SurfSense as MCP protocol
4. **Bridge** — WebSocket gateway with streaming and conversation management
5. **Dashboard** — Next.js web UI with real-time chat, visualizations, and document management

DocuMentor does **not** implement its own:
- Document parsing (→ SurfSense + Docling)
- Vector search or RAG (→ SurfSense + pgvector)
- LLM inference (→ RelayGPU, OpenRouter, or any OpenAI-compatible provider)
- Agent orchestration (→ Hermes Agent AIAgent)

## System diagram

```
┌─────────────────────────────────────────────────────────┐
│                    User's Browser                        │
│  Next.js dashboard (:3000)                               │
│  Chat (streaming) · Documents · Dashboard · Settings     │
└──────────────────────┬──────────────────────────────────┘
                       │ WebSocket (ws://localhost:8001/ws)
                       │
┌──────────────────────▼──────────────────────────────────┐
│            Bridge Server (:8001) — v0.5.0                │
│  FastAPI + WebSocket                                     │
│                                                          │
│  Queries ──→ Hermes Service (:8002) via HTTP/SSE         │
│              ├── SSE event: delta → ws stream             │
│              ├── SSE event: tool → agent_status           │
│              └── SSE event: done → result + dashboard     │
│              (auto-fallback to direct MCP if Hermes down)│
│                                                          │
│  CRUD ────→ MCP Wrapper (direct JSON-RPC)                │
│  (upload, delete, list, create_space, extract, search)   │
│                                                          │
│  11 typed handlers · Pydantic validation                 │
│  Per-connection conversation history                     │
│  CORS restricted · Rate limiting (30 req/min)            │
└──────────┬────────────────────────┬─────────────────────┘
           │                        │ HTTP / JSON-RPC
           │                        │
┌──────────▼──────────────────────┐ │
│   Hermes Service (:8002)         │ │
│   FastAPI + SSE streaming        │ │
│                                  │ │
│   AIAgent (Nous Research)        │ │
│   - Reasoning + tool selection   │ │
│   - MCP tool calls ─────────────┼─┼──→ MCP Wrapper
│   - System prompt: DocuMentor    │ │
│   - ThreadPoolExecutor (sync→async) │
└──────────────────────────────────┘ │
                                     │
┌────────────────────────────────────▼────────────────────┐
│         MCP Wrapper (:8000) — v1.0.0                     │
│  Dual protocol:                                          │
│  /mcp/    — Streamable HTTP (for Hermes, Claude Desktop) │
│  /jsonrpc — JSON-RPC plain (for Bridge direct calls)     │
│  /health  — Health check                                 │
│                                                          │
│  25 tools: query, upload, list, delete, extract,         │
│  search, spaces, threads, status, settings...            │
│                                                          │
│  JWT auth with TTL + auto-retry on 401                   │
│  Connection pooling (httpx.AsyncClient)                  │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
                       │
┌──────────────────────▼──────────────────────────────────┐
│         SurfSense (:8929)                                │
│  Document ingestion, chunking, embedding                 │
│  Hybrid search (semantic + keyword)                      │
│  Thread-based chat with SSE streaming                    │
│  ┌──────────────┐  ┌───────────┐  ┌──────────────┐     │
│  │ PostgreSQL   │  │ Redis     │  │ Celery       │     │
│  │ + pgvector   │  │ (queue)   │  │ (workers)    │     │
│  └──────────────┘  └───────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (OpenAI-compatible)
                       │
┌──────────────────────▼──────────────────────────────────┐
│         LLM Provider                                     │
│  RelayGPU, OpenRouter, OpenAI, Ollama, etc.             │
│  Configured via .env (OPENAI_API_KEY + OPENAI_BASE_URL) │
└─────────────────────────────────────────────────────────┘
```

## How queries flow (v0.5.0 — Hermes as service)

```
1. User types question in chat
2. Frontend sends: { type: "query", payload: { query, search_space_id } }
3. Bridge checks Hermes availability (GET /health)
4. If Hermes available:
   a. Bridge POSTs query + conversation history to Hermes service (/query)
   b. Hermes service returns SSE stream
   c. Bridge forwards SSE events to WebSocket:
      - event: delta → { type: "stream", delta: "..." }
      - event: tool  → { type: "agent_status", tool: "..." }
      - event: done  → { type: "result", dashboard: {...} }
   d. Hermes internally calls MCP tools on mcp-wrapper
   e. Bridge stores updated conversation history
5. If Hermes unavailable (fallback):
   a. Bridge calls MCP wrapper directly via JSON-RPC (surfsense_query)
   b. Returns result without AI reasoning
6. Frontend renders streamed text + dashboard visualizations
```

## How uploads flow

```
1. User drops file in UI
2. Frontend encodes as base64, sends: { type: "upload", payload: {...} }
3. Bridge validates (Pydantic: filename, size ≤50MB, search_space_id)
4. Bridge decodes base64 → temp file, frees b64 from memory
5. Bridge calls MCP wrapper: surfsense_upload(file_path, search_space_id)
6. MCP wrapper POSTs multipart to SurfSense /api/v1/documents/fileupload
7. SurfSense queues document (Docling ETL → chunks → embeddings)
8. Bridge polls surfsense_document_status every 2s (max 60s)
9. Once ready, Bridge calls surfsense_extract_tables
10. Bridge sends dashboard JSON to frontend
11. Frontend renders via DashboardRenderer
```

## Docker services

| Service | Port | Container | Role |
|---|---|---|---|
| **bridge** | 8001 | `Dockerfile.bridge` | WebSocket gateway, query routing |
| **hermes** | 8002 | `hermes-service/Dockerfile` | AI reasoning + MCP tool use |
| **mcp-wrapper** | 8000 | `Dockerfile.mcp` | 25 MCP tools over SurfSense |
| **surfsense-backend** | 8929 | (from SurfSense) | RAG, search, doc processing |
| **postgres** | 5432 | (from SurfSense) | Data + pgvector |
| **redis** | 6379 | (from SurfSense) | Task queue |

## What is DocuMentor's own code vs. dependencies

| Component | Owner | Location |
|---|---|---|
| Bridge server (v0.5.0) | **DocuMentor** | `backend/bridge.py` |
| Hermes HTTP wrapper | **DocuMentor** | `hermes-service/server.py` |
| MCP wrapper (v1.0.0) | **DocuMentor** | `surfsense-skill/mcp_server.py` |
| Frontend UI | **DocuMentor** | `frontend/` |
| Dashboard schemas | **DocuMentor** | `DOCSTEMPLATES.md` |
| Docker composition | **DocuMentor** | `docker-compose.yml` |
| SurfSense | MODSetter | SurfSense Docker image |
| Hermes Agent | Nous Research | `hermes-agent/` (submodule) |
| surfsense-skill | **DocuMentor** | `surfsense-skill/` (submodule, own repo) |

## Known limitations

1. **LLM dependency for structured output**: Dashboard quality depends on
   the model's ability to return valid JSON. The frontend handles malformed
   data gracefully with fallback rendering.

2. **Single-user design**: No authentication, no RBAC, no multi-tenancy.
   SurfSense uses a single admin account configured in .env.

3. **Base64 uploads**: Files are encoded in-browser. The bridge enforces 50MB
   and frees memory after decode, but large files spike RAM temporarily.

4. **Concurrent queries**: Hermes service uses a singleton AIAgent with
   ThreadPoolExecutor (4 workers). Heavy concurrent load may queue.

5. **No offline processing**: All queries require a live LLM provider.

6. **SurfSense API contract**: The MCP wrapper assumes specific API shapes.
   The submodule is pinned to a specific commit to mitigate breakage.

## Security model

- **Network boundary**: All services on localhost / Docker internal network.
  Exposed ports: frontend (:3000), bridge WebSocket (:8001).
- **CORS**: Restricted to configured origins (default: localhost:3000).
- **Rate limiting**: 30 requests per 60s per WebSocket connection.
- **No generic passthrough**: 11 typed handlers, each Pydantic-validated.
- **Upload validation**: Filename sanitized, size enforced, temp files cleaned.
- **JWT tokens**: Cached 55min TTL, auto-refreshed, retry once on 401.
- **Hermes isolation**: `skip_context_files=True`, `skip_memory=True` —
  no personal context leaks into document queries.
- **Inter-service**: Bridge ↔ Hermes ↔ MCP Wrapper communicate over Docker
  internal network. Only bridge exposes a port to the host.

## File structure

```
DocuMentor/
├── backend/
│   ├── bridge.py              ← WebSocket gateway + Hermes HTTP client
│   ├── Dockerfile.bridge      ← Bridge container (lightweight)
│   ├── Dockerfile.mcp         ← MCP wrapper container
│   └── requirements.txt
├── hermes-service/
│   ├── server.py              ← HTTP/SSE wrapper for AIAgent
│   ├── Dockerfile             ← Hermes container (with all agent deps)
│   ├── hermes-config.yaml     ← MCP config (Docker internal URLs)
│   └── requirements.txt
├── frontend/
│   ├── app/page.tsx           ← Main page (wiring)
│   ├── components/
│   │   ├── ChatPanel.tsx      ← Chat with streaming support
│   │   ├── AppHeader.tsx
│   │   ├── DocSidebar.tsx
│   │   ├── SettingsPanel.tsx
│   │   └── UploadModal.tsx
│   ├── hooks/
│   │   ├── useBridge.ts       ← WebSocket client
│   │   ├── useChatState.ts    ← Chat state with streaming
│   │   ├── useDashboardState.ts
│   │   ├── useDocumentsState.ts
│   │   └── useUploadState.ts
│   ├── types/bridge.ts        ← Protocol types (discriminated unions)
│   └── DashboardRenderer.tsx  ← JSON → visual dashboard
├── surfsense-skill/           ← MCP server (own repo, submodule)
│   └── mcp_server.py         ← 25 tools, dual protocol
├── hermes-agent/              ← AI agent source (submodule)
├── docs/                      ← Audit reports, improvement plans
├── docker-compose.yml
├── .env.example
├── hermes-config.example.yaml ← MCP config template (local dev)
├── ARCHITECTURE.md            ← This file
├── HERMES_INTEGRATION_PLAN.md ← Integration phases
└── README.md
```
