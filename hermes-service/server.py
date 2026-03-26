"""
Hermes Service — HTTP wrapper for Hermes AIAgent
-------------------------------------------------
Lightweight FastAPI server that exposes Hermes AIAgent via:
  POST /query    — run a query with SSE streaming
  GET  /health   — health check

The bridge talks to this service over HTTP instead of importing AIAgent directly.
This allows Hermes to run in its own container with isolated dependencies.

SSE event types sent to the client:
  event: delta      data: {"delta": "text chunk"}
  event: tool       data: {"tool": "tool_name", "status": "running", "preview": "..."}
  event: status     data: {"message": "Thinking..."}
  event: done       data: {"response": "full text", "messages": [...], "dashboard": {...}}
  event: error      data: {"error": "message"}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

# ---------------------------------------------------------------------------
# Hermes AIAgent import
# ---------------------------------------------------------------------------

HERMES_AGENT_DIR = os.getenv(
    "HERMES_AGENT_DIR",
    os.path.join(os.path.dirname(__file__), "..", "hermes-agent"),
)
if os.path.isdir(HERMES_AGENT_DIR) and HERMES_AGENT_DIR not in sys.path:
    sys.path.insert(0, HERMES_AGENT_DIR)

from run_agent import AIAgent  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HERMES_PORT = int(os.getenv("HERMES_PORT", "8002"))
HERMES_MODEL = os.getenv("HERMES_MODEL", "qwen/qwen3-235b-a22b")
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "https://openrouter.ai/api/v1")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
HERMES_MAX_ITERATIONS = int(os.getenv("HERMES_MAX_ITERATIONS", "20"))
MCP_URL = os.getenv("MCP_URL", "http://mcp-wrapper:8000/mcp/")

SYSTEM_PROMPT = """You are DocuMentor, an intelligent document analysis assistant for universities.
You help users understand, query, and extract insights from their uploaded documents.

You have access to SurfSense tools for document management and querying.
When answering questions:
1. Use the available search/query tools to find relevant information in the knowledge base.
2. Always cite which documents your information comes from.
3. If you can extract structured data (tables, metrics, KPIs), format it as JSON for dashboard rendering.
4. Be concise but thorough. Answer in the same language the user writes in.
5. If no relevant documents are found, say so honestly.

You are running inside DocuMentor, a self-hosted document intelligence platform.
Do NOT identify yourself as SurfSense or any other tool — you are DocuMentor."""

logger = logging.getLogger("hermes-service")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Hermes Service", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Internal service — only bridge talks to this
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Agent management
# ---------------------------------------------------------------------------

_agent_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hermes")
_agent: Optional[AIAgent] = None
_agent_lock = asyncio.Lock()


def _create_agent() -> AIAgent:
    """Create a configured AIAgent instance."""
    # Ensure MCP tools are discovered (may fail at import time if mcp-wrapper wasn't ready)
    try:
        from tools.mcp_tool import discover_mcp_tools
        tool_names = discover_mcp_tools()
        logger.info("MCP discovery found %d tools: %s", len(tool_names), ", ".join(tool_names[:5]))
    except Exception as e:
        logger.warning("MCP tool rediscovery failed: %s", e)

    agent = AIAgent(
        base_url=HERMES_BASE_URL,
        api_key=HERMES_API_KEY,
        model=HERMES_MODEL,
        max_iterations=HERMES_MAX_ITERATIONS,
        platform="web",
        enabled_toolsets=["mcp-documenter"],
        skip_context_files=True,
        skip_memory=True,
        quiet_mode=True,
        ephemeral_system_prompt=SYSTEM_PROMPT,
    )
    tool_names = [t.get("function", {}).get("name", "?") for t in (agent.tools or [])]
    logger.info(
        "AIAgent created (model=%s, base_url=%s, tools=%d)",
        HERMES_MODEL,
        HERMES_BASE_URL,
        len(tool_names),
    )
    if tool_names:
        logger.info("Registered tools: %s", ", ".join(tool_names))
    else:
        logger.warning("⚠️ No tools registered! Check MCP config at /root/.hermes/config.yaml")
    return agent


async def get_agent() -> AIAgent:
    """Get or create the singleton AIAgent."""
    global _agent
    async with _agent_lock:
        if _agent is None:
            loop = asyncio.get_running_loop()
            _agent = await loop.run_in_executor(_agent_executor, _create_agent)
        return _agent


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    search_space_id: int = Field(default=1)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    thread_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Dashboard parser (same as bridge)
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(\{.*?\})\s*\n```", re.DOTALL)


def _parse_dashboard(text: str) -> Optional[dict]:
    """Try to extract a dashboard JSON block from the response text."""
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and "type" in data:
                return data
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# SSE query endpoint
# ---------------------------------------------------------------------------

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    """Run a query through Hermes AIAgent with SSE streaming."""

    agent = await get_agent()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    # Callbacks: push events into the async queue from the executor thread
    def on_stream_delta(delta: str | None) -> None:
        if delta is None:
            return  # We send 'done' after run_conversation completes
        asyncio.run_coroutine_threadsafe(
            queue.put({"event": "delta", "data": {"delta": delta}}),
            loop,
        )

    def on_tool_progress(tool_name: str, args_preview: str = "") -> None:
        asyncio.run_coroutine_threadsafe(
            queue.put({
                "event": "tool",
                "data": {"tool": tool_name, "status": "running", "preview": args_preview[:100]},
            }),
            loop,
        )

    def on_status(status_msg: str) -> None:
        asyncio.run_coroutine_threadsafe(
            queue.put({"event": "status", "data": {"message": status_msg}}),
            loop,
        )

    # Configure callbacks
    agent.stream_delta_callback = on_stream_delta
    agent.tool_progress_callback = on_tool_progress
    agent.status_callback = on_status

    async def event_generator():
        """Generate SSE events from the queue."""
        # Start the agent in the thread pool
        def _run():
            try:
                result = agent.run_conversation(
                    user_message=request.query,
                    conversation_history=list(request.conversation_history),
                )
                return result
            except Exception as e:
                logger.exception("Agent error")
                return {"error": str(e)}

        task = loop.run_in_executor(_agent_executor, _run)

        # Stream events until the agent finishes
        while True:
            # Check if task is done
            if task.done():
                # Drain remaining events
                while not queue.empty():
                    item = await queue.get()
                    yield {
                        "event": item["event"],
                        "data": json.dumps(item["data"]),
                    }
                break

            # Wait for events with timeout
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield {
                    "event": item["event"],
                    "data": json.dumps(item["data"]),
                }
            except asyncio.TimeoutError:
                continue

        # Get the result
        try:
            result = await task
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }
            return

        if "error" in result:
            yield {
                "event": "error",
                "data": json.dumps({"error": result["error"]}),
            }
            return

        # Build final response
        final_response = result.get("final_response", "")
        messages = result.get("messages", [])
        dashboard = _parse_dashboard(final_response)
        if dashboard is None:
            dashboard = {"type": "summary", "content": final_response, "query": request.query}

        yield {
            "event": "done",
            "data": json.dumps({
                "response": final_response,
                "messages": messages,
                "dashboard": dashboard,
            }),
        }

        # Clear callbacks
        agent.stream_delta_callback = None
        agent.tool_progress_callback = None
        agent.status_callback = None

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "hermes-agent",
        "version": "0.4.0",
        "model": HERMES_MODEL,
        "agent_ready": _agent is not None,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Hermes Service v0.4.0 on port %s", HERMES_PORT)
    logger.info("Model: %s @ %s", HERMES_MODEL, HERMES_BASE_URL)
    logger.info("MCP URL: %s", MCP_URL)
    uvicorn.run(app, host="0.0.0.0", port=HERMES_PORT, log_level="info")
