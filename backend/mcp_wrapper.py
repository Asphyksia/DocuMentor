"""
UniDash MCP Wrapper
-------------------
Exposes SurfSense as MCP tools for Hermes Agent.
Runs as an HTTP server on localhost:8000/mcp

Tools:
  - surfsense_upload(file_path, search_space_id)
  - surfsense_query(query, search_space_id, thread_id?)
  - surfsense_extract_tables(doc_id, search_space_id)
  - surfsense_list_documents(search_space_id)
  - surfsense_list_spaces()
  - surfsense_create_space(name, description?)

Usage:
  pip install fastapi uvicorn httpx python-multipart
  python backend/mcp_wrapper.py

Hermes config (~/.hermes/config.yaml):
  mcp_servers:
    unidash:
      url: "http://localhost:8000/mcp"
"""

import asyncio
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SURFSENSE_BASE = os.getenv("SURFSENSE_BASE_URL", "http://localhost:8929")
SURFSENSE_EMAIL = os.getenv("SURFSENSE_EMAIL", "admin@unidash.local")
SURFSENSE_PASSWORD = os.getenv("SURFSENSE_PASSWORD", "admin")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("unidash-mcp")

app = FastAPI(title="UniDash MCP Wrapper", version="0.1.0")

# ---------------------------------------------------------------------------
# SurfSense auth (JWT token cache)
# ---------------------------------------------------------------------------

_token_cache: dict[str, str] = {}


async def get_token(client: httpx.AsyncClient) -> str:
    """Authenticate with SurfSense and cache the JWT token."""
    if "token" in _token_cache:
        return _token_cache["token"]

    resp = await client.post(
        f"{SURFSENSE_BASE}/auth/jwt/login",
        data={"username": SURFSENSE_EMAIL, "password": SURFSENSE_PASSWORD},
    )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"SurfSense auth failed: {resp.status_code} {resp.text}",
        )
    token = resp.json()["access_token"]
    _token_cache["token"] = token
    return token


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def tool_list_spaces() -> dict:
    """List all available search spaces."""
    async with httpx.AsyncClient(timeout=30) as client:
        token = await get_token(client)
        resp = await client.get(
            f"{SURFSENSE_BASE}/api/v1/search-spaces",
            headers=auth_headers(token),
        )
        resp.raise_for_status()
        spaces = resp.json()
        return {
            "type": "search_spaces",
            "spaces": [
                {"id": s["id"], "name": s["name"], "description": s.get("description")}
                for s in spaces
            ],
        }


async def tool_create_space(name: str, description: str = "") -> dict:
    """Create a new search space."""
    async with httpx.AsyncClient(timeout=30) as client:
        token = await get_token(client)
        resp = await client.post(
            f"{SURFSENSE_BASE}/api/v1/search-spaces",
            headers=auth_headers(token),
            json={"name": name, "description": description},
        )
        resp.raise_for_status()
        space = resp.json()
        return {
            "type": "search_space_created",
            "id": space["id"],
            "name": space["name"],
        }


async def tool_upload(file_path: str, search_space_id: int) -> dict:
    """Upload a document to SurfSense for indexing."""
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {file_path}")

    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "application/octet-stream"

    async with httpx.AsyncClient(timeout=120) as client:
        token = await get_token(client)
        with open(path, "rb") as f:
            files = {"files": (path.name, f, mime_type)}
            data = {"search_space_id": str(search_space_id), "should_summarize": "true"}
            resp = await client.post(
                f"{SURFSENSE_BASE}/api/v1/documents/fileupload",
                headers=auth_headers(token),
                files=files,
                data=data,
            )
        resp.raise_for_status()
        result = resp.json()
        return {
            "type": "upload_result",
            "file": path.name,
            "document_ids": result.get("document_ids", []),
            "status": "queued",
            "message": result.get("message", "File queued for processing"),
        }


async def tool_list_documents(search_space_id: int) -> dict:
    """List documents in a search space."""
    async with httpx.AsyncClient(timeout=30) as client:
        token = await get_token(client)
        resp = await client.get(
            f"{SURFSENSE_BASE}/api/v1/documents",
            headers=auth_headers(token),
            params={"search_space_id": search_space_id, "page_size": 50},
        )
        resp.raise_for_status()
        data = resp.json()
        docs = data.get("items", data) if isinstance(data, dict) else data
        return {
            "type": "document_list",
            "search_space_id": search_space_id,
            "total": data.get("total", len(docs)) if isinstance(data, dict) else len(docs),
            "documents": [
                {
                    "id": d["id"],
                    "title": d["title"],
                    "type": d["document_type"],
                    "status": d.get("status", {}).get("state", "ready") if d.get("status") else "ready",
                    "created_at": d.get("created_at"),
                }
                for d in docs
            ],
        }


async def tool_query(
    query: str,
    search_space_id: int,
    thread_id: str | None = None,
) -> dict:
    """
    Query the knowledge base and return structured data for dashboard rendering.
    Creates a new thread if thread_id is not provided.
    """
    async with httpx.AsyncClient(timeout=120) as client:
        token = await get_token(client)
        headers = auth_headers(token)

        # Create thread if needed
        if not thread_id:
            resp = await client.post(
                f"{SURFSENSE_BASE}/api/v1/threads",
                headers=headers,
                json={"search_space_id": search_space_id, "title": query[:80]},
            )
            resp.raise_for_status()
            thread_id = resp.json()["id"]

        # Send message and collect streamed response
        full_response = ""
        async with client.stream(
            "POST",
            f"{SURFSENSE_BASE}/api/v1/threads/{thread_id}/messages",
            headers=headers,
            json={
                "search_space_id": search_space_id,
                "message": query,
                "stream": True,
            },
            timeout=120,
        ) as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data:"):
                    chunk = line[5:].strip()
                    if chunk and chunk != "[DONE]":
                        try:
                            event = json.loads(chunk)
                            # Extract text delta
                            if event.get("type") == "text-delta":
                                full_response += event.get("textDelta", "")
                            elif isinstance(event, dict) and "content" in event:
                                full_response += str(event["content"])
                        except json.JSONDecodeError:
                            full_response += chunk

        # Try to parse as JSON (structured dashboard output)
        dashboard_data = None
        try:
            # Look for JSON block in response
            import re
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", full_response, re.DOTALL)
            if json_match:
                dashboard_data = json.loads(json_match.group(1))
            else:
                dashboard_data = json.loads(full_response)
        except (json.JSONDecodeError, AttributeError):
            # Plain text response — wrap as summary
            dashboard_data = {
                "type": "summary",
                "content": full_response,
                "query": query,
            }

        return {
            "type": "query_result",
            "thread_id": thread_id,
            "search_space_id": search_space_id,
            "query": query,
            "dashboard": dashboard_data,
        }


async def tool_extract_tables(doc_id: int, search_space_id: int) -> dict:
    """
    Extract structured tables and metrics from a specific document.
    Uses targeted query to get tabular data for dashboard rendering.
    """
    query = (
        "Extract all tables, numeric data, metrics, and statistics from this document. "
        "Return as structured JSON with: summary, tables (array of {title, headers, rows}), "
        "metrics (array of {label, value, unit}), and charts_data (array of {title, type, data})."
    )
    result = await tool_query(
        query=query,
        search_space_id=search_space_id,
    )
    result["type"] = "extract_tables_result"
    result["doc_id"] = doc_id
    return result


# ---------------------------------------------------------------------------
# MCP HTTP endpoint (StreamableHTTP transport)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "surfsense_list_spaces",
        "description": "List all available search spaces (knowledge bases) in SurfSense.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "surfsense_create_space",
        "description": "Create a new search space (knowledge base) for a set of documents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name for the search space"},
                "description": {"type": "string", "description": "Optional description"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "surfsense_upload",
        "description": (
            "Upload a document (PDF, Excel, Word, CSV, etc.) to SurfSense for indexing. "
            "Returns document_ids and queued status. Use surfsense_list_documents to check when ready."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the file"},
                "search_space_id": {"type": "integer", "description": "Target search space ID"},
            },
            "required": ["file_path", "search_space_id"],
        },
    },
    {
        "name": "surfsense_list_documents",
        "description": "List all indexed documents in a search space with their status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search_space_id": {"type": "integer", "description": "Search space ID"},
            },
            "required": ["search_space_id"],
        },
    },
    {
        "name": "surfsense_query",
        "description": (
            "Query the knowledge base with natural language. Returns structured JSON "
            "for dashboard rendering: summary, tables, metrics, charts. "
            "Optionally continue an existing thread with thread_id."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language query"},
                "search_space_id": {"type": "integer", "description": "Search space ID"},
                "thread_id": {
                    "type": "string",
                    "description": "Optional existing thread ID to continue",
                },
            },
            "required": ["query", "search_space_id"],
        },
    },
    {
        "name": "surfsense_extract_tables",
        "description": (
            "Extract all tables, metrics and structured data from a specific document. "
            "Returns JSON ready for dashboard rendering."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "integer", "description": "Document ID"},
                "search_space_id": {"type": "integer", "description": "Search space ID"},
            },
            "required": ["doc_id", "search_space_id"],
        },
    },
]


async def dispatch_tool(name: str, args: dict) -> Any:
    """Route tool calls to their implementations."""
    match name:
        case "surfsense_list_spaces":
            return await tool_list_spaces()
        case "surfsense_create_space":
            return await tool_create_space(**args)
        case "surfsense_upload":
            return await tool_upload(**args)
        case "surfsense_list_documents":
            return await tool_list_documents(**args)
        case "surfsense_query":
            return await tool_query(**args)
        case "surfsense_extract_tables":
            return await tool_extract_tables(**args)
        case _:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# MCP protocol handlers
# ---------------------------------------------------------------------------


@app.post("/mcp")
async def mcp_endpoint(request: Request) -> JSONResponse:
    """Handle MCP JSON-RPC requests from Hermes."""
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    logger.info("MCP request: %s", method)

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "unidash-mcp", "version": "0.1.0"},
            }

        elif method == "tools/list":
            result = {"tools": TOOL_DEFINITIONS}

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            data = await dispatch_tool(tool_name, tool_args)
            result = {
                "content": [
                    {"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}
                ]
            }

        elif method == "notifications/initialized":
            # No response needed for notifications
            return JSONResponse(content=None, status_code=204)

        else:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            )

        return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "result": result})

    except HTTPException as e:
        logger.error("Tool error: %s", e.detail)
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": e.detail},
            },
            status_code=200,  # MCP errors go in body, not HTTP status
        )
    except Exception as e:
        logger.exception("Unexpected error in MCP handler")
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(e)},
            },
            status_code=200,
        )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "unidash-mcp"}


@app.get("/tools")
async def list_tools() -> dict:
    """Debug endpoint — list available tools."""
    return {"tools": [t["name"] for t in TOOL_DEFINITIONS]}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting UniDash MCP Wrapper on port %s", MCP_PORT)
    logger.info("SurfSense backend: %s", SURFSENSE_BASE)
    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT, log_level="info")
