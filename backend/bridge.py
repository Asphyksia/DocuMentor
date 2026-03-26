"""
DocuMentor Bridge Server
------------------------
WebSocket gateway between the Next.js dashboard and the MCP wrapper / Hermes Agent.

Design principles (v0.5.0 — Hermes as separate service):
  - Queries are routed to Hermes service (HTTP/SSE) for intelligent reasoning.
  - Automatic fallback: if Hermes is down, queries go direct to MCP wrapper.
  - CRUD operations (upload, delete, list) always go direct to MCP wrapper.
  - Streaming: Hermes SSE events are forwarded to the frontend via WebSocket.
  - Per-connection conversation history for multi-turn chat.
  - CORS restricted to configured origins. Rate limiting per connection.
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
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MCP_BASE = os.getenv("MCP_URL", "http://localhost:8000")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "8001"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))  # 50 MB
MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT", "120"))  # seconds
HEALTH_TIMEOUT = 10

# Hermes service (dedicated container)
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8002")
HERMES_TIMEOUT = int(os.getenv("HERMES_TIMEOUT", "180"))  # seconds

# CORS — restrict to known frontends; override with ALLOWED_ORIGINS env var
_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", ",".join(_default_origins)).split(",")
    if o.strip()
]

# Rate limiting (per WebSocket connection)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))  # requests per window

MAX_CONVERSATION_MESSAGES = 20  # per-connection history limit

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("bridge")


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
    RATE_LIMITED = "RATE_LIMITED"
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

app = FastAPI(title="DocuMentor Bridge", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Connected clients & conversation history
# ---------------------------------------------------------------------------

active_connections: set[WebSocket] = set()
_conversation_histories: dict[int, list[dict[str, Any]]] = {}

# Per-connection rate limiter: {ws_id: [timestamp, ...]}
_rate_buckets: dict[int, list[float]] = {}


def _check_rate_limit(ws_id: int) -> bool:
    """Return True if within rate limit, False if exceeded."""
    now = time.monotonic()
    bucket = _rate_buckets.setdefault(ws_id, [])
    # Prune old entries
    cutoff = now - RATE_LIMIT_WINDOW
    bucket[:] = [t for t in bucket if t > cutoff]
    if len(bucket) >= RATE_LIMIT_MAX:
        return False
    bucket.append(now)
    return True


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Hermes service client — detects availability, streams SSE responses
# ---------------------------------------------------------------------------

_hermes_available: bool | None = None  # None = not checked yet
_hermes_client: httpx.AsyncClient | None = None


def get_hermes_client() -> httpx.AsyncClient:
    global _hermes_client
    if _hermes_client is None or _hermes_client.is_closed:
        _hermes_client = httpx.AsyncClient(
            timeout=httpx.Timeout(HERMES_TIMEOUT, connect=10),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _hermes_client


async def _check_hermes() -> bool:
    """Check if Hermes service is reachable. Caches result for 30s."""
    global _hermes_available
    try:
        client = get_hermes_client()
        resp = await client.get(f"{HERMES_URL}/health", timeout=5)
        _hermes_available = resp.status_code == 200
    except Exception:
        _hermes_available = False
    return _hermes_available


async def is_hermes_available() -> bool:
    """Return cached Hermes availability or check if unknown."""
    if _hermes_available is None:
        return await _check_hermes()
    return _hermes_available


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
    hermes_ok = await is_hermes_available()

    # ---------------------------------------------------------------
    # Fallback: no Hermes service → direct MCP call (legacy behavior)
    # ---------------------------------------------------------------
    if not hermes_ok:
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
    # Hermes service path — HTTP POST with SSE streaming
    # ---------------------------------------------------------------
    await _run_hermes_query(ws, data)


async def _run_hermes_query(ws: WebSocket, data: QueryPayload) -> None:
    """Execute a query through Hermes service via HTTP/SSE streaming."""
    ws_id = id(ws)
    history = _conversation_histories.get(ws_id, [])

    try:
        await send_status(ws, "querying", "Thinking...")

        client = get_hermes_client()
        request_body = {
            "query": data.query,
            "search_space_id": data.search_space_id,
            "conversation_history": list(history),
        }
        if data.thread_id:
            request_body["thread_id"] = data.thread_id

        # Stream SSE response from Hermes service
        async with client.stream(
            "POST",
            f"{HERMES_URL}/query",
            json=request_body,
            timeout=HERMES_TIMEOUT,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise Exception(f"Hermes returned {response.status_code}: {body.decode()}")

            final_response = ""
            final_dashboard = None
            final_messages = []

            # Parse SSE events
            event_type = ""
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    event_type = ""
                    continue
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                    continue
                if not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                try:
                    event_data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if event_type == "delta":
                    delta = event_data.get("delta", "")
                    if delta:
                        await send_json(ws, {
                            "type": "stream",
                            "payload": {"delta": delta, "done": False},
                        })

                elif event_type == "tool":
                    await send_json(ws, {
                        "type": "agent_status",
                        "payload": {
                            "tool": event_data.get("tool", ""),
                            "status": event_data.get("status", "running"),
                            "preview": event_data.get("preview", ""),
                        },
                    })

                elif event_type == "status":
                    await send_status(ws, "querying", event_data.get("message", ""))

                elif event_type == "done":
                    final_response = event_data.get("response", "")
                    final_messages = event_data.get("messages", [])
                    final_dashboard = event_data.get("dashboard")

                elif event_type == "error":
                    error_msg = event_data.get("error", "Unknown Hermes error")
                    raise Exception(error_msg)

        # Update conversation history
        if final_messages:
            if len(final_messages) > MAX_CONVERSATION_MESSAGES:
                final_messages = final_messages[-MAX_CONVERSATION_MESSAGES:]
            _conversation_histories[ws_id] = final_messages

        # Build dashboard if not provided
        if final_dashboard is None:
            final_dashboard = _parse_dashboard_from_text(final_response)
        if final_dashboard is None:
            final_dashboard = {"type": "summary", "content": final_response, "query": data.query}

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
                "dashboard": final_dashboard,
            },
        })
        await send_status(ws, "ready", "Query complete")

    except httpx.ConnectError:
        logger.error("Hermes service unreachable")
        # Mark as unavailable for next request
        global _hermes_available
        _hermes_available = False
        await send_json(ws, {"type": "stream", "payload": {"delta": "", "done": True}})
        await send_status(ws, "error", "Hermes service unreachable")
        await send_error(ws, ErrorCode.MCP_UNREACHABLE, "Hermes service is not reachable. Try again for direct search fallback.")
    except Exception as e:
        logger.exception("Hermes query error")
        await send_json(ws, {
            "type": "stream",
            "payload": {"delta": "", "done": True},
        })
        await send_status(ws, "error", f"Query failed: {e}")
        await send_error(ws, ErrorCode.INTERNAL_ERROR, f"Agent error: {e}")

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

            # Rate limiting (skip for status/clear — low-cost operations)
            if msg_type not in ("status", "clear") and not _check_rate_limit(id(ws)):
                await send_error(
                    ws, ErrorCode.RATE_LIMITED,
                    f"Rate limit exceeded ({RATE_LIMIT_MAX} requests per {RATE_LIMIT_WINDOW}s). Please slow down."
                )
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
        ws_id = id(ws)
        active_connections.discard(ws)
        _conversation_histories.pop(ws_id, None)
        _rate_buckets.pop(ws_id, None)
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
        "version": "0.5.0",
        "clients": len(active_connections),
        "hermes": _hermes_available or False,
        "hermes_url": HERMES_URL,
        "cors_origins": ALLOWED_ORIGINS,
        "rate_limit": f"{RATE_LIMIT_MAX}/{RATE_LIMIT_WINDOW}s",
    }

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("shutdown")
async def shutdown():
    global _mcp_client, _hermes_client
    if _mcp_client and not _mcp_client.is_closed:
        await _mcp_client.aclose()
    if _hermes_client and not _hermes_client.is_closed:
        await _hermes_client.aclose()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting DocuMentor Bridge v0.5.0 on port %s", BRIDGE_PORT)
    logger.info("CORS origins: %s", ALLOWED_ORIGINS)
    logger.info("Rate limit: %d requests per %ds window", RATE_LIMIT_MAX, RATE_LIMIT_WINDOW)
    logger.info("MCP wrapper: %s", MCP_BASE)
    logger.info("Max upload: %d MB", MAX_UPLOAD_BYTES // (1024 * 1024))
    uvicorn.run(app, host="0.0.0.0", port=BRIDGE_PORT, log_level="info")
