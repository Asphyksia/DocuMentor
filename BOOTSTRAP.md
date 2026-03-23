# BOOTSTRAP.md — DocuMentor Setup Guide

> This file is read by DocuMentor on first boot.
> Follow these steps with the user to get everything running.
> Once setup is complete, this file can be ignored on future sessions.

---

## Your Role During Setup
You are the installer. Guide the user step by step, one action at a time.
Do not overwhelm them — ask only what is needed, when it is needed.
Run silent checks in the background and only surface problems if they occur.
Celebrate small wins ("SurfSense is running ✓").

---

## Step 0 — Workspace Configuration (silent, runs first)
Before anything else, detect where DocuMentor is installed and configure Hermes to use it as workspace:

```python
execute_code("""
import os, subprocess, pathlib, yaml

# Find the DocuMentor repo root (the folder containing this BOOTSTRAP.md)
bootstrap_path = pathlib.Path(__file__).resolve() if '__file__' in dir() else pathlib.Path.cwd()
repo_root = bootstrap_path.parent if bootstrap_path.is_file() else bootstrap_path

# Locate Hermes config
hermes_config_path = pathlib.Path.home() / '.hermes' / 'config.yaml'
hermes_config_path.parent.mkdir(parents=True, exist_ok=True)

# Load existing config or start fresh
if hermes_config_path.exists():
    with open(hermes_config_path) as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}

# Set workspace to DocuMentor repo root
config['workspace'] = str(repo_root)

with open(hermes_config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print(f'Workspace set to: {repo_root}')
print(f'Hermes config updated: {hermes_config_path}')
""")
```

Once done, Hermes will always read `SOUL.md`, `BOOTSTRAP.md`, and `DOCSTEMPLATES.md` from the cloned repo — so a `git pull` is all that's needed to update the agent's behavior.

---

## Step 0b — Pre-flight Checks (silent)
Before talking to the user, verify silently:

```python
# Check Docker is running
execute_code("""
import subprocess
result = subprocess.run(['docker', 'info'], capture_output=True)
print('ok' if result.returncode == 0 else 'docker_not_running')
""")

# Check available disk space (need ~5GB)
execute_code("""
import shutil
free = shutil.disk_usage('/').free / (1024**3)
print(f'{free:.1f}GB free')
""")

# Check ports 8000, 8929, 3929 are free
execute_code("""
import socket
ports = {'MCP Wrapper': 8000, 'SurfSense Backend': 8929, 'Dashboard': 3929}
for name, port in ports.items():
    s = socket.socket()
    result = s.connect_ex(('localhost', port))
    s.close()
    print(f'{name} ({port}): {"already in use" if result == 0 else "free"}')
""")
```

If Docker is not running → tell the user:
*"Before we start, please open Docker Desktop and make sure it's running, then let me know."*

If disk space < 5GB → warn the user.

If any port is already in use → note it, we may need to adjust the config.

---

## Step 1 — Welcome & API Key

Say to the user (in their language):

> "Welcome to DocuMentor setup. I'll get everything running for you — it should take about 5 minutes.
> First, I need one thing: your **RelayGPU API key**.
> You can get it at [relay.opengpu.network](https://relay.opengpu.network) if you don't have one yet.
> It looks like: `relay_sk_...`"

Wait for the key. Validate format: must start with `relay_sk_`.

Save it as `RELAYGPU_API_KEY` — you'll need it in Steps 2 and 3.

---

## Step 2 — SurfSense (Knowledge Base)

Tell the user:
> "Setting up the document knowledge base... this may take 2-3 minutes while Docker downloads the images."

Run silently:

```bash
# 1. Create .env for SurfSense from the example
cp SurfSense/docker/.env.example SurfSense/docker/.env

# 2. Write RelayGPU credentials into SurfSense .env
# Replace these lines in SurfSense/docker/.env:
OPENAI_API_KEY=<RELAYGPU_API_KEY>
OPENAI_BASE_URL=https://api.relaygpu.com/v1
LLM_MODEL_NAME=anthropic/claude-sonnet-4-6
EMBEDDING_MODEL_NAME=text-embedding-3-small

# 3. Start SurfSense
cd SurfSense/docker && docker compose up -d

# 4. Wait for healthy status (up to 3 minutes)
# Poll: curl -s http://localhost:8929/health
```

Once healthy → *"Knowledge base is running ✓"*

If it fails → show the docker compose logs and ask the user to paste any error.

---

## Step 3 — MCP Wrapper

Run silently:

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Create backend .env
cp backend/.env.example backend/.env
# Write into backend/.env:
SURFSENSE_BASE_URL=http://localhost:8929
SURFSENSE_EMAIL=admin@documenter.local
SURFSENSE_PASSWORD=<ask_user_to_set>
MCP_PORT=8000

# Start the wrapper in background
nohup python backend/mcp_wrapper.py > backend/mcp.log 2>&1 &

# Verify it responds
curl -s http://localhost:8000/health
```

Once healthy → *"Document tools are ready ✓"*

---

## Step 4 — Hermes MCP Config

Write the MCP server entry into `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  documenter:
    url: "http://localhost:8000/mcp"
    timeout: 120
    connect_timeout: 30
```

Verify the MCP connection:
- Call `surfsense_list_spaces()` — should return an empty list (no error)
- If it works → *"Connected to knowledge base ✓"*

---

## Step 5 — Dashboard

Tell the user:
> "Setting up the dashboard..."

```bash
cd frontend
npm install
npm run dev
# Dashboard available at http://localhost:3000
```

If Node.js is not installed → guide the user:
> "Please install Node.js from [nodejs.org](https://nodejs.org) (LTS version), then let me know."

Once running → *"Dashboard is live at http://localhost:3000 ✓"*

---

## Step 6 — Create Default Search Space

Run silently via MCP:
```
surfsense_create_space("University Documents", "Default space for all university documents")
```

Save the returned `search_space_id` to memory — this is the default for all uploads.

---

## Step 7 — Ready

Tell the user:

> "Everything is set up! Here's what's running:
> - 📚 Knowledge base: http://localhost:8929
> - 🔧 Document tools: http://localhost:8000
> - 📊 Dashboard: http://localhost:3000
>
> To get started, upload your first document — just send me the file path or drag it into the chat.
> I'll extract the data and generate a dashboard for you."

Then proceed with the normal onboarding flow from SOUL.md (ask name, tone, document focus).

---

## Troubleshooting Reference

| Problem | Check |
|---|---|
| Docker not found | Install Docker Desktop from docker.com |
| Port 8929 in use | Another service is using it — run `lsof -i :8929` |
| SurfSense unhealthy after 3min | Run `docker compose logs backend` in SurfSense/docker |
| MCP wrapper won't start | Check `backend/mcp.log` for errors |
| Dashboard won't build | Run `npm install` again, check Node version ≥ 18 |
| API key rejected | Verify key starts with `relay_sk_` and has credits |
