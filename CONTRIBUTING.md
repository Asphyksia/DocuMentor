# Contributing to DocuMentor

Thanks for your interest in contributing! Here's how to get started.

## Getting Started

1. Fork the repo and clone it
2. Follow the [Quick Start](README.md#quick-start) to set up your dev environment
3. Create a feature branch: `git checkout -b feature/my-feature`

## Development Setup

```bash
git clone https://github.com/YOUR_USER/DocuMentor
cd DocuMentor
git submodule update --init --recursive
cp .env.example .env
# Edit .env with your API key

# Start backend
docker compose up -d

# Start frontend (dev mode)
cd frontend && npm install && npm run dev
```

## Project Structure

- `backend/mcp_wrapper.py` — MCP server (25 tools wrapping SurfSense)
- `backend/bridge.py` — WebSocket bridge between dashboard and MCP
- `frontend/` — Next.js dashboard (React + Tremor + Framer Motion)
- `SOUL.md` — Agent personality and workflow
- `DOCSTEMPLATES.md` — JSON output schemas for dashboard rendering

## What to Contribute

- **Bug fixes** — always welcome
- **New view types** — add to `DOCSTEMPLATES.md` + `DashboardRenderer.tsx`
- **Better document parsing** — improve extraction quality for specific file types
- **Tests** — we need them! Unit tests for MCP tools, E2E for the dashboard
- **Documentation** — improve README, add examples, write tutorials
- **i18n** — translate the UI (currently English only)

## Pull Request Guidelines

1. Keep PRs focused — one feature or fix per PR
2. Update `DOCSTEMPLATES.md` if you add/change JSON schemas
3. Test your changes with at least one document upload
4. Follow existing code style (Python: PEP 8, TypeScript: Prettier defaults)
5. Update README if your change affects setup or usage

## Code Style

- **Python:** PEP 8, type hints, async/await, f-strings
- **TypeScript:** Strict mode, functional components, named exports
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, etc.

## Issues

- Use GitHub Issues for bug reports and feature requests
- Tag with appropriate labels
- Include reproduction steps for bugs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
