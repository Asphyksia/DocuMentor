# Architecture

> Last updated: 2026-03-25

## What DocuMentor is

DocuMentor is an **intelligent document analysis platform** for universities that connects:

1. **SurfSense** — document ingestion, chunking, embedding, hybrid search
2. **Hermes Agent** — AI reasoning with tool-use capabilities
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
│            Bridge Server (:8001) — v0.3.0                │
│  FastAPI + WebSocket                                     │
│                                                          │
│  Queries ──→ Hermes AIAgent (via run_in_executor)        │
│              ├── stream_delta_callback → ws streaming     │
│              ├── tool_progress_callback → agent_status    │
│              └── run_conversation(history) → multi-turn   │
│                                                          │
│  CRUD ────→ MCP Wrapper (direct JSON-RPC)                │
│  (upload, delete, list, create_space, extract, search)   │
│                                                          │
│  11 typed handlers · Pydantic validation                 │
│  Per-connection conversation history                     │
│  Query lock (serialized for singleton agent)             │
└──────────┬────────────────────────┬─────────────────────┘
           │ MCP (Streamable HTTP)  │ HTTP / JSON-RPC
           │                        │
┌──────────▼────────────────────────▼─────────────────────┐
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

## How queries flow (v0.3.0 — with Hermes)

```
1. User types question in chat
2. Frontend sends: { type: "query", payload: { query, search_space_id } }
3. Bridge acquires query lock (one agent call at a time)
4. Bridge creates callbacks → WebSocket streaming
5. Bridge calls AIAgent.run_conversation(query, history) via ThreadPoolExecutor
6. Hermes AIAgent reasons about the query:
   a. Decides which MCP tools to use (e.g., surfsense_query, surfsense_search_documents)
   b. Calls tools via MCP Streamable HTTP → MCP Wrapper → SurfSense
   c. Processes results, may call additional tools
   d. Generates final response
7. During execution:
   - stream_delta_callback fires per token → { type: "stream", delta: "..." }
   - tool_progress_callback fires per tool → { type: "agent_status", tool: "..." }
8. On completion:
   - Bridge stores updated conversation history
   - Sends { type: "stream", done: true }
   - Sends { type: "result", dashboard: {...} }
9. Frontend renders streamed text + dashboard visualizations

Fallback (no Hermes): Bridge calls MCP wrapper directly via JSON-RPC (no reasoning).
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

## What is DocuMentor's own code vs. dependencies

| Component | Owner | Location |
|---|---|---|
| Bridge server (v0.3.0) | **DocuMentor** | `backend/bridge.py` |
| MCP wrapper (v1.0.0) | **DocuMentor** | `surfsense-skill/mcp_server.py` |
| Frontend UI | **DocuMentor** | `frontend/` |
| Dashboard schemas | **DocuMentor** | `DOCSTEMPLATES.md` |
| Docker composition | **DocuMentor** | `docker-compose.yml` |
| SurfSense | MODSetter | `SurfSense/` (submodule) |
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

4. **Serialized queries**: The query lock means only one Hermes query runs
   at a time. Concurrent queries are queued. This is a limitation of the
   singleton AIAgent pattern — future work could use an agent pool.

5. **No offline processing**: All queries require a live LLM provider.

6. **SurfSense API contract**: The MCP wrapper assumes specific API shapes.
   The submodule is pinned to a specific commit to mitigate breakage.

## Security model

- **Network boundary**: All services on localhost / Docker internal network.
  Exposed ports: frontend (:3000), bridge WebSocket (:8001).
- **No generic passthrough**: 11 typed handlers, each Pydantic-validated.
- **Upload validation**: Filename sanitized, size enforced, temp files cleaned.
- **JWT tokens**: Cached 55min TTL, auto-refreshed, retry once on 401.
- **CORS**: Currently `*` — restrict for any network-exposed deployment.
- **Hermes isolation**: `skip_context_files=True`, `skip_memory=True` —
  no personal context leaks into document queries.

## File structure

```
DocuMentor/
├── backend/
│   ├── bridge.py              ← WebSocket gateway + Hermes integration
│   ├── Dockerfile             ← MCP wrapper container
│   ├── Dockerfile.bridge      ← Bridge container (with Hermes deps)
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
├── SurfSense/                 ← RAG backend (submodule)
├── hermes-agent/              ← AI agent (submodule)
├── docker-compose.yml
├── .env.example
├── hermes-config.example.yaml ← MCP config for Hermes
├── ARCHITECTURE.md            ← This file
├── HERMES_INTEGRATION_PLAN.md ← Integration phases
└── README.md
```
