# DevMemory
Independent, local-first memory for development agents. Preview 0.3.0. Python 3.11+ with SQLite FTS5, no third-party runtime dependencies. No telemetry or cloud calls.

## Home Assistant OS
Add https://github.com/vorlocsev/devmemory to the app store's Repositories menu, install DevMemory, start it and open Web UI. The image is built locally (internet required to fetch Python base). HAOS acceptance pending. See [app docs](devmemory/DOCS.md).

## Standalone Docker
Set DEVMEMORY_TOKEN to a random secret of at least 32 characters in your shell or a private .env file. Run docker compose up -d --build; open http://127.0.0.1:8099 and enter the token. Port is loopback-only. Do not publish unencrypted HTTP to remote users.

## Native Python (Linux/Windows)
Set the same environment variable and run python devmemory/server.py. Default listener is loopback port 8099 and data directory is ./data. Change with --data, --host, --port; use TLS and a reviewed authentication strategy before remote deployment.

## API
GET /api/projects; POST /api/projects (slug, name); POST /api/entries (project, kind, status, title, body, optional source, sha); GET /api/entries?project=demo&q=search&offset=0 (20/page); GET /api/context?project=demo (up to 30 recent records, 32768 character budget, Markdown); POST /api/delete (project, id). Standalone API uses Authorization: Bearer <token>; POST also requires Content-Type: application/json and X-DevMemory: 1. Ingress relies on HA login and verifies supervisor peer IP. No CORS. No external API exposure in HA mode.

## Tests
python -m unittest discover -s devmemory/tests -v

## Roadmap
0.3 read-only exact-head GitHub snapshots and agent context workflow; 0.4 MCP and remote authorization; 0.5 optional embeddings; 1.0 after ARM64/AMD64 builds, HAOS install/backup/restore, security and resource tests. Public registry publishing pending. No private project data is bundled.

## Workspace
Choose Memory, Projects, Integrations or Settings. Language and appearance preferences are stored locally in the browser; the API token is held only in JavaScript memory. Ingress automatically opens the workspace, while standalone mode requires a token. GitHub and MCP are roadmap placeholders. The database schema is unchanged in 0.3.0. HAOS 0.2.1 has been exercised on ARM64; 0.3.0 device acceptance remains pending.

## Full memory backup (0.3.0)
In Settings, download a logical JSON backup of all projects and entries (maximum 4 MiB; no partial exports). SHA-256 detects accidental corruption, not authenticity. The file is not encrypted. Restore accepts only an empty DevMemory database and inserts records atomically, retaining IDs, timestamps and provenance; FTS is rebuilt. Never delete existing data merely to import a backup. For larger databases or complete app recovery, use Home Assistant backups or a stopped standalone database backup. This does not include browser preferences or authentication credentials. Physical restore remains unverified.

## GitHub integration (0.3.0 preview)
Select a project, open Integrations, enter owner/repository and save, then Sync now. Public GitHub API only: GET requests to api.github.com, no redirects, no GitHub credentials, no writes. Fetches up to five recent commits, PRs and workflow runs per sync; not exhaustive and subject to unauthenticated API rate limits. No local journal data is sent. Imported evidence describes GitHub metadata, not actual checkout SHA, hardware or acceptance verification. Duplicate identical observations are skipped; changed observations remain historical. Logical JSON backup v2 preserves imported entries and bindings. Older v1 backups from 0.2.3 can still be restored; they contain no bindings. Version 0.2.3 cannot restore v2 backups. Automatic polling and private repository access are not implemented yet.
