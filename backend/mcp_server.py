"""
DocuMentor MCP Server — v1.0.0
-------------------------------
Dual-protocol MCP server:
  - /mcp       — Streamable HTTP (real MCP protocol) for Hermes Agent
  - /jsonrpc   — JSON-RPC for bridge backward compatibility
  - /health    — Health check
  - /tools     — Debug tool listing

Architecture:
  FastMCP handles the MCP protocol at /mcp (Streamable HTTP/SSE).
  A Starlette custom route at /jsonrpc translates JSON-RPC calls into
  the same tool functions, for the bridge which speaks JSON-RPC.
  Both share the same tool implementations and SurfSense auth.

Requires: mcp[cli], httpx, uvicorn
"""

from __future__ import annotations

import contextlib
import json
import logging
import mimetypes
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SURFSENSE_BASE = os.getenv("SURFSENSE_BASE_URL", "http://backend:8000")
SURFSENSE_EMAIL = os.getenv("SURFSENSE_EMAIL", "admin@documenter.app")
SURFSENSE_PASSWORD = os.getenv("SURFSENSE_PASSWORD", "admin")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
TOKEN_TTL = int(os.getenv("TOKEN_TTL", "3300"))
REQUEST_TIMEOUT = int(os.getenv("MCP_REQUEST_TIMEOUT", "120"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("mcp")

# ---------------------------------------------------------------------------
# FastMCP instance (handles Streamable HTTP at /mcp)
# ---------------------------------------------------------------------------

mcp = FastMCP("DocuMentor", stateless_http=True, json_response=True)

# ---------------------------------------------------------------------------
# Reusable HTTP client + Auth
# ---------------------------------------------------------------------------

_http: httpx.AsyncClient | None = None
_token: str | None = None
_token_expires: float = 0


def http() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=10),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _http


async def authenticate() -> str:
    global _token, _token_expires
    resp = await http().post(
        f"{SURFSENSE_BASE}/auth/jwt/login",
        data={"username": SURFSENSE_EMAIL, "password": SURFSENSE_PASSWORD},
    )
    if resp.status_code != 200:
        _token = None
        raise RuntimeError(f"SurfSense auth failed: {resp.status_code} {resp.text[:200]}")
    _token = resp.json()["access_token"]
    _token_expires = time.time() + TOKEN_TTL
    logger.info("Authenticated with SurfSense (TTL %ds)", TOKEN_TTL)
    return _token


async def get_token() -> str:
    if _token and time.time() < _token_expires:
        return _token
    return await authenticate()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def authed_request(method: str, path: str, *, params: dict | None = None,
                         json_body: Any = None, data: dict | None = None,
                         files: Any = None, timeout: float | None = None) -> httpx.Response:
    token = await get_token()
    url = f"{SURFSENSE_BASE}{path}"
    kwargs: dict[str, Any] = {"headers": auth_headers(token)}
    if params: kwargs["params"] = params
    if json_body is not None: kwargs["json"] = json_body
    if data is not None: kwargs["data"] = data
    if files is not None: kwargs["files"] = files
    if timeout is not None: kwargs["timeout"] = timeout
    resp = await getattr(http(), method.lower())(url, **kwargs)
    if resp.status_code == 401:
        logger.warning("Got 401, re-authenticating...")
        token = await authenticate()
        kwargs["headers"] = auth_headers(token)
        resp = await getattr(http(), method.lower())(url, **kwargs)
    resp.raise_for_status()
    return resp

# ===========================================================================
# TOOL IMPLEMENTATIONS (shared by FastMCP and JSON-RPC)
# ===========================================================================

async def _tool_upload(file_path: str, search_space_id: int) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "application/octet-stream"
    token = await get_token()
    with open(path, "rb") as f:
        files = {"files": (path.name, f, mime_type)}
        form_data = {"search_space_id": str(search_space_id), "should_summarize": "true"}
        resp = await http().post(f"{SURFSENSE_BASE}/api/v1/documents/fileupload",
                                 headers=auth_headers(token), files=files, data=form_data, timeout=120)
    resp.raise_for_status()
    result = resp.json()
    logger.info("Uploaded %s -> doc_ids=%s", path.name, result.get("document_ids"))
    return {"type": "upload_result", "file": path.name,
            "document_ids": result.get("document_ids", []), "status": "queued",
            "message": result.get("message", "File queued for processing")}


async def _tool_list_documents(search_space_id: int, page: int = 0, page_size: int = 50) -> dict:
    resp = await authed_request("GET", "/api/v1/documents",
                                params={"search_space_id": search_space_id, "page": page, "page_size": page_size})
    data = resp.json()
    docs = data.get("items", data) if isinstance(data, dict) else data
    return {"type": "document_list", "search_space_id": search_space_id,
            "total": data.get("total", len(docs)) if isinstance(data, dict) else len(docs),
            "documents": [{"id": d["id"], "title": d["title"],
                           "type": d.get("document_type", "unknown"),
                           "status": d.get("status", {}).get("state", "ready") if isinstance(d.get("status"), dict) else "ready",
                           "created_at": d.get("created_at")} for d in (docs if isinstance(docs, list) else [])]}


async def _tool_get_document(document_id: int) -> dict:
    resp = await authed_request("GET", f"/api/v1/documents/{document_id}")
    doc = resp.json()
    return {"type": "document_detail", "id": doc["id"], "title": doc.get("title"),
            "document_type": doc.get("document_type"), "content": doc.get("content"),
            "document_metadata": doc.get("document_metadata"), "search_space_id": doc.get("search_space_id"),
            "created_at": doc.get("created_at"), "updated_at": doc.get("updated_at")}


async def _tool_delete_document(document_id: int) -> dict:
    await authed_request("DELETE", f"/api/v1/documents/{document_id}")
    return {"type": "document_deleted", "id": document_id, "status": "deleted"}


async def _tool_update_document(document_id: int, title: str | None = None, document_metadata: dict | None = None) -> dict:
    body: dict[str, Any] = {}
    if title is not None: body["title"] = title
    if document_metadata is not None: body["document_metadata"] = document_metadata
    if not body: raise ValueError("Nothing to update")
    resp = await authed_request("PUT", f"/api/v1/documents/{document_id}", json_body=body)
    doc = resp.json()
    return {"type": "document_updated", "id": doc["id"], "title": doc.get("title"), "updated_at": doc.get("updated_at")}


async def _tool_document_status(search_space_id: int, document_ids: str) -> dict:
    resp = await authed_request("GET", "/api/v1/documents/status",
                                params={"search_space_id": search_space_id, "document_ids": document_ids})
    data = resp.json()
    items = data.get("items", data) if isinstance(data, dict) else data
    return {"type": "document_status", "items": [
        {"id": item.get("id"), "title": item.get("title"),
         "state": item.get("status", {}).get("state", "unknown") if isinstance(item.get("status"), dict) else "unknown",
         "reason": item.get("status", {}).get("reason") if isinstance(item.get("status"), dict) else None}
        for item in (items if isinstance(items, list) else [])]}


async def _tool_search_documents(title: str, search_space_id: int | None = None, page_size: int = 50) -> dict:
    params: dict[str, Any] = {"title": title, "page_size": page_size}
    if search_space_id is not None: params["search_space_id"] = search_space_id
    resp = await authed_request("GET", "/api/v1/documents/search", params=params)
    data = resp.json()
    docs = data.get("items", data) if isinstance(data, dict) else data
    return {"type": "document_search", "query": title,
            "total": data.get("total", len(docs)) if isinstance(data, dict) else len(docs),
            "documents": [{"id": d["id"], "title": d["title"], "type": d.get("document_type")}
                          for d in (docs if isinstance(docs, list) else [])]}


async def _tool_type_counts(search_space_id: int | None = None) -> dict:
    params: dict[str, Any] = {}
    if search_space_id is not None: params["search_space_id"] = search_space_id
    resp = await authed_request("GET", "/api/v1/documents/type-counts", params=params)
    return {"type": "type_counts", "counts": resp.json()}


async def _tool_extract_tables(doc_id: int, search_space_id: int) -> dict:
    query = ("Extract all tables, numeric data, metrics, and statistics from this document. "
             "Return as structured JSON with: summary, tables (array of {title, headers, rows}), "
             "metrics (array of {label, value, unit}), and charts_data (array of {title, type, data}).")
    result = await _tool_query(query=query, search_space_id=search_space_id)
    result["type"] = "extract_tables_result"
    result["doc_id"] = doc_id
    return result


async def _tool_list_spaces() -> dict:
    resp = await authed_request("GET", "/api/v1/searchspaces")
    spaces = resp.json()
    return {"type": "search_spaces", "spaces": [
        {"id": s["id"], "name": s["name"], "description": s.get("description")}
        for s in (spaces if isinstance(spaces, list) else [])]}


async def _tool_create_space(name: str, description: str = "") -> dict:
    resp = await authed_request("POST", "/api/v1/searchspaces", json_body={"name": name, "description": description})
    space = resp.json()
    return {"type": "search_space_created", "id": space["id"], "name": space["name"]}


async def _tool_get_space(search_space_id: int) -> dict:
    resp = await authed_request("GET", f"/api/v1/searchspaces/{search_space_id}")
    s = resp.json()
    return {"type": "search_space_detail", "id": s["id"], "name": s.get("name"),
            "description": s.get("description"), "created_at": s.get("created_at")}


async def _tool_update_space(search_space_id: int, name: str | None = None, description: str | None = None) -> dict:
    body: dict[str, Any] = {}
    if name is not None: body["name"] = name
    if description is not None: body["description"] = description
    if not body: raise ValueError("Nothing to update")
    resp = await authed_request("PUT", f"/api/v1/searchspaces/{search_space_id}", json_body=body)
    s = resp.json()
    return {"type": "search_space_updated", "id": s["id"], "name": s.get("name")}


async def _tool_delete_space(search_space_id: int) -> dict:
    await authed_request("DELETE", f"/api/v1/searchspaces/{search_space_id}")
    return {"type": "search_space_deleted", "id": search_space_id, "status": "deleted"}


async def _tool_query(query: str, search_space_id: int, thread_id: str | None = None) -> dict:
    token = await get_token()
    headers = auth_headers(token)
    client = http()
    if not thread_id:
        resp = await client.post(f"{SURFSENSE_BASE}/api/v1/threads", headers=headers,
                                 json={"search_space_id": search_space_id, "title": query[:80]})
        resp.raise_for_status()
        thread_id = str(resp.json()["id"])
    full_response = ""
    async with client.stream("POST", f"{SURFSENSE_BASE}/api/v1/new_chat", headers=headers,
                             json={"chat_id": int(thread_id), "user_query": query,
                                   "search_space_id": search_space_id}, timeout=120) as stream:
        async for line in stream.aiter_lines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    try:
                        event = json.loads(chunk)
                        if event.get("type") == "text-delta":
                            full_response += event.get("textDelta", "")
                        elif isinstance(event, dict) and "content" in event:
                            full_response += str(event["content"])
                    except json.JSONDecodeError:
                        full_response += chunk
    dashboard_data = _parse_dashboard_json(full_response, query)
    logger.info("Query completed (thread=%s, response_len=%d)", thread_id, len(full_response))
    return {"type": "query_result", "thread_id": thread_id, "search_space_id": search_space_id,
            "query": query, "dashboard": dashboard_data}


def _parse_dashboard_json(text: str, query: str) -> dict:
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try: return json.loads(json_match.group(1))
        except json.JSONDecodeError: pass
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict): return parsed
    except (json.JSONDecodeError, ValueError): pass
    return {"type": "summary", "content": text, "query": query}


async def _tool_list_threads(search_space_id: int | None = None) -> dict:
    params: dict[str, Any] = {}
    if search_space_id is not None: params["search_space_id"] = search_space_id
    resp = await authed_request("GET", "/api/v1/threads", params=params)
    data = resp.json()
    threads = data if isinstance(data, list) else data.get("items", [])
    return {"type": "thread_list", "threads": [
        {"id": t["id"], "title": t.get("title"), "search_space_id": t.get("search_space_id"),
         "created_at": t.get("created_at")} for t in threads]}


async def _tool_get_thread(thread_id: int) -> dict:
    resp = await authed_request("GET", f"/api/v1/threads/{thread_id}")
    t = resp.json()
    return {"type": "thread_detail", "id": t["id"], "title": t.get("title"),
            "search_space_id": t.get("search_space_id"),
            "created_at": t.get("created_at"), "updated_at": t.get("updated_at")}


async def _tool_delete_thread(thread_id: int) -> dict:
    await authed_request("DELETE", f"/api/v1/threads/{thread_id}")
    return {"type": "thread_deleted", "id": thread_id, "status": "deleted"}


async def _tool_thread_history(thread_id: int) -> dict:
    resp = await authed_request("GET", f"/api/v1/threads/{thread_id}/messages")
    data = resp.json()
    messages = data if isinstance(data, list) else data.get("items", [])
    return {"type": "thread_history", "thread_id": thread_id, "messages": [
        {"id": m.get("id"), "role": m.get("role"), "content": m.get("content", "")[:500],
         "created_at": m.get("created_at")} for m in messages]}


async def _tool_list_reports(search_space_id: int | None = None) -> dict:
    params: dict[str, Any] = {}
    if search_space_id is not None: params["search_space_id"] = search_space_id
    resp = await authed_request("GET", "/api/v1/reports", params=params)
    data = resp.json()
    reports = data if isinstance(data, list) else data.get("items", [])
    return {"type": "report_list", "reports": [
        {"id": r["id"], "title": r.get("title"), "created_at": r.get("created_at")} for r in reports]}


async def _tool_get_report(report_id: int) -> dict:
    resp = await authed_request("GET", f"/api/v1/reports/{report_id}/content")
    data = resp.json()
    return {"type": "report_content", "id": report_id, "content": data.get("content", data)}


async def _tool_export_report(report_id: int) -> dict:
    resp = await authed_request("GET", f"/api/v1/reports/{report_id}/export")
    ct = resp.headers.get("content-type", "")
    if "json" in ct: return {"type": "report_export", "id": report_id, "data": resp.json()}
    return {"type": "report_export", "id": report_id, "content_type": ct,
            "size_bytes": len(resp.content), "message": "Binary content available via direct download."}


async def _tool_delete_report(report_id: int) -> dict:
    await authed_request("DELETE", f"/api/v1/reports/{report_id}")
    return {"type": "report_deleted", "id": report_id, "status": "deleted"}


async def _tool_create_note(search_space_id: int, content: str) -> dict:
    resp = await authed_request("POST", f"/api/v1/search-spaces/{search_space_id}/notes",
                                json_body={"content": content})
    data = resp.json()
    return {"type": "note_created", "id": data.get("id"), "search_space_id": search_space_id}


async def _tool_get_logs(search_space_id: int | None = None, limit: int = 50) -> dict:
    params: dict[str, Any] = {"page_size": limit}
    if search_space_id is not None: params["search_space_id"] = search_space_id
    resp = await authed_request("GET", "/api/v1/logs", params=params)
    data = resp.json()
    logs = data if isinstance(data, list) else data.get("items", [])
    return {"type": "audit_logs", "logs": [
        {"id": e.get("id"), "action": e.get("action"), "details": e.get("details"),
         "created_at": e.get("created_at")} for e in logs[:limit]]}

# ===========================================================================
# FASTMCP TOOL REGISTRATION (Hermes connects via Streamable HTTP at /mcp)
# Each @mcp.tool() wraps the shared _tool_* function and returns str (JSON).
# ===========================================================================

@mcp.tool()
async def surfsense_upload(file_path: str, search_space_id: int) -> str:
    """Upload a document (PDF, Excel, Word, CSV, etc.) to SurfSense for indexing."""
    return json.dumps(await _tool_upload(file_path, search_space_id))

@mcp.tool()
async def surfsense_list_documents(search_space_id: int, page: int = 0, page_size: int = 50) -> str:
    """List all indexed documents in a search space."""
    return json.dumps(await _tool_list_documents(search_space_id, page, page_size))

@mcp.tool()
async def surfsense_get_document(document_id: int) -> str:
    """Get full detail of a specific document."""
    return json.dumps(await _tool_get_document(document_id))

@mcp.tool()
async def surfsense_delete_document(document_id: int) -> str:
    """Permanently delete a document."""
    return json.dumps(await _tool_delete_document(document_id))

@mcp.tool()
async def surfsense_update_document(document_id: int, title: str | None = None, document_metadata: dict | None = None) -> str:
    """Update a document's title or metadata."""
    return json.dumps(await _tool_update_document(document_id, title, document_metadata))

@mcp.tool()
async def surfsense_document_status(search_space_id: int, document_ids: str) -> str:
    """Batch status check for documents (comma-separated IDs)."""
    return json.dumps(await _tool_document_status(search_space_id, document_ids))

@mcp.tool()
async def surfsense_search_documents(title: str, search_space_id: int | None = None, page_size: int = 50) -> str:
    """Search documents by title substring."""
    return json.dumps(await _tool_search_documents(title, search_space_id, page_size))

@mcp.tool()
async def surfsense_type_counts(search_space_id: int | None = None) -> str:
    """Get document counts grouped by type."""
    return json.dumps(await _tool_type_counts(search_space_id))

@mcp.tool()
async def surfsense_extract_tables(doc_id: int, search_space_id: int) -> str:
    """Extract structured data from a document for dashboard rendering."""
    return json.dumps(await _tool_extract_tables(doc_id, search_space_id))

@mcp.tool()
async def surfsense_list_spaces() -> str:
    """List all search spaces (knowledge bases)."""
    return json.dumps(await _tool_list_spaces())

@mcp.tool()
async def surfsense_create_space(name: str, description: str = "") -> str:
    """Create a new search space."""
    return json.dumps(await _tool_create_space(name, description))

@mcp.tool()
async def surfsense_get_space(search_space_id: int) -> str:
    """Get detail of a specific search space."""
    return json.dumps(await _tool_get_space(search_space_id))

@mcp.tool()
async def surfsense_update_space(search_space_id: int, name: str | None = None, description: str | None = None) -> str:
    """Update a search space's name or description."""
    return json.dumps(await _tool_update_space(search_space_id, name, description))

@mcp.tool()
async def surfsense_delete_space(search_space_id: int) -> str:
    """Delete a search space and ALL its documents. Irreversible."""
    return json.dumps(await _tool_delete_space(search_space_id))

@mcp.tool()
async def surfsense_query(query: str, search_space_id: int, thread_id: str | None = None) -> str:
    """Query the knowledge base with natural language. Returns structured JSON for dashboards."""
    return json.dumps(await _tool_query(query, search_space_id, thread_id))

@mcp.tool()
async def surfsense_list_threads(search_space_id: int | None = None) -> str:
    """List conversation threads."""
    return json.dumps(await _tool_list_threads(search_space_id))

@mcp.tool()
async def surfsense_get_thread(thread_id: int) -> str:
    """Get detail of a conversation thread."""
    return json.dumps(await _tool_get_thread(thread_id))

@mcp.tool()
async def surfsense_delete_thread(thread_id: int) -> str:
    """Delete a conversation thread."""
    return json.dumps(await _tool_delete_thread(thread_id))

@mcp.tool()
async def surfsense_thread_history(thread_id: int) -> str:
    """Get all messages in a conversation thread."""
    return json.dumps(await _tool_thread_history(thread_id))

@mcp.tool()
async def surfsense_list_reports(search_space_id: int | None = None) -> str:
    """List generated reports."""
    return json.dumps(await _tool_list_reports(search_space_id))

@mcp.tool()
async def surfsense_get_report(report_id: int) -> str:
    """Get report content."""
    return json.dumps(await _tool_get_report(report_id))

@mcp.tool()
async def surfsense_export_report(report_id: int) -> str:
    """Export a report for download."""
    return json.dumps(await _tool_export_report(report_id))

@mcp.tool()
async def surfsense_delete_report(report_id: int) -> str:
    """Delete a report."""
    return json.dumps(await _tool_delete_report(report_id))

@mcp.tool()
async def surfsense_create_note(search_space_id: int, content: str) -> str:
    """Create a note in a search space."""
    return json.dumps(await _tool_create_note(search_space_id, content))

@mcp.tool()
async def surfsense_get_logs(search_space_id: int | None = None, limit: int = 50) -> str:
    """Get audit logs."""
    return json.dumps(await _tool_get_logs(search_space_id, limit))

# ===========================================================================
# JSON-RPC DISPATCHER (bridge calls /jsonrpc)
# ===========================================================================

_TOOL_MAP = {
    "surfsense_upload": lambda a: _tool_upload(file_path=a["file_path"], search_space_id=a["search_space_id"]),
    "surfsense_list_documents": lambda a: _tool_list_documents(search_space_id=a["search_space_id"], page=a.get("page", 0), page_size=a.get("page_size", 50)),
    "surfsense_get_document": lambda a: _tool_get_document(document_id=a["document_id"]),
    "surfsense_delete_document": lambda a: _tool_delete_document(document_id=a["document_id"]),
    "surfsense_update_document": lambda a: _tool_update_document(document_id=a["document_id"], title=a.get("title"), document_metadata=a.get("document_metadata")),
    "surfsense_document_status": lambda a: _tool_document_status(search_space_id=a["search_space_id"], document_ids=a["document_ids"]),
    "surfsense_search_documents": lambda a: _tool_search_documents(title=a["title"], search_space_id=a.get("search_space_id"), page_size=a.get("page_size", 50)),
    "surfsense_type_counts": lambda a: _tool_type_counts(search_space_id=a.get("search_space_id")),
    "surfsense_extract_tables": lambda a: _tool_extract_tables(doc_id=a["doc_id"], search_space_id=a["search_space_id"]),
    "surfsense_list_spaces": lambda a: _tool_list_spaces(),
    "surfsense_create_space": lambda a: _tool_create_space(name=a["name"], description=a.get("description", "")),
    "surfsense_get_space": lambda a: _tool_get_space(search_space_id=a["search_space_id"]),
    "surfsense_update_space": lambda a: _tool_update_space(search_space_id=a["search_space_id"], name=a.get("name"), description=a.get("description")),
    "surfsense_delete_space": lambda a: _tool_delete_space(search_space_id=a["search_space_id"]),
    "surfsense_query": lambda a: _tool_query(query=a["query"], search_space_id=a["search_space_id"], thread_id=a.get("thread_id")),
    "surfsense_list_threads": lambda a: _tool_list_threads(search_space_id=a.get("search_space_id")),
    "surfsense_get_thread": lambda a: _tool_get_thread(thread_id=a["thread_id"]),
    "surfsense_delete_thread": lambda a: _tool_delete_thread(thread_id=a["thread_id"]),
    "surfsense_thread_history": lambda a: _tool_thread_history(thread_id=a["thread_id"]),
    "surfsense_list_reports": lambda a: _tool_list_reports(search_space_id=a.get("search_space_id")),
    "surfsense_get_report": lambda a: _tool_get_report(report_id=a["report_id"]),
    "surfsense_export_report": lambda a: _tool_export_report(report_id=a["report_id"]),
    "surfsense_delete_report": lambda a: _tool_delete_report(report_id=a["report_id"]),
    "surfsense_create_note": lambda a: _tool_create_note(search_space_id=a["search_space_id"], content=a["content"]),
    "surfsense_get_logs": lambda a: _tool_get_logs(search_space_id=a.get("search_space_id"), limit=a.get("limit", 50)),
}

# Tool definitions for JSON-RPC tools/list (lazy — populated on first request)
_tool_definitions_cache: list | None = None

def _get_tool_definitions() -> list:
    global _tool_definitions_cache
    if _tool_definitions_cache is None:
        _tool_definitions_cache = [
            {"name": name, "description": name.replace("_", " ").replace("surfsense ", ""),
             "inputSchema": {"type": "object", "properties": {}, "required": []}}
            for name in _TOOL_MAP
        ]
    return _tool_definitions_cache


async def jsonrpc_handler(request: Request) -> JSONResponse:
    """JSON-RPC endpoint for the bridge."""
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    try:
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "documenter-mcp", "version": "1.0.0"}}
        elif method == "tools/list":
            result = {"tools": _get_tool_definitions()}
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            handler = _TOOL_MAP.get(tool_name)
            if not handler:
                return JSONResponse(content={"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}})
            logger.info("JSON-RPC call: %s(%s)", tool_name, list(tool_args.keys()))
            t0 = time.time()
            data = await handler(tool_args)
            logger.info("Tool %s completed in %.1fs", tool_name, time.time() - t0)
            result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]}
        elif method == "notifications/initialized":
            return JSONResponse(content=None, status_code=204)
        else:
            return JSONResponse(content={"jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}})

        return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "result": result})

    except KeyError as e:
        logger.error("Missing argument: %s", e)
        return JSONResponse(content={"jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32602, "message": f"Missing required argument: {e}"}}, status_code=200)
    except Exception as e:
        logger.exception("JSON-RPC error")
        return JSONResponse(content={"jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32603, "message": str(e)}}, status_code=200)


async def health_handler(request: Request) -> JSONResponse:
    return JSONResponse(content={"status": "ok", "service": "documenter-mcp", "version": "1.0.0",
                                 "tools": len(_TOOL_MAP), "protocols": ["mcp-streamable-http", "jsonrpc"]})


# ===========================================================================
# STARLETTE APP — mounts FastMCP + custom routes
# ===========================================================================

@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield
    # Cleanup HTTP client
    global _http
    if _http and not _http.is_closed:
        await _http.aclose()


app = Starlette(
    routes=[
        # Specific routes FIRST (before the catch-all mount)
        Route("/jsonrpc", jsonrpc_handler, methods=["POST"]),  # for bridge
        Route("/health", health_handler, methods=["GET"]),
        # FastMCP catch-all LAST — serves /mcp (Streamable HTTP for Hermes)
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    logger.info("Starting DocuMentor MCP Server v1.0.0 on port %s", MCP_PORT)
    logger.info("SurfSense backend: %s", SURFSENSE_BASE)
    logger.info("Streamable HTTP (Hermes): /mcp")
    logger.info("JSON-RPC (bridge): /jsonrpc")
    logger.info("Health: /health")
    logger.info("Registered %d tools", len(_TOOL_MAP))
    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT, log_level="info")
