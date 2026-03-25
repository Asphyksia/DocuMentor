# Issue: MCP HTTP servers fail silently without `mcp[cli]`

## Repository
`nousresearch/hermes-agent`

## Title
MCP HTTP servers fail silently when `mcp[cli]` is not installed

## Description

When configuring an MCP server with `url:` (Streamable HTTP transport), Hermes fails to connect but doesn't report a clear error. The root cause is that `mcp[cli]` is not included in Hermes' base dependencies — only in the `[mcp]` optional group.

## Steps to reproduce

1. Fresh install of Hermes Agent (standard installer)
2. Add an HTTP MCP server to `~/.hermes/config.yaml`:
   ```yaml
   mcp_servers:
     my_server:
       url: "http://localhost:8000/mcp/"
   ```
3. Start Hermes: `hermes`
4. Try to use any MCP tool → silent failure or "MCP tool discovery failed" debug log

## Expected behavior

Either:
- `mcp[cli]` should be a base dependency (since HTTP MCP servers are a core feature)
- Or Hermes should emit a clear WARNING log: "mcp[cli] not installed — HTTP MCP servers require it. Run: `cd ~/.hermes/hermes-agent && uv pip install -e '.[mcp]'`"

## Workaround

Manually install in the Hermes venv:
```bash
cd ~/.hermes/hermes-agent
uv pip install "mcp[cli]"
```

## Environment
- Hermes Agent 0.4.0
- Python 3.11
- Ubuntu 22.04 / ZorinOS
