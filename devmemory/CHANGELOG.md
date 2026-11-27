# 0.3.0 — preview
- Public GitHub repository binding and manual read-only sync, five recent objects per endpoint.
- Commits, PR head metadata and workflow run attempt/conclusion imported as historical evidence, not acceptance.
- Deterministic deduplication and transactional journal/FTS writes; changed observations retained.
- No GitHub token, private repository access or automatic polling in this increment.
- Logical JSON backup includes imported evidence but not integration bindings; rebind after restore.

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
