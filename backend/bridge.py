"""
DocuMentor Bridge Server
------------------------
WebSocket gateway between the Next.js dashboard and the MCP wrapper / Hermes Agent.

Design principles (v0.3.0 — Hermes integration):
  - Queries are routed through Hermes AIAgent for intelligent reasoning.
  - CRUD operations (upload, delete, list) go direct to MCP wrapper.
  - Streaming: agent responses stream token-by-token to the frontend.
  - Per-connection conversation history for multi-turn chat.
  - Explicit message allowlist: only known message types are dispatched.
  - Pydantic validation: every inbound payload is validated before processing.
  - Structured error responses with error codes.

Protocol — Client → Server:
  { "type": "query",            "payload": { "query": "...", "search_space_id": 1 } }
  { "type": "upload",           "payload": { "filename": "...", "data": "<base64>", "search_space_id": 1 } }
  { "type": "list_docs",        "payload": { "search_space_id": 1 } }
  { "type": "list_spaces" }
  { "type": "create_space",     "payload": { "name": "...", "description": "..." } }
  { "type": "extract",          "payload": { "doc_id": 1, "search_space_id": 1 } }
  { "type": "delete_document",  "payload": { "document_id": 5, "search_space_id": 1 } }
  { "type": "delete_space",     "payload": { "search_space_id": 2 } }
  { "type": "search_documents", "payload": { "title": "budget", "search_space_id": 1 } }
  { "type": "clear" }
  { "type": "status" }

Protocol — Server → Client:
  { "type": "result",     "payload": { ... } }
  { "type": "stream",     "payload": { "delta": "...", "done": false } }
  { "type": "agent_status", "payload": { "tool": "...", "status": "running" } }
  { "type": "status",     "payload": { "state": "...", "message": "..." } }
  { "type": "documents",  "payload": { ... } }
  { "type": "spaces",     "payload": { ... } }
  { "type": "error",      "payload": { "code": "...", "message": "..." } }
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Hermes AIAgent — imported from hermes-agent source
# ---------------------------------------------------------------------------

HERMES_AGENT_DIR = os.getenv(
    "HERMES_AGENT_DIR",
    os.path.join(os.path.dirname(__file__), "..", "hermes-agent"),
)
if os.path.isdir(HERMES_AGENT_DIR) and HERMES_AGENT_DIR not in sys.path:
    sys.path.insert(0, HERMES_AGENT_DIR)

_hermes_available = False
try:
    from run_agent import AIAgent
    _hermes_available = True
except ImportError:
    AIAgent = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MCP_BASE = os.getenv("MCP_URL", "http://localhost:8000")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "8001"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))  # 50 MB
MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT", "120"))  # seconds
HEALTH_TIMEOUT = 10

# Hermes Agent config
HERMES_MODEL = os.getenv("HERMES_MODEL", "qwen/qwen3-235b-a22b")
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "https://openrouter.ai/api/v1")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
HERMES_MAX_ITERATIONS = int(os.getenv("HERMES_MAX_ITERATIONS", "20"))
MAX_CONVERSATION_MESSAGES = 20  # per-connection history limit

DOCUMENTER_SYSTEM_PROMPT = """You are DocuMentor, an intelligent document analysis assistant for universities.
You help users understand, query, and extract insights from their uploaded documents.

You have access to SurfSense tools for document management and querying.
When answering questions:
1. Use the available search/query tools to find relevant information in the knowledge base.
2. Structure your response clearly with sections if the answer is complex.
3. Reference specific documents when relevant.
4. For data extraction requests, provide structured data when possible.

Always respond in the same language the user writes in.
Be concise but thorough. If you don't find relevant information, say so honestly.
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("bridge")

# Thread pool for running sync AIAgent in async context
_agent_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hermes-agent")

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

class ErrorCode:
    INVALID_JSON = "INVALID_JSON"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN_TYPE = "UNKNOWN_TYPE"
    MCP_ERROR = "MCP_ERROR"
    MCP_UNREACHABLE = "MCP_UNREACHABLE"
    UPLOAD_TOO_LARGE = "UPLOAD_TOO_LARGE"
    UPLOAD_DECODE_FAILED = "UPLOAD_DECODE_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

# ---------------------------------------------------------------------------
# Pydantic models — inbound payloads
# ---------------------------------------------------------------------------

class QueryPayload(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    search_space_id: int = Field(..., gt=0)
    thread_id: Optional[str] = None

class UploadPayload(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    data: str = Field(..., min_length=1)  # base64
    search_space_id: int = Field(..., gt=0)

    @field_validator("filename")
    @classmethod
    def sanitize_filename(cls, v: str) -> str:
        safe = Path(v).name  # strip path traversal
        if not safe:
            raise ValueError("Invalid filename")
        return safe

class ListDocsPayload(BaseModel):
    search_space_id: int = Field(..., gt=0)

class CreateSpacePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)

class ExtractPayload(BaseModel):
    doc_id: int = Field(..., gt=0)
    search_space_id: int = Field(..., gt=0)

class DeleteDocumentPayload(BaseModel):
    document_id: int = Field(..., gt=0)
    search_space_id: Optional[int] = None

class DeleteSpacePayload(BaseModel):
    search_space_id: int = Field(..., gt=0)

class SearchDocumentsPayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    search_space_id: Optional[int] = None

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="DocuMentor Bridge", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Connected clients & conversation history
# ---------------------------------------------------------------------------

active_connections: set[WebSocket] = set()
_conversation_histories: dict[int, list[dict[str, Any]]] = {}


# ---------------------------------------------------------------------------
# Hermes AIAgent factory
# ---------------------------------------------------------------------------

def _create_agent() -> "AIAgent | None":
    """Create a fresh AIAgent configured for DocuMentor. Returns None if unavailable."""
    if not _hermes_available or AIAgent is None:
        logger.warning("Hermes AIAgent not available — queries will fall back to direct MCP")
        return None
    try:
        agent = AIAgent(
            model=HERMES_MODEL,
            base_url=HERMES_BASE_URL,
            api_key=HERMES_API_KEY,
            platform="web",
            enabled_toolsets=["mcp-surfsense"],
            skip_context_files=True,
            skip_memory=True,
            quiet_mode=True,
            max_iterations=HERMES_MAX_ITERATIONS,
            ephemeral_system_prompt=DOCUMENTER_SYSTEM_PROMPT,
        )
        logger.info("Hermes AIAgent created (model=%s, tools=%d)", HERMES_MODEL, len(agent.tools or []))
        return agent
    except Exception:
        logger.exception("Failed to create Hermes AIAgent")
        return None


# Lazy singleton agent + query lock to prevent callback interleaving
_agent_instance: "AIAgent | None" = None
_agent_init_attempted = False
_agent_query_lock: asyncio.Lock | None = None


def _get_query_lock() -> asyncio.Lock:
    global _agent_query_lock
    if _agent_query_lock is None:
        _agent_query_lock = asyncio.Lock()
    return _agent_query_lock


def _get_agent() -> "AIAgent | None":
    """Get or create the singleton AIAgent."""
    global _agent_instance, _agent_init_attempted
    if not _agent_init_attempted:
        _agent_init_attempted = True
        _agent_instance = _create_agent()
    return _agent_instance

# ---------------------------------------------------------------------------
# MCP client — single reusable httpx client
# ---------------------------------------------------------------------------

_mcp_client: httpx.AsyncClient | None = None


def get_mcp_client() -> httpx.AsyncClient:
    global _mcp_client
    if _mcp_client is None or _mcp_client.is_closed:
        _mcp_client = httpx.AsyncClient(
            timeout=httpx.Timeout(MCP_TIMEOUT, connect=10),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _mcp_client


async def mcp_call(tool: str, args: dict) -> dict:
    """Call a tool on the MCP wrapper via JSON-RPC. Raises on failure."""
    client = get_mcp_client()
    resp = await client.post(
        f"{MCP_BASE}/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        },
    )
    resp.raise_for_status()
    data = resp.json()

    if "error" in data and data["error"]:
        msg = data["error"].get("message", "MCP error")
        raise MCPError(msg)

    result = data.get("result", {})
    content_list = result.get("content", [])
    if not content_list:
        raise MCPError("Empty response from MCP tool")

    text = content_list[0].get("text", "{}")
    # Handle cases where FastMCP wraps the result differently
    if not text or text.isspace():
        raise MCPError(f"Empty text response from {tool}")

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("mcp_call %s: json.loads failed: %s", tool, e)
        return {"type": "raw", "content": text}


class MCPError(Exception):
    """Raised when the MCP wrapper returns an error."""
    pass

# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

async def send_error(ws: WebSocket, code: str, message: str, **extra: Any) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    payload.update(extra)
    try:
        await ws.send_json({"type": "error", "payload": payload})
    except Exception:
        pass  # connection already dead


async def send_status(ws: WebSocket, state: str, message: str) -> None:
    try:
        await ws.send_json({"type": "status", "payload": {"state": state, "message": message}})
    except Exception:
        pass


async def send_json(ws: WebSocket, msg: dict) -> None:
    try:
        await ws.send_json(msg)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def handle_status(ws: WebSocket, _payload: dict) -> None:
    try:
        client = get_mcp_client()
        mcp_health = await client.get(f"{MCP_BASE}/health", timeout=HEALTH_TIMEOUT)
        mcp_ok = mcp_health.status_code == 200
    except Exception:
        mcp_ok = False

    await send_json(ws, {
        "type": "status",
        "payload": {
            "state": "ready" if mcp_ok else "error",
            "mcp": mcp_ok,
            "message": "All systems operational" if mcp_ok else "MCP wrapper not responding",
        },
    })


async def handle_list_spaces(ws: WebSocket, _payload: dict) -> None:
    try:
        result = await mcp_call("surfsense_list_spaces", {})
        await send_json(ws, {"type": "spaces", "payload": result})
    except (MCPError, httpx.HTTPError) as e:
        logger.error("list_spaces failed: %s", e)
        await send_error(ws, ErrorCode.MCP_ERROR, f"Failed to list spaces: {e}")


async def handle_create_space(ws: WebSocket, payload: dict) -> None:
    data = CreateSpacePayload(**payload)
    try:
        result = await mcp_call("surfsense_create_space", {
            "name": data.name,
            "description": data.description,
        })
        await send_json(ws, {"type": "space_created", "payload": result})
    except (MCPError, httpx.HTTPError) as e:
        logger.error("create_space failed: %s", e)
        await send_error(ws, ErrorCode.MCP_ERROR, f"Failed to create space: {e}")


async def handle_list_docs(ws: WebSocket, payload: dict) -> None:
    data = ListDocsPayload(**payload)
    try:
        result = await mcp_call("surfsense_list_documents", {
            "search_space_id": data.search_space_id,
        })
        await send_json(ws, {"type": "documents", "payload": result})
    except (MCPError, httpx.HTTPError) as e:
        logger.error("list_docs failed: %s", e)
        await send_error(ws, ErrorCode.MCP_ERROR, f"Failed to list documents: {e}")


async def handle_upload(ws: WebSocket, payload: dict) -> None:
    data = UploadPayload(**payload)

    # --- Size check (base64 is ~33% overhead, so b64 len * 0.75 ≈ raw size) ---
    estimated_size = len(data.data) * 3 // 4
    if estimated_size > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        await send_error(ws, ErrorCode.UPLOAD_TOO_LARGE,
                         f"File exceeds {limit_mb}MB limit (estimated {estimated_size // (1024*1024)}MB)")
        return

    try:
        await send_status(ws, "uploading", f"Uploading {data.filename}...")

        # Decode base64
        try:
            raw_bytes = base64.b64decode(data.data, validate=True)
        except Exception:
            await send_error(ws, ErrorCode.UPLOAD_DECODE_FAILED, "Invalid base64 data")
            return

        # Free the b64 string from memory immediately
        del data.data

        suffix = Path(data.filename).suffix
        upload_dir = os.environ.get("UPLOAD_DIR", "/tmp/documenter-uploads")
        os.makedirs(upload_dir, exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix="documenter-", dir=upload_dir
        )
        tmp.write(raw_bytes)
        tmp.close()
        del raw_bytes  # free

        # Upload via MCP
        upload_result = await mcp_call("surfsense_upload", {
            "file_path": tmp.name,
            "search_space_id": data.search_space_id,
        })

        doc_ids = upload_result.get("document_ids", [])
        doc_id = doc_ids[0] if doc_ids else None

        # Poll for readiness (max 60s)
        await send_status(ws, "indexing", f"Indexing {data.filename}...")

        if doc_id:
            for attempt in range(30):
                await asyncio.sleep(2)
                try:
                    status = await mcp_call("surfsense_document_status", {
                        "search_space_id": data.search_space_id,
                        "document_ids": str(doc_id),
                    })
                    items = status.get("items", [])
                    if items and items[0].get("state") == "ready":
                        break
                    if items and items[0].get("state") == "error":
                        reason = items[0].get("reason", "Unknown indexing error")
                        await send_error(ws, ErrorCode.MCP_ERROR, f"Indexing failed: {reason}")
                        return
                except Exception:
                    # Fallback: check doc list
                    try:
                        docs = await mcp_call("surfsense_list_documents", {
                            "search_space_id": data.search_space_id,
                        })
                        doc_list = docs.get("documents", [])
                        target = next((d for d in doc_list if d["id"] == doc_id), None)
                        if target and target.get("status") == "ready":
                            break
                    except Exception:
                        pass

            # Extract structured data
            await send_status(ws, "querying", f"Analyzing {data.filename}...")
            extracted = await mcp_call("surfsense_extract_tables", {
                "doc_id": doc_id,
                "search_space_id": data.search_space_id,
            })
            dashboard = extracted.get("dashboard", {})
        else:
            dashboard = {
                "type": "generic",
                "summary": f"File {data.filename} uploaded but no structured data extracted.",
                "views": [],
            }

        # Clean up
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

        await send_json(ws, {
            "type": "result",
            "payload": {
                "action": "upload",
                "filename": data.filename,
                "doc_id": doc_id,
                "dashboard": dashboard,
            },
        })
        await send_status(ws, "ready", f"{data.filename} processed successfully")

        # Refresh doc list
        await handle_list_docs(ws, {"search_space_id": data.search_space_id})

    except (MCPError, httpx.HTTPError) as e:
        logger.exception("Upload error for %s", data.filename)
        await send_status(ws, "error", f"Upload failed: {e}")
        await send_error(ws, ErrorCode.MCP_ERROR, str(e))
    except Exception as e:
        logger.exception("Unexpected upload error for %s", data.filename)
        await send_status(ws, "error", "Upload failed unexpectedly")
        await send_error(ws, ErrorCode.INTERNAL_ERROR, "An internal error occurred during upload")


def _parse_dashboard_from_text(text: str) -> dict | None:
    """Try to extract a dashboard JSON from agent response text."""
    # Look for ```json ... ``` blocks (greedy between fences to capture nested {})
    json_match = re.search(r"```(?:json)?\s*(\{.+\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    # Try parsing the whole text as JSON
    text_stripped = text.strip()
    if text_stripped.startswith("{") and text_stripped.endswith("}"):
        try:
            parsed = json.loads(text_stripped)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return None


async def handle_query(ws: WebSocket, payload: dict) -> None:
    data = QueryPayload(**payload)
    agent = _get_agent()

    # ---------------------------------------------------------------
    # Fallback: no Hermes → direct MCP call (legacy behavior)
    # ---------------------------------------------------------------
    if agent is None:
        try:
            await send_status(ws, "querying", "Searching documents...")
            args: dict[str, Any] = {"query": data.query, "search_space_id": data.search_space_id}
            if data.thread_id:
                args["thread_id"] = data.thread_id
            result = await mcp_call("surfsense_query", args)
            await send_json(ws, {
                "type": "result",
                "payload": {
                    "action": "query",
                    "query": data.query,
                    "thread_id": result.get("thread_id"),
                    "dashboard": result.get("dashboard", {}),
                },
            })
            await send_status(ws, "ready", "Query complete")
        except (MCPError, httpx.HTTPError) as e:
            logger.error("Query error (fallback): %s", e)
            await send_status(ws, "error", f"Query failed: {e}")
            await send_error(ws, ErrorCode.MCP_ERROR, str(e))
        return

    # ---------------------------------------------------------------
    # Hermes Agent path — streaming + tool use
    # Lock ensures only one query runs at a time (singleton agent
    # has shared callback state). Concurrent queries are queued.
    # ---------------------------------------------------------------
    async with _get_query_lock():
        await _run_hermes_query(ws, agent, data)


async def _run_hermes_query(ws: WebSocket, agent: "AIAgent", data: QueryPayload) -> None:
    """Execute a query through Hermes AIAgent with streaming callbacks."""
    ws_id = id(ws)
    history = _conversation_histories.get(ws_id, [])
    loop = asyncio.get_running_loop()

    # Callback wrappers: fire from executor thread → async WebSocket send
    def on_stream_delta(delta: str | None) -> None:
        if delta is None:
            # Stream finished signal from Hermes
            asyncio.run_coroutine_threadsafe(
                send_json(ws, {"type": "stream", "payload": {"delta": "", "done": True}}),
                loop,
            )
            return
        asyncio.run_coroutine_threadsafe(
            send_json(ws, {"type": "stream", "payload": {"delta": delta, "done": False}}),
            loop,
        )

    def on_tool_progress(tool_name: str, args_preview: str = "") -> None:
        asyncio.run_coroutine_threadsafe(
            send_json(ws, {
                "type": "agent_status",
                "payload": {"tool": tool_name, "status": "running", "preview": args_preview[:100]},
            }),
            loop,
        )

    def on_status(status_msg: str) -> None:
        asyncio.run_coroutine_threadsafe(
            send_status(ws, "querying", status_msg),
            loop,
        )

    # Configure callbacks on the agent for this request
    agent.stream_delta_callback = on_stream_delta
    agent.tool_progress_callback = on_tool_progress
    agent.status_callback = on_status

    try:
        await send_status(ws, "querying", "Thinking...")

        def _run_agent() -> dict:
            return agent.run_conversation(
                user_message=data.query,
                conversation_history=list(history),  # copy to avoid mutation
            )

        result = await loop.run_in_executor(_agent_executor, _run_agent)

        final_response = result.get("final_response", "")
        updated_history = result.get("messages", [])

        # Trim and store conversation history
        if len(updated_history) > MAX_CONVERSATION_MESSAGES:
            updated_history = updated_history[-MAX_CONVERSATION_MESSAGES:]
        _conversation_histories[ws_id] = updated_history

        # Try to parse dashboard data from response
        dashboard = _parse_dashboard_from_text(final_response)
        if dashboard is None:
            dashboard = {"type": "summary", "content": final_response, "query": data.query}

        # Send final result
        await send_json(ws, {
            "type": "stream",
            "payload": {"delta": "", "done": True},
        })
        await send_json(ws, {
            "type": "result",
            "payload": {
                "action": "query",
                "query": data.query,
                "response": final_response,
                "dashboard": dashboard,
            },
        })
        await send_status(ws, "ready", "Query complete")

    except Exception as e:
        logger.exception("Hermes query error")
        await send_json(ws, {
            "type": "stream",
            "payload": {"delta": "", "done": True},
        })
        await send_status(ws, "error", f"Query failed: {e}")
        await send_error(ws, ErrorCode.INTERNAL_ERROR, f"Agent error: {e}")
    finally:
        # Clear callbacks to avoid leaking ws references
        agent.stream_delta_callback = None
        agent.tool_progress_callback = None
        agent.status_callback = None


async def handle_extract(ws: WebSocket, payload: dict) -> None:
    data = ExtractPayload(**payload)

    try:
        await send_status(ws, "querying", "Extracting data...")

        result = await mcp_call("surfsense_extract_tables", {
            "doc_id": data.doc_id,
            "search_space_id": data.search_space_id,
        })

        await send_json(ws, {
            "type": "result",
            "payload": {
                "action": "extract",
                "doc_id": data.doc_id,
                "dashboard": result.get("dashboard", {}),
            },
        })
        await send_status(ws, "ready", "Extraction complete")

    except (MCPError, httpx.HTTPError) as e:
        logger.error("Extract error: %s", e)
        await send_error(ws, ErrorCode.MCP_ERROR, str(e))


async def handle_delete_document(ws: WebSocket, payload: dict) -> None:
    data = DeleteDocumentPayload(**payload)

    try:
        result = await mcp_call("surfsense_delete_document", {
            "document_id": data.document_id,
        })
        await send_json(ws, {
            "type": "result",
            "payload": {"action": "delete_document", "document_id": data.document_id, "result": result},
        })
        if data.search_space_id:
            await handle_list_docs(ws, {"search_space_id": data.search_space_id})
    except (MCPError, httpx.HTTPError) as e:
        logger.error("Delete document error: %s", e)
        await send_error(ws, ErrorCode.MCP_ERROR, str(e))


async def handle_delete_space(ws: WebSocket, payload: dict) -> None:
    data = DeleteSpacePayload(**payload)

    try:
        result = await mcp_call("surfsense_delete_space", {
            "search_space_id": data.search_space_id,
        })
        await send_json(ws, {
            "type": "result",
            "payload": {"action": "delete_space", "search_space_id": data.search_space_id, "result": result},
        })
        await handle_list_spaces(ws, {})
    except (MCPError, httpx.HTTPError) as e:
        logger.error("Delete space error: %s", e)
        await send_error(ws, ErrorCode.MCP_ERROR, str(e))


async def handle_search_documents(ws: WebSocket, payload: dict) -> None:
    data = SearchDocumentsPayload(**payload)

    try:
        args: dict[str, Any] = {"title": data.title}
        if data.search_space_id:
            args["search_space_id"] = data.search_space_id
        result = await mcp_call("surfsense_search_documents", args)
        await send_json(ws, {"type": "documents", "payload": result})
    except (MCPError, httpx.HTTPError) as e:
        logger.error("Search documents error: %s", e)
        await send_error(ws, ErrorCode.MCP_ERROR, str(e))


async def handle_clear(ws: WebSocket, _payload: dict) -> None:
    """Clear conversation history for this connection."""
    ws_id = id(ws)
    _conversation_histories.pop(ws_id, None)
    logger.info("Cleared conversation history for connection %d", ws_id)
    await send_json(ws, {
        "type": "status",
        "payload": {"state": "ready", "message": "Conversation cleared"},
    })

# ---------------------------------------------------------------------------
# Dispatcher — explicit allowlist, no generic passthrough
# ---------------------------------------------------------------------------

HANDLERS: dict[str, Any] = {
    "status":           handle_status,
    "list_spaces":      handle_list_spaces,
    "create_space":     handle_create_space,
    "list_docs":        handle_list_docs,
    "upload":           handle_upload,
    "query":            handle_query,
    "extract":          handle_extract,
    "delete_document":  handle_delete_document,
    "delete_space":     handle_delete_space,
    "search_documents": handle_search_documents,
    "clear":            handle_clear,
}

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

MAX_WS_MESSAGE_SIZE = 75 * 1024 * 1024  # 75 MB (base64 overhead for 50MB files)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_connections.add(ws)
    logger.info("Client connected (%d total)", len(active_connections))

    try:
        while True:
            raw = await ws.receive_text()

            # Basic size guard
            if len(raw) > MAX_WS_MESSAGE_SIZE:
                await send_error(ws, ErrorCode.UPLOAD_TOO_LARGE, "Message too large")
                continue

            # Parse JSON
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_error(ws, ErrorCode.INVALID_JSON, "Invalid JSON")
                continue

            if not isinstance(msg, dict):
                await send_error(ws, ErrorCode.INVALID_JSON, "Message must be a JSON object")
                continue

            msg_type = msg.get("type", "")
            payload = msg.get("payload", {})

            if not isinstance(payload, dict):
                payload = {}

            handler = HANDLERS.get(msg_type)
            if not handler:
                await send_error(ws, ErrorCode.UNKNOWN_TYPE, f"Unknown message type: {msg_type}")
                continue

            # Validate & dispatch
            try:
                asyncio.create_task(_safe_handle(handler, ws, payload, msg_type))
            except Exception as e:
                logger.exception("Failed to create handler task for %s", msg_type)
                await send_error(ws, ErrorCode.INTERNAL_ERROR, "Internal error")

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        active_connections.discard(ws)
        _conversation_histories.pop(id(ws), None)
        logger.info("Client disconnected (%d remaining)", len(active_connections))


async def _safe_handle(handler, ws: WebSocket, payload: dict, msg_type: str) -> None:
    """Wrapper that catches validation and unexpected errors per handler."""
    try:
        await handler(ws, payload)
    except (ValueError, TypeError) as e:
        # Pydantic validation errors surface here
        logger.warning("Validation error for %s: %s", msg_type, e)
        await send_error(ws, ErrorCode.VALIDATION_ERROR, str(e))
    except httpx.ConnectError:
        logger.error("MCP unreachable for %s", msg_type)
        await send_error(ws, ErrorCode.MCP_UNREACHABLE, "MCP wrapper is not reachable")
    except httpx.TimeoutException:
        logger.error("MCP timeout for %s", msg_type)
        await send_error(ws, ErrorCode.MCP_ERROR, "Request timed out")
    except MCPError as e:
        logger.error("MCP error for %s: %s", msg_type, e)
        await send_error(ws, ErrorCode.MCP_ERROR, str(e))
    except Exception as e:
        logger.exception("Unexpected error in handler %s", msg_type)
        await send_error(ws, ErrorCode.INTERNAL_ERROR, "An internal error occurred")

# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "documenter-bridge",
        "version": "0.3.0",
        "clients": len(active_connections),
        "hermes": _hermes_available,
    }

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("shutdown")
async def shutdown():
    global _mcp_client
    if _mcp_client and not _mcp_client.is_closed:
        await _mcp_client.aclose()
    _agent_executor.shutdown(wait=False)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting DocuMentor Bridge v0.3.0 on port %s", BRIDGE_PORT)
    logger.info("MCP wrapper: %s", MCP_BASE)
    logger.info("Max upload: %d MB", MAX_UPLOAD_BYTES // (1024 * 1024))
    uvicorn.run(app, host="0.0.0.0", port=BRIDGE_PORT, log_level="info")
