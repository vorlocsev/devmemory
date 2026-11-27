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
