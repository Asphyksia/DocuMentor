"""
DocuMentor Bridge Server
------------------------
WebSocket server that connects the Next.js dashboard to Hermes/MCP.
Single point of communication — the dashboard never talks to MCP or SurfSense directly.

Protocol:
  Client → Server:
    { "type": "query",            "payload": { "query": "...", "search_space_id": 1 } }
    { "type": "upload",           "payload": { "filename": "...", "data": "<base64>", "search_space_id": 1 } }
    { "type": "list_docs",        "payload": { "search_space_id": 1 } }
    { "type": "list_spaces" }
    { "type": "create_space",     "payload": { "name": "...", "description": "..." } }
    { "type": "extract",          "payload": { "doc_id": 1, "search_space_id": 1 } }
    { "type": "delete_document",  "payload": { "document_id": 5, "search_space_id": 1 } }
    { "type": "delete_space",     "payload": { "search_space_id": 2 } }
    { "type": "search_documents", "payload": { "title": "budget", "search_space_id": 1 } }
    { "type": "mcp_call",         "payload": { "tool": "<any_mcp_tool>", "args": { ... } } }
    { "type": "status" }

  Server → Client:
    { "type": "result",     "payload": { ... dashboard JSON ... } }
    { "type": "status",     "payload": { "state": "uploading|indexing|querying|ready|error", "message": "..." } }
    { "type": "documents",  "payload": { ... document list ... } }
    { "type": "spaces",     "payload": { ... spaces list ... } }
    { "type": "mcp_result", "payload": { "tool": "...", "result": { ... } } }
    { "type": "error",      "payload": { "message": "..." } }

Usage:
  pip install fastapi uvicorn httpx python-multipart websockets
  python backend/bridge.py

Ports:
  Bridge WebSocket: 8001
  MCP Wrapper:      8000 (called internally)
"""

import asyncio
import base64
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MCP_BASE = os.getenv("MCP_URL", "http://localhost:8000")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "8001"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("documenter-bridge")

app = FastAPI(title="DocuMentor Bridge", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Connected clients
# ---------------------------------------------------------------------------

active_connections: set[WebSocket] = set()


async def broadcast(message: dict):
    """Send a message to all connected clients."""
    text = json.dumps(message, ensure_ascii=False)
    dead = set()
    for ws in active_connections:
        try:
            await ws.send_text(text)
        except Exception:
            dead.add(ws)
    active_connections.difference_update(dead)


# ---------------------------------------------------------------------------
# MCP client
# ---------------------------------------------------------------------------

async def mcp_call(tool: str, args: dict) -> dict:
    """Call a tool on the MCP wrapper via JSON-RPC."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{MCP_BASE}/mcp",
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
            raise Exception(data["error"].get("message", "MCP error"))
        content = data["result"]["content"][0]["text"]
        return json.loads(content)


# ---------------------------------------------------------------------------
# Message handlers
# ---------------------------------------------------------------------------

async def handle_status(ws: WebSocket):
    """Return system health status."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            mcp_health = await client.get(f"{MCP_BASE}/health")
        mcp_ok = mcp_health.status_code == 200
    except Exception:
        mcp_ok = False

    await ws.send_json({
        "type": "status",
        "payload": {
            "state": "ready" if mcp_ok else "error",
            "mcp": mcp_ok,
            "message": "All systems operational" if mcp_ok else "MCP wrapper not responding",
        },
    })


async def handle_list_spaces(ws: WebSocket):
    """List search spaces."""
    try:
        result = await mcp_call("surfsense_list_spaces", {})
        await ws.send_json({"type": "spaces", "payload": result})
    except Exception as e:
        await ws.send_json({"type": "error", "payload": {"message": str(e)}})


async def handle_create_space(ws: WebSocket, payload: dict):
    """Create a new search space."""
    try:
        result = await mcp_call("surfsense_create_space", {
            "name": payload["name"],
            "description": payload.get("description", ""),
        })
        await ws.send_json({"type": "space_created", "payload": result})
    except Exception as e:
        await ws.send_json({"type": "error", "payload": {"message": str(e)}})


async def handle_list_docs(ws: WebSocket, payload: dict):
    """List documents in a search space."""
    try:
        result = await mcp_call("surfsense_list_documents", {
            "search_space_id": payload["search_space_id"],
        })
        await ws.send_json({"type": "documents", "payload": result})
    except Exception as e:
        await ws.send_json({"type": "error", "payload": {"message": str(e)}})


async def handle_upload(ws: WebSocket, payload: dict):
    """
    Upload a file: receive base64 data, save to temp, send to MCP,
    poll for indexing completion, then extract structured data.
    """
    filename = payload.get("filename", "unknown")
    file_data = payload.get("data", "")
    search_space_id = payload.get("search_space_id", 1)

    try:
        # Status: uploading
        await ws.send_json({
            "type": "status",
            "payload": {"state": "uploading", "message": f"Uploading {filename}..."},
        })

        # Decode and save to temp file
        raw_bytes = base64.b64decode(file_data)
        suffix = Path(filename).suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="documenter-")
        tmp.write(raw_bytes)
        tmp.close()

        # Upload via MCP
        upload_result = await mcp_call("surfsense_upload", {
            "file_path": tmp.name,
            "search_space_id": search_space_id,
        })

        doc_ids = upload_result.get("document_ids", [])

        # Status: indexing
        await ws.send_json({
            "type": "status",
            "payload": {"state": "indexing", "message": f"Indexing {filename}..."},
        })

        # Poll for document readiness (max 60s) using batch status endpoint
        doc_id = doc_ids[0] if doc_ids else None
        if doc_id:
            for _ in range(30):
                await asyncio.sleep(2)
                try:
                    status = await mcp_call("surfsense_document_status", {
                        "search_space_id": search_space_id,
                        "document_ids": str(doc_id),
                    })
                    items = status.get("items", [])
                    if items and items[0].get("state") == "ready":
                        break
                except Exception:
                    # Fallback to list_documents if status endpoint fails
                    docs = await mcp_call("surfsense_list_documents", {
                        "search_space_id": search_space_id,
                    })
                    doc_list = docs.get("documents", [])
                    target = next((d for d in doc_list if d["id"] == doc_id), None)
                    if target and target.get("status") == "ready":
                        break

            # Status: extracting
            await ws.send_json({
                "type": "status",
                "payload": {"state": "querying", "message": f"Analyzing {filename}..."},
            })

            # Extract structured data
            extracted = await mcp_call("surfsense_extract_tables", {
                "doc_id": doc_id,
                "search_space_id": search_space_id,
            })

            dashboard = extracted.get("dashboard", {})
        else:
            dashboard = {
                "type": "generic",
                "summary": f"File {filename} uploaded but no structured data extracted.",
                "views": [],
            }

        # Clean up temp file
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

        # Send result
        await ws.send_json({
            "type": "result",
            "payload": {
                "action": "upload",
                "filename": filename,
                "doc_id": doc_id,
                "dashboard": dashboard,
            },
        })

        # Status: ready
        await ws.send_json({
            "type": "status",
            "payload": {"state": "ready", "message": f"{filename} processed successfully"},
        })

        # Send updated document list
        await handle_list_docs(ws, {"search_space_id": search_space_id})

    except Exception as e:
        logger.exception("Upload error")
        await ws.send_json({
            "type": "status",
            "payload": {"state": "error", "message": f"Upload failed: {e}"},
        })
        await ws.send_json({"type": "error", "payload": {"message": str(e)}})


async def handle_query(ws: WebSocket, payload: dict):
    """Natural language query against the knowledge base."""
    query = payload.get("query", "")
    search_space_id = payload.get("search_space_id", 1)
    thread_id = payload.get("thread_id")

    try:
        await ws.send_json({
            "type": "status",
            "payload": {"state": "querying", "message": "Searching documents..."},
        })

        args = {"query": query, "search_space_id": search_space_id}
        if thread_id:
            args["thread_id"] = thread_id

        result = await mcp_call("surfsense_query", args)

        await ws.send_json({
            "type": "result",
            "payload": {
                "action": "query",
                "query": query,
                "thread_id": result.get("thread_id"),
                "dashboard": result.get("dashboard", {}),
            },
        })

        await ws.send_json({
            "type": "status",
            "payload": {"state": "ready", "message": "Query complete"},
        })

    except Exception as e:
        logger.exception("Query error")
        await ws.send_json({
            "type": "status",
            "payload": {"state": "error", "message": f"Query failed: {e}"},
        })
        await ws.send_json({"type": "error", "payload": {"message": str(e)}})


async def handle_extract(ws: WebSocket, payload: dict):
    """Extract tables from a specific document."""
    doc_id = payload.get("doc_id")
    search_space_id = payload.get("search_space_id", 1)

    try:
        await ws.send_json({
            "type": "status",
            "payload": {"state": "querying", "message": "Extracting data..."},
        })

        result = await mcp_call("surfsense_extract_tables", {
            "doc_id": doc_id,
            "search_space_id": search_space_id,
        })

        await ws.send_json({
            "type": "result",
            "payload": {
                "action": "extract",
                "doc_id": doc_id,
                "dashboard": result.get("dashboard", {}),
            },
        })

        await ws.send_json({
            "type": "status",
            "payload": {"state": "ready", "message": "Extraction complete"},
        })

    except Exception as e:
        logger.exception("Extract error")
        await ws.send_json({"type": "error", "payload": {"message": str(e)}})


# ---------------------------------------------------------------------------
# Generic MCP passthrough — exposes ALL 25 tools to the dashboard
# ---------------------------------------------------------------------------

async def handle_mcp_call(ws: WebSocket, payload: dict):
    """
    Generic passthrough: call any MCP tool by name.
    Client sends: { "type": "mcp_call", "payload": { "tool": "surfsense_delete_document", "args": { "document_id": 5 } } }
    Server returns: { "type": "mcp_result", "payload": { "tool": "...", "result": { ... } } }
    """
    tool = payload.get("tool", "")
    args = payload.get("args", {})
    request_id = payload.get("request_id")

    if not tool:
        await ws.send_json({"type": "error", "payload": {"message": "Missing 'tool' in mcp_call"}})
        return

    try:
        result = await mcp_call(tool, args)
        response: dict[str, Any] = {
            "type": "mcp_result",
            "payload": {"tool": tool, "result": result},
        }
        if request_id:
            response["payload"]["request_id"] = request_id
        await ws.send_json(response)
    except Exception as e:
        logger.error("MCP passthrough error (%s): %s", tool, e)
        response = {"type": "error", "payload": {"message": str(e), "tool": tool}}
        if request_id:
            response["payload"]["request_id"] = request_id
        await ws.send_json(response)


async def handle_delete_document(ws: WebSocket, payload: dict):
    """Delete a document and refresh the list."""
    try:
        result = await mcp_call("surfsense_delete_document", {
            "document_id": payload["document_id"],
        })
        await ws.send_json({"type": "mcp_result", "payload": {"tool": "surfsense_delete_document", "result": result}})
        # Refresh doc list
        if "search_space_id" in payload:
            await handle_list_docs(ws, {"search_space_id": payload["search_space_id"]})
    except Exception as e:
        await ws.send_json({"type": "error", "payload": {"message": str(e)}})


async def handle_delete_space(ws: WebSocket, payload: dict):
    """Delete a search space and refresh the list."""
    try:
        result = await mcp_call("surfsense_delete_space", {
            "search_space_id": payload["search_space_id"],
        })
        await ws.send_json({"type": "mcp_result", "payload": {"tool": "surfsense_delete_space", "result": result}})
        await handle_list_spaces(ws)
    except Exception as e:
        await ws.send_json({"type": "error", "payload": {"message": str(e)}})


async def handle_search_documents(ws: WebSocket, payload: dict):
    """Search documents by title."""
    try:
        result = await mcp_call("surfsense_search_documents", {
            "title": payload["title"],
            "search_space_id": payload.get("search_space_id"),
        })
        await ws.send_json({"type": "documents", "payload": result})
    except Exception as e:
        await ws.send_json({"type": "error", "payload": {"message": str(e)}})


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

HANDLERS = {
    "status": lambda ws, _: handle_status(ws),
    "list_spaces": lambda ws, _: handle_list_spaces(ws),
    "create_space": lambda ws, p: handle_create_space(ws, p),
    "list_docs": lambda ws, p: handle_list_docs(ws, p),
    "upload": lambda ws, p: handle_upload(ws, p),
    "query": lambda ws, p: handle_query(ws, p),
    "extract": lambda ws, p: handle_extract(ws, p),
    "delete_document": lambda ws, p: handle_delete_document(ws, p),
    "delete_space": lambda ws, p: handle_delete_space(ws, p),
    "search_documents": lambda ws, p: handle_search_documents(ws, p),
    "mcp_call": lambda ws, p: handle_mcp_call(ws, p),
}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_connections.add(ws)
    logger.info("Client connected (%d total)", len(active_connections))

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({
                    "type": "error",
                    "payload": {"message": "Invalid JSON"},
                })
                continue

            msg_type = msg.get("type", "")
            payload = msg.get("payload", {})

            handler = HANDLERS.get(msg_type)
            if handler:
                # Run handler as task so we don't block the receive loop
                asyncio.create_task(handler(ws, payload))
            else:
                await ws.send_json({
                    "type": "error",
                    "payload": {"message": f"Unknown message type: {msg_type}"},
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("WebSocket error")
    finally:
        active_connections.discard(ws)
        logger.info("Client disconnected (%d remaining)", len(active_connections))


# ---------------------------------------------------------------------------
# REST endpoints (for health checks and debugging)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "documenter-bridge",
        "clients": len(active_connections),
    }


@app.get("/connections")
async def connections():
    return {"count": len(active_connections)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting DocuMentor Bridge on port %s", BRIDGE_PORT)
    logger.info("MCP wrapper: %s", MCP_BASE)
    uvicorn.run(app, host="0.0.0.0", port=BRIDGE_PORT, log_level="info")
