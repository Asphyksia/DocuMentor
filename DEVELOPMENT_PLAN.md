# DocuMentor — Development Plan

> Created: 2026-03-29
> Status: Active
> Current version: v0.5.0

---

## Where We Are

DocuMentor is a working prototype. You can upload documents, query them with natural language, and get visual dashboards. Hermes Agent routes queries intelligently. The core architecture is solid.

**But it's not production-ready.** No auth, no tests, UX gaps, singleton agent bottleneck, and no persistent conversation history. The audit scored production readiness at 4/10.

---

## The Goal

Transform DocuMentor from a **functional demo** into a **deployable MVP** that a university department could actually use. Not enterprise-grade — but usable, secure enough, and reliable.

---

## Development Phases

### Phase 1 — Security & Stability (MVP Gate)
> Without this, nobody else can use it safely.

| # | Task | Est. | Priority | Files |
|---|------|------|----------|-------|
| 1.1 | **Basic auth system** — login with user/pass from .env, JWT token, WebSocket auth validation | 1-2 days | 🔴 Critical | `bridge.py`, new `auth.py`, frontend `LoginForm.tsx`, `useBridge.ts` |
| 1.2 | **Secure WebSocket handshake** — validate JWT on connection, reject unauthorized | 2-3 hrs | 🔴 Critical | `bridge.py` |
| 1.3 | **Environment validation** — startup check for required env vars, fail fast with clear errors | 1-2 hrs | 🟡 High | `bridge.py`, `server.py` |
| 1.4 | **Temp file cleanup** — ensure cleanup on crash/restart, not just happy path | 1 hr | 🟡 High | `bridge.py` |
| 1.5 | **Error boundaries** — React error boundary wrapping main UI sections | 2-3 hrs | 🟡 High | frontend `app/layout.tsx`, new `ErrorBoundary.tsx` |

**Milestone:** Auth-protected access, no silent failures on startup.

---

### Phase 2 — UX Polish
> Make it feel like a product, not a prototype.

| # | Task | Est. | Priority | Files |
|---|------|------|----------|-------|
| 2.1 | **Loading skeletons** — sidebar, chat, dashboard placeholders while loading | 3-4 hrs | 🟡 High | `DocSidebar.tsx`, `ChatPanel.tsx` |
| 2.2 | **Empty states** — "Upload your first document", "No conversations yet" | 2 hrs | 🟡 High | `DocSidebar.tsx`, `ChatPanel.tsx` |
| 2.3 | **Error handling with retry** — failed queries show retry button, failed uploads show re-upload | 3-4 hrs | 🟡 High | `ChatPanel.tsx`, `useChatState.ts` |
| 2.4 | **Connection status banner** — visible reconnection indicator when WebSocket drops | 1-2 hrs | 🟢 Medium | `AppHeader.tsx` or new `ConnectionBanner.tsx` |
| 2.5 | **Delete confirmation** — modal before deleting documents/spaces | 1-2 hrs | 🟢 Medium | `DocSidebar.tsx`, new `ConfirmDialog.tsx` |
| 2.6 | **Toast notifications** — for non-chat feedback (doc deleted, space created, etc.) | 2-3 hrs | 🟢 Medium | new `Toast.tsx` (shadcn has one) |
| 2.7 | **Keyboard shortcuts** — Ctrl+Enter send, Ctrl+U upload, Escape close modals | 2-3 hrs | 🟢 Medium | `page.tsx`, `ChatPanel.tsx`, `UploadModal.tsx` |

**Milestone:** Professional UX with proper feedback for every action.

---

### Phase 3 — Backend Robustness
> Make it scale beyond one user, one query at a time.

| # | Task | Est. | Priority | Files |
|---|------|------|----------|-------|
| 3.1 | **Agent pool** — replace singleton AIAgent with per-connection or pooled instances | 3-4 hrs | 🟡 High | `server.py` |
| 3.2 | **Structured logging** — structlog/loguru with JSON output, request IDs | 2-3 hrs | 🟡 High | `bridge.py`, `server.py` |
| 3.3 | **WebSocket reconnect backoff** — exponential backoff instead of fixed 3s | 1 hr | 🟢 Medium | `useBridge.ts` |
| 3.4 | **Graceful shutdown** — drain active connections, finish in-progress queries | 2-3 hrs | 🟢 Medium | `bridge.py` |
| 3.5 | **Health check improvements** — include service versions, uptime, agent pool status | 1-2 hrs | 🟢 Medium | `bridge.py`, `server.py` |

**Milestone:** Handles concurrent users without serializing queries.

---

### Phase 4 — Features
> New functionality that adds real value.

| # | Task | Est. | Priority | Files |
|---|------|------|----------|-------|
| 4.1 | **Persistent conversation history** — save to localStorage minimum, backend threads ideal | 1 day | 🟡 High | `useChatState.ts`, `ChatPanel.tsx`, optionally `bridge.py` |
| 4.2 | **Document sidebar search** — filter docs by name | 2-3 hrs | 🟢 Medium | `DocSidebar.tsx` |
| 4.3 | **Model selector in UI** — change LLM from settings panel without restarting | 1 day | 🟢 Medium | `SettingsPanel.tsx`, `bridge.py` (new handler) |
| 4.4 | **Export results** — copy response, export dashboard as image/PDF | 1 day | 🟢 Medium | `ChatPanel.tsx`, `DashboardRenderer.tsx` |
| 4.5 | **Responsive/mobile layout** — collapsible sidebar, full-width chat on mobile | 1 day | 🟢 Medium | `page.tsx`, `DocSidebar.tsx`, `DashboardRenderer.tsx` |
| 4.6 | **Light/dark theme toggle** — next-themes, adjust chart colors | 3-4 hrs | 🔵 Nice | All components with color refs |

**Milestone:** Feature-complete MVP.

---

### Phase 5 — Quality & Testing
> Confidence that changes don't break things.

| # | Task | Est. | Priority | Files |
|---|------|------|----------|-------|
| 5.1 | **Backend unit tests** — handler validation, Pydantic models, MCP call mocking | 2-3 days | 🟡 High | new `tests/` directory |
| 5.2 | **Frontend component tests** — React Testing Library for critical flows | 2-3 days | 🟢 Medium | new `__tests__/` |
| 5.3 | **Integration test** — upload → query → response round-trip | 1 day | 🟢 Medium | new `tests/integration/` |
| 5.4 | **CI pipeline** — GitHub Actions: lint, type-check, test on PR | 1 day | 🟢 Medium | `.github/workflows/` |

**Milestone:** Automated quality gates.

---

## Suggested Sprint Order

```
Sprint 1 (1 week):  Phase 1 (auth + security) + 2.1-2.3 (critical UX)
Sprint 2 (1 week):  Phase 2 remainder + 3.1-3.2 (agent pool + logging)
Sprint 3 (1 week):  Phase 4.1-4.3 (history, search, model selector)
Sprint 4 (1 week):  Phase 5.1-5.4 (tests + CI) + 4.4-4.6 (polish)
```

Total estimate: **~4 weeks** at moderate pace.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-29 | Auth before features | Audit rated security 5/10; no point building features on an unsecured system |
| 2026-03-29 | Hermes as separate container (v0.5.0) | Isolates dependencies, easier to upgrade/restart independently |
| 2026-03-29 | localStorage for chat history first | Quickest path to persistent history without backend changes |
| 2026-03-29 | No multi-tenancy yet | Single-user is fine for MVP; auth is just access control for now |

---

## Open Questions

1. **Auth scope** — Simple user/pass from .env, or do we want university SSO (OAuth/SAML) from the start?
2. **Deployment target** — Docker on a university server? Cloud? Affects some architecture decisions.
3. **Multi-user priority** — Is this single-department or needs multi-user from day one?
4. **Model selection** — Stick with RelayGPU or need to support Ollama (local) for data-sensitive deployments?

---

*This is a living document. Update as decisions are made and priorities shift.*
