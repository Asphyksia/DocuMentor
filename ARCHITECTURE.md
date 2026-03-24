# Architecture

> Last updated: 2026-03-24

## What DocuMentor is

DocuMentor is an **integration layer** that connects three external systems and adds value through:

1. A unified web UI for document intelligence
2. A WebSocket bridge that translates user actions into MCP tool calls
3. An MCP wrapper that adapts the SurfSense API for agent consumption
4. Dashboard rendering contracts (JSON schemas for structured data visualization)
5. A guided setup experience for non-technical users

DocuMentor does **not** implement its own:
- Document parsing (→ SurfSense + Docling)
- Vector search or RAG (→ SurfSense + pgvector)
- LLM inference (→ RelayGPU or any OpenAI-compatible provider)
- Agent orchestration (→ Hermes Agent)

## System diagram

```
┌─────────────────────────────────────────────┐
│              User's Browser                  │
│  Next.js dashboard (:3000)                   │
│  Chat · Documents · Dashboard · Settings     │
└──────────────────┬──────────────────────────┘
                   │ WebSocket (ws://localhost:8001/ws)
                   │
┌──────────────────▼──────────────────────────┐
│         Bridge Server (:8001)                │  ← DocuMentor own code
│  FastAPI + WebSocket                         │
│  - Message validation (Pydantic)             │
│  - 10 typed handlers (no generic passthrough)│
│  - Status broadcasting                       │
│  - Upload orchestration (decode → MCP → poll)│
└──────────────────┬──────────────────────────┘
                   │ HTTP / JSON-RPC
                   │
┌──────────────────▼──────────────────────────┐
│        MCP Wrapper (:8000)                   │  ← DocuMentor own code
│  FastAPI + JSON-RPC (MCP protocol)           │     (also: surfsense-skill repo)
│  - 25 tools organized by category            │
│  - JWT auth with TTL + auto-retry on 401     │
│  - Explicit argument routing per tool        │
└──────────────────┬──────────────────────────┘
                   │ REST API
                   │
┌──────────────────▼──────────────────────────┐
│        SurfSense (:8929)                     │  ← External dependency
│  Document ingestion, chunking, embedding     │     (git submodule)
│  Hybrid search (semantic + keyword)          │
│  Thread-based chat with streaming            │
│  ┌─────────────┐  ┌──────────────┐          │
│  │ PostgreSQL   │  │ Redis        │          │
│  │ + pgvector   │  │ (task queue) │          │
│  └─────────────┘  └──────────────┘          │
└──────────────────┬──────────────────────────┘
                   │ HTTP (OpenAI-compatible)
                   │
┌──────────────────▼──────────────────────────┐
│        LLM Provider                          │  ← External service
│  RelayGPU, OpenAI, Ollama, etc.             │
│  Configured via .env                         │
└─────────────────────────────────────────────┘

Optional:
┌─────────────────────────────────────────────┐
│        Hermes Agent                          │  ← External dependency
│  Uses MCP Wrapper as tool server             │     (git submodule)
│  Provides agent orchestration layer          │
│  Not required for dashboard-only usage       │
└─────────────────────────────────────────────┘
```

## What is DocuMentor's own code vs. dependencies

| Component | Owner | Location |
|---|---|---|
| Bridge server | **DocuMentor** | `backend/bridge.py` |
| MCP wrapper | **DocuMentor** | `backend/mcp_wrapper.py` (also `surfsense-skill/`) |
| Shared modules | **DocuMentor** | `backend/documenter/` |
| Frontend UI | **DocuMentor** | `frontend/` |
| Dashboard schemas | **DocuMentor** | `DOCSTEMPLATES.md` |
| Setup scripts | **DocuMentor** | `setup.sh`, `uninstall.sh` |
| Docker composition | **DocuMentor** | `docker-compose.yml` |
| SurfSense | MODSetter | `SurfSense/` (submodule) |
| Hermes Agent | Nous Research | `hermes-agent/` (submodule) |
| surfsense-skill | **DocuMentor** | `surfsense-skill/` (submodule, own repo) |

## Data flow: upload

```
1. User drops file in UI
2. Frontend encodes as base64, sends via WebSocket: { type: "upload", payload: {...} }
3. Bridge validates payload (Pydantic: filename, size, search_space_id)
4. Bridge decodes base64 → temp file, frees b64 from memory
5. Bridge calls MCP wrapper: surfsense_upload(file_path, search_space_id)
6. MCP wrapper authenticates with SurfSense (JWT, cached with TTL)
7. MCP wrapper POSTs multipart to SurfSense /api/v1/documents/fileupload
8. SurfSense queues document for processing (Docling ETL → chunks → embeddings)
9. Bridge polls surfsense_document_status every 2s (max 60s)
10. Once ready, Bridge calls surfsense_extract_tables → model generates structured JSON
11. Bridge sends dashboard JSON to frontend via WebSocket
12. Frontend renders via DashboardRenderer (KPI, bar, line, pie, table, etc.)
```

## Data flow: natural language query

```
1. User types question in chat
2. Frontend sends via WebSocket: { type: "query", payload: { query, search_space_id } }
3. Bridge validates, calls MCP wrapper: surfsense_query(query, search_space_id)
4. MCP wrapper creates a thread in SurfSense (or reuses existing)
5. MCP wrapper streams response from SurfSense /api/v1/threads/{id}/messages
6. MCP wrapper attempts to parse structured dashboard JSON from model response
7. Falls back to { type: "summary", content: "..." } if parsing fails
8. Bridge forwards dashboard JSON to frontend
9. Frontend renders inline in chat or in dashboard panel
```

## Known limitations

1. **LLM dependency for structured output**: Dashboard quality depends entirely on
   the model's ability to return valid JSON matching DOCSTEMPLATES.md schemas.
   There is no server-side validation of model output — the frontend must handle
   malformed or incomplete data gracefully.

2. **Single-user design**: No authentication, no RBAC, no multi-tenancy.
   SurfSense uses a single admin account configured in .env.

3. **Base64 uploads**: Files are encoded in-browser and sent over WebSocket.
   This doubles memory usage temporarily. The bridge enforces a 50MB limit
   and frees memory immediately after decode, but large files will spike RAM.

4. **No offline processing**: All queries require a live LLM provider.
   If RelayGPU (or configured provider) is down, queries fail.

5. **SurfSense API contract**: The MCP wrapper assumes specific SurfSense API
   shapes. If SurfSense changes its API between versions, the wrapper may break.
   The submodule is pinned to a specific commit to mitigate this.

6. **No end-to-end encryption**: Data in transit between services is HTTP
   (not HTTPS) within the Docker network. Fine for localhost, not for
   network-exposed deployments without a reverse proxy.

## Security model

- **Network boundary**: All services run on localhost or within a Docker network.
  The only port exposed to the user's browser is the frontend (:3000) and
  the bridge WebSocket (:8001).
- **No generic passthrough**: The bridge exposes exactly 10 message types.
  Each one is validated before dispatch. There is no way to call arbitrary
  MCP tools from the frontend.
- **Upload validation**: Filename sanitized (path traversal stripped),
  size enforced pre-decode, temp files cleaned after use.
- **JWT tokens**: Cached with 55-minute TTL, auto-refreshed. Retry once on 401.
- **CORS**: Currently `*` — acceptable for localhost, should be restricted
  for any network-exposed deployment.

## File structure

```
DocuMentor/
├── backend/
│   ├── bridge.py              ← WebSocket gateway (629 lines)
│   ├── mcp_wrapper.py         ← MCP server, 25 tools (716 lines)
│   ├── documenter/            ← Shared modules
│   │   ├── surfsense_client.py  ← HTTP client (auth, retry, pooling)
│   │   └── errors.py           ← Error codes and types
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                   ← Next.js pages
│   ├── components/            ← React components
│   │   └── ui/                ← shadcn/ui base components
│   ├── hooks/useBridge.ts     ← WebSocket client hook
│   ├── DashboardRenderer.tsx  ← JSON → visual dashboard
│   └── lib/utils.ts           ← Tailwind utilities
├── SurfSense/                 ← Git submodule (external)
├── hermes-agent/              ← Git submodule (external)
├── surfsense-skill/           ← Git submodule (own repo)
├── docker-compose.yml
├── setup.sh
├── .env.example
├── ARCHITECTURE.md            ← This file
├── DOCSTEMPLATES.md           ← Dashboard JSON schemas
├── BOOTSTRAP.md               ← Hermes agent onboarding
└── README.md
```
