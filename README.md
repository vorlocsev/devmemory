# DevMemory
Independent, local-first memory for development agents. Preview 0.2.0. Python 3.11+ with SQLite FTS5, no third-party runtime dependencies. No telemetry or cloud calls.

## Home Assistant OS
Add https://github.com/vorlocsev/devmemory to the app store's Repositories menu, install DevMemory, start it and open Web UI. The image is built locally (internet required to fetch Python base). HAOS acceptance pending. See [app docs](devmemory/DOCS.md).

## Standalone Docker
Set DEVMEMORY_TOKEN to a random secret of at least 32 characters in your shell or a private .env file. Run docker compose up -d --build; open http://127.0.0.1:8099 and enter the token. Port is loopback-only. Do not publish unencrypted HTTP to remote users.

## Native Python (Linux/Windows)
Set the same environment variable and run python devmemory/server.py. Default listener is loopback port 8099 and data directory is ./data. Change with --data, --host, --port; use TLS and a reviewed authentication strategy before remote deployment.

## API
GET /api/projects; POST /api/projects (slug, name); POST /api/entries (project, kind, status, title, body, optional source, sha); GET /api/entries?project=demo&q=search&offset=0 (100/page); GET /api/context?project=demo (30 recent records, Markdown); POST /api/delete (project, id). Standalone API uses Authorization: Bearer <token>; POST also requires Content-Type: application/json and X-DevMemory: 1. Ingress relies on HA login and verifies supervisor peer IP. No CORS. No external API exposure in HA mode.

## Tests
python -m unittest discover -s devmemory/tests -v

## Roadmap
0.3 read-only exact-head GitHub snapshots and agent context workflow; 0.4 MCP and remote authorization; 0.5 optional embeddings; 1.0 after ARM64/AMD64 builds, HAOS install/backup/restore, security and resource tests. Public registry publishing pending. No private project data is bundled.
