# DevMemory 0.2.3 (preview)
After installation, Start → Open Web UI. The web UI is administrator-only via Home Assistant Ingress; no host port, Supervisor API or hardware privileges are requested. Data lives in /data/memory.sqlite3. Include the app in Home Assistant backups; for a manual file copy, stop the app first (SQLite WAL). Test restore before relying on backups. Export context includes up to 30 newest entries with a 32,768-character budget; oversized output is marked as limited. It is not a full backup. The preview permits up to eight concurrent requests and lists 20 records per page. Resource targets have not yet been measured on a Raspberry Pi.

Create a project, add entries, choose a kind and evidence status, then search within that project. Verified evidence requires a source and exact SHA; this checks fields, not source authenticity. Never store tokens or secrets. Delete removes a record from active search, not historical backups or forensic remnants.

Remote MCP, semantic search and GitHub synchronization are not implemented. Do not expose the standalone HTTP service to the internet. This preview has not yet been installed on HAOS.

## Workspace
Choose Memory, Projects, Integrations or Settings. Language and appearance preferences are stored locally in the browser; the API token is held only in JavaScript memory. Ingress automatically opens the workspace, while standalone mode requires a token. GitHub and MCP are roadmap placeholders. The database schema is unchanged in 0.2.3. HAOS 0.2.1 has been exercised on ARM64; 0.2.3 device acceptance remains pending.

## Full memory backup (0.2.3)
In Settings, download a logical JSON backup of all projects and entries (maximum 4 MiB; no partial exports). SHA-256 detects accidental corruption, not authenticity. The file is not encrypted. Restore accepts only an empty DevMemory database and inserts records atomically, retaining IDs, timestamps and provenance; FTS is rebuilt. Never delete existing data merely to import a backup. For larger databases or complete app recovery, use Home Assistant backups or a stopped standalone database backup. This does not include browser preferences or authentication credentials. Physical restore remains unverified.
