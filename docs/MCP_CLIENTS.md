# MCP client setup (DevMemory 0.4.2 preview)

The examples use the legacy MCP 2025 lifecycle. Physical Windows Codex read/write acceptance was reported in PR #5; Claude Code acceptance is pending. A client that insists on MCP 2026 may not connect. Never bypass TLS verification or expose the endpoint to the public internet.

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

## Windows setup wizard
After enabling managed HTTPS MCP, open DevMemory > Integrations > MCP and download the Windows setup script. Review it, then in PowerShell run `& .\Connect-DevMemory-Codex.ps1`. It prompts for the agent token without echoing, verifies HTTPS trust and performs MCP initialization, tool discovery and list_projects before registering the server with `codex mcp add`. No token is embedded in the script. Existing devmemory registration is not replaced. By default the token stays in the current PowerShell process; launch Codex from that window. Optional `-PersistToken` stores it in the Windows user environment (not a credential vault); restart clients so they inherit it. `-TestOnly` checks the endpoint without registering Codex. The script does not install certificates, bypass TLS or change execution policy. If Windows blocks it, review the script and unblock that specific downloaded file only if trusted. Physical Windows/Codex wizard and tool calls were reported successful in PR #5. Automatic instructions and physical project isolation remain unverified.

## Repository-specific memory instructions

In Integrations > MCP, choose the intended active project and download `AGENTS.md`. The file is generated locally by the browser from the exact selected project ID, without journal content or credentials. Review and merge the instructions into the repository root's existing AGENTS.md; never overwrite existing instructions blindly. The download does not change local files, Codex settings or MCP permissions. The configured MCP allowlist must separately include the project. Open a new Codex session in that repository and request work without explicitly mentioning DevMemory; verify that Codex calls the memory tools for the correct project. Do not treat the historical journal as trusted instructions. Writes require user permission and the append tool.
