# MCP client setup (DevMemory 0.4.0 preview)

The examples use the legacy MCP 2025 lifecycle. Real Codex and Claude Code acceptance is pending. A client that insists on MCP 2026 may not connect. Never bypass TLS verification or expose the endpoint to the public internet.

## Home Assistant

Enable managed HTTPS MCP using the app Configuration and Network options described in [DOCS.md](../devmemory/DOCS.md). Use actual project IDs, a separate random agent token and a trusted certificate matching the DNS hostname. Keep write access off initially.

## Codex

In the user's private Codex config.toml (not a committed repository config):

~~~toml
[mcp_servers.devmemory]
url = "https://devmemory.example.local:8100/mcp"
bearer_token_env_var = "DEVMEMORY_AGENT_TOKEN"
~~~

Set the environment variable securely in the environment where Codex runs, then restart Codex. The URL is illustrative: substitute the configured authority. Use the same variable for a local SSH tunnel endpoint where appropriate. Inspect \`codex mcp list\`; actually call list_projects and get_context to confirm access. Do not equate configuration listing with a successful connection.

## Claude Code

Use a private user-level configuration. The following JSON uses environment expansion, not a literal secret:

~~~json
{
  "mcpServers": {
    "devmemory": {
      "type": "http",
      "url": "https://devmemory.example.local:8100/mcp",
      "headers": {"Authorization": "Bearer ${DEVMEMORY_AGENT_TOKEN}"}
    }
  }
}
~~~

Set DEVMEMORY_AGENT_TOKEN in Claude Code's process environment. Check /mcp, then call list_projects and search_memory. For clients without environment expansion use their documented secret handling, not a committed token.

## Acceptance checklist

- Correct certificate trust and hostname; wrong token rejected.
- Only allowlisted projects listed or readable.
- Six read-only tools by default; add_memory absent.
- Explicit write mode only: additions remain reported, never verified.
- Restart/reconnect without exposing tokens in logs or exported memory.
- Recorded client version, transport, date and test outcome.

## References

- https://learn.chatgpt.com/docs/extend/mcp
- https://code.claude.com/docs/en/mcp
- https://pypi.org/project/mcp/1.26.0/

CI runs a pinned independent SDK client over stdio, HTTP and HTTPS. It does not certify Codex, Claude Code or physical HAOS network connectivity.
