# Hermes Integration Plan — Phase 1
## Bridge as Intelligent Gateway

### Goal
Route user queries through Hermes Agent instead of direct MCP tool calls.
Hermes reasons about the query, decides which MCP tools to use, executes them,
and returns a structured response — all streamed to the frontend in real-time.

### Architecture Change

**Before (current):**
```
Frontend → WebSocket → Bridge → JSON-RPC → MCP Wrapper → SurfSense
                                                ↑
                                Hermes (separate CLI, not connected)
```

**After (Phase 1):**
```
Frontend → WebSocket → Bridge ──→ AIAgent.run_conversation() ──→ MCP tools → SurfSense
                         │                    ↓ callbacks
                         │        stream_delta / tool_progress / thinking
                         │                    ↓
                         └──── ws.send_json() to frontend (real-time)

CRUD operations (upload, delete, list_docs, etc.) → still direct to MCP wrapper
```

### What Changes

#### bridge.py
- Import `AIAgent` from hermes-agent
- Create a singleton `AIAgent` instance at startup (or per-session)
- `handle_query()` → delegates to `AIAgent.run_conversation()` via `run_in_executor()`
- Callbacks stream progress to WebSocket in real-time
- All other handlers (upload, list_docs, create_space, delete_*) → unchanged, still direct MCP

#### New WebSocket message types (Server → Client)
- `{ type: "stream", payload: { delta: "token..." } }` — streaming text tokens
- `{ type: "agent_status", payload: { tool: "surfsense_query", status: "running" } }` — tool execution status
- `{ type: "thinking", payload: { text: "..." } }` — agent reasoning (optional, for debug)

#### Frontend changes (minimal for Phase 1)
- `useBridge.ts` → handle new `stream` message type
- `ChatPanel.tsx` → render streaming tokens as they arrive
- `useChatState.ts` → add streaming message state

#### Config
- `HERMES_HOME` env var → points to `~/.hermes` (or DocuMentor-specific dir)
- `~/.hermes/config.yaml` must have `mcp_servers.surfsense` pointing to MCP wrapper
- Agent model configurable via env: `HERMES_MODEL` (default: from config.yaml)

### AIAgent Configuration

```python
agent = AIAgent(
    # Model — use whatever is configured
    model=os.getenv("HERMES_MODEL", "qwen/qwen3-235b-a22b"),
    base_url=os.getenv("HERMES_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("HERMES_API_KEY", os.getenv("OPENROUTER_API_KEY")),
    
    # Platform hints
    platform="web",
    
    # Only MCP tools — no terminal, no browser, no file access
    enabled_toolsets=["mcp-surfsense"],
    
    # No personal context
    skip_context_files=True,
    skip_memory=True,
    
    # Suppress console output (we're running as a service)
    quiet_mode=True,
    
    # Streaming callbacks
    stream_delta_callback=on_stream_delta,
    tool_progress_callback=on_tool_progress,
    thinking_callback=on_thinking,
    status_callback=on_status,
    
    # System prompt for DocuMentor context
    ephemeral_system_prompt=DOCUMENTER_SYSTEM_PROMPT,
)
```

### System Prompt

```
You are DocuMentor, an intelligent document analysis assistant for universities.
You help users understand, query, and extract insights from their uploaded documents.

You have access to SurfSense tools for document management and querying.
When answering questions:
1. Use surfsense_query to search the knowledge base
2. Structure your response clearly
3. If the query involves specific documents, reference them
4. For data extraction, return structured JSON when appropriate

Always respond in the same language the user writes in.
```

### Conversation History Management

- Bridge maintains per-WebSocket conversation history in memory
- On new query: append user message, call `run_conversation(conversation_history=history)`
- After response: update history with result["messages"]
- On WebSocket disconnect: discard history (stateless sessions for now)
- Phase 3 will add persistent threads via SurfSense

### Threading Model

```
Main async event loop (FastAPI/uvicorn)
  │
  ├── WebSocket handler (async) — receives messages, sends responses
  │
  └── ThreadPoolExecutor (max_workers=4)
        └── AIAgent.run_conversation() (sync, blocking)
              └── callbacks → asyncio.run_coroutine_threadsafe() → ws.send_json()
```

This is the exact same pattern used by Hermes' ACP adapter.

### Docker Changes

Option A (recommended): Bridge container installs hermes-agent as dependency
- Add hermes-agent to bridge's requirements.txt / Dockerfile
- Set HERMES_HOME to a volume for config persistence
- MCP wrapper stays as separate container

Option B: Merge bridge + hermes into one container
- More complex Dockerfile but simpler networking

### Migration Path

1. Phase 1: Query routing through Hermes (this plan)
2. Phase 2: Streaming tokens to frontend + typing indicators
3. Phase 3: Persistent conversation threads
4. Phase 4: Hermes-driven document analysis on upload

### Files to Modify

- `backend/bridge.py` — main changes (AIAgent integration)
- `backend/requirements.txt` — add hermes-agent dependency path
- `backend/Dockerfile` — install hermes-agent
- `frontend/types/bridge.ts` — add stream/agent_status types
- `frontend/hooks/useBridge.ts` — handle stream messages
- `frontend/hooks/useChatState.ts` — streaming message state
- `frontend/components/ChatPanel.tsx` — render streaming text
- `docker-compose.yml` — env vars for Hermes config
