# 0.4.2 — preview
- Create a project, optional GitHub binding and opt-in polling schedule atomically in one form. No immediate API request, no overwrite of existing projects and no automatic MCP grant.
- Browser, storage and HTTP regression tests cover setup, input validation, duplicate conflict and authorization.

# 0.4.1 — preview
- Download repository-specific AGENTS.md from Integrations for the selected project, with explicit project scope, historical-data warnings and permission-aware writes. No credentials, automatic installation or configuration changes.

# 0.4.0 — preview
- Local stdio MCP adapter with legacy initialize handshake, six read tools and optional append-only reported memory.
- Optional project allowlist, bounded input/results and subprocess wire tests.
- Opt-in standalone Streamable HTTP MCP (legacy 2025 revisions), loopback-only, separate bearer token, explicit project allowlist, bounded expiring sessions.
- Managed HA HTTPS MCP: explicit opt-in, unmapped port by default, TLS certificate from dedicated app configuration folder, fail-closed configuration, authenticated status endpoint.
- Independent MCP Python SDK 1.26.0 interoperability gate (CI-only dependency): stdio, HTTP and managed HTTPS; client setup guide.
- Bound context output by serialized byte budget, including Unicode.
- Authenticated Windows Codex setup download, endpoint prefilled but no token; local HTTPS/MCP probe and native Codex CLI registration.
- Windows Codex read/write and fresh-session recovery reported in physical acceptance; OAuth, modern 2026 protocol and Claude Code acceptance remain pending.

# 0.3.0 — preview
- Public GitHub repository binding and manual read-only sync, five recent objects per endpoint.
- Commits, PR head metadata and workflow run attempt/conclusion imported as historical evidence, not acceptance.
- Deterministic deduplication and transactional journal/FTS writes; changed observations retained.
- Opt-in automatic polling, persisted interval and shared five-minute gate; one-hour pause after HTTP 403/429; latest 20 attempts per project.
- Optional fine-grained GitHub PAT via HA app options or standalone environment; private repository read support (live acceptance pending). Logical backup deliberately excludes scheduling, attempt history and cooldown; restored bindings require explicit re-enabling.
- Logical backup v2 preserves repository bindings and imported evidence; legacy v1 remains accepted.

# 0.2.3 — preview
- Home Assistant store icon and logo with PNG integrity/dimension tests.
- Consistent all-project logical JSON backup with SHA-256 integrity check and 4 MiB size bound.
- Transactional restore to empty databases only; preserves IDs, timestamps and provenance; rebuilds FTS.
- Authenticated export/import in Settings, no overwrite or database deletion endpoint.
- Backup tests for roundtrip, checksum, bounds, isolation and refusal to overwrite.

# 0.2.2 — preview
- Responsive workspace with Memory, Projects, Integrations and Settings tabs.
- Russian/English labels and system/light/dark appearance preferences.
- Detect deployment mode from health endpoint; hide standalone authentication in Ingress.
- Experimental store classification; no database schema changes.
- Integration tabs are roadmap information only.
- Browser CI exercises standalone API and simulated Ingress routing; serialized workspace actions and draft reset on logout.

# 0.2.1 — preview
- Bound HTTP concurrency to eight workers and reduce page size to 20.
- Bound Markdown context and validate request framing.
- Handle SIGTERM and SIGINT to stop accepting new requests.
- Add image runtime smoke tests for both architectures (CI required).

# 0.2.0 — preview
- Generic projects; no preloaded personal data.
- Persistent SQLite, FTS5, append/delete journal, context export, REST API and web UI.
- HA Ingress packaging and independent Docker/native mode.
- No MCP, CI sync or physical-device acceptance yet.
