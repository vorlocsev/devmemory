# DevMemory 0.2.1 (preview)
After installation, Start → Open Web UI. The web UI is administrator-only via Home Assistant Ingress; no host port, Supervisor API or hardware privileges are requested. Data lives in /data/memory.sqlite3. Include the app in Home Assistant backups; for a manual file copy, stop the app first (SQLite WAL). Test restore before relying on backups. Export context includes up to 30 newest entries with a 32,768-character budget; oversized output is marked as limited. It is not a full backup. The preview permits up to eight concurrent requests and lists 20 records per page. Resource targets have not yet been measured on a Raspberry Pi.

Create a project, add entries, choose a kind and evidence status, then search within that project. Verified evidence requires a source and exact SHA; this checks fields, not source authenticity. Never store tokens or secrets. Delete removes a record from active search, not historical backups or forensic remnants.

Remote MCP, semantic search and GitHub synchronization are not implemented. Do not expose the standalone HTTP service to the internet. This preview has not yet been installed on HAOS.
