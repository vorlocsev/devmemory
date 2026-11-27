# DevMemory 0.4.0 - Windows PowerShell 5.1 / PowerShell 7
# Review before running. No administrator rights required.
param([string]$Url = '__DEVMEMORY_URL__', [switch]$TestOnly, [switch]$PersistToken)
$ErrorActionPreference = 'Stop'
if (-not $Url -or $Url -eq '__DEVMEMORY_URL__') {
    $Url = Read-Host 'DevMemory HTTPS MCP URL'
}
$uri = [Uri]$Url
if (-not $uri.IsAbsoluteUri -or $uri.Scheme -ne 'https' -or $uri.UserInfo -or $uri.Query -or $uri.Fragment -or $uri.AbsolutePath -cne '/mcp') {
    throw 'Expected https://host:port/mcp (no credentials or query)'
}
Write-Host ('Target: ' + $uri.AbsoluteUri)
if ((Read-Host 'Verify this address, then type YES to continue') -cne 'YES') { return }
if (-not $TestOnly) {
    $null = Get-Command codex -ErrorAction Stop
    $raw = & codex mcp list --json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Codex MCP configuration' }
    $servers = ConvertFrom-Json -InputObject ($raw -join [Environment]::NewLine)
    foreach ($server in @($servers)) {
        if ($null -eq $server -or -not $server.PSObject.Properties['name']) { throw 'Unexpected Codex MCP list response' }
        if ($server.name -eq 'devmemory') { throw 'DevMemory is already registered. Inspect it using codex mcp get devmemory; no changes made.' }
    }
}
$secure = Read-Host 'Paste the DevMemory agent token (input hidden)' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr); $secure.Dispose() }
if ($token -cnotmatch '^[A-Za-z0-9_-]{32,256}$') { throw 'Invalid agent token format' }
Add-Type -AssemblyName System.Net.Http
$handler = New-Object System.Net.Http.HttpClientHandler
$handler.AllowAutoRedirect = $false
$handler.UseProxy = $false
$client = New-Object System.Net.Http.HttpClient($handler)
$client.Timeout = [TimeSpan]::FromSeconds(15)
$client.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue('Bearer', $token)
$client.DefaultRequestHeaders.Accept.ParseAdd('application/json')
$client.DefaultRequestHeaders.Accept.ParseAdd('text/event-stream')
$session = $null
function Send-Mcp([string]$Method, $Payload, [string]$SessionId, [string]$Version) {
    $request = New-Object System.Net.Http.HttpRequestMessage((New-Object System.Net.Http.HttpMethod($Method)), $uri)
    try {
        if ($SessionId) { $request.Headers.Add('Mcp-Session-Id', $SessionId) }
        if ($Version) { $request.Headers.Add('MCP-Protocol-Version', $Version) }
        if ($null -ne $Payload) {
            $request.Content = New-Object System.Net.Http.StringContent(($Payload | ConvertTo-Json -Depth 12 -Compress), [Text.Encoding]::UTF8, 'application/json')
        }
        $response = $client.SendAsync($request).GetAwaiter().GetResult()
        try {
            $status = [int]$response.StatusCode
            if ($status -notin @(200,202,204)) { throw "MCP HTTP $status. Check token, host, port and app settings." }
            $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            $sid = if ($response.Headers.Contains('Mcp-Session-Id')) { @($response.Headers.GetValues('Mcp-Session-Id'))[0] } else { $null }
            $json = if ($body) { ConvertFrom-Json -InputObject $body } else { $null }
            if ($json -and $json.error) { throw 'MCP JSON-RPC request rejected' }
            return @{ Status=$status; Session=$sid; Json=$json }
        } finally { $response.Dispose() }
    } finally { $request.Dispose() }
}
$version = '2025-11-25'
try {
    $init = Send-Mcp 'POST' @{jsonrpc='2.0';id=1;method='initialize';params=@{protocolVersion=$version;capabilities=@{};clientInfo=@{name='devmemory-windows-setup';version='0.4.0'}}} '' ''
    $session = $init.Session
    if ($session -cnotmatch '^[A-Za-z0-9_-]{43}$' -or $init.Json.result.serverInfo.name -cne 'devmemory' -or $init.Json.result.protocolVersion -cne $version) { throw 'Unexpected MCP server or protocol' }
    $null = Send-Mcp 'POST' @{jsonrpc='2.0';method='notifications/initialized'} $session $version
    $result = Send-Mcp 'POST' @{jsonrpc='2.0';id=2;method='tools/list'} $session $version
    if ('list_projects' -notin @($result.Json.result.tools | ForEach-Object {$_.name})) { throw 'Missing DevMemory tools' }
    $result = Send-Mcp 'POST' @{jsonrpc='2.0';id=3;method='tools/call';params=@{name='list_projects';arguments=@{}}} $session $version
    if ($result.Json.result.isError -ne $false) { throw 'Cannot read permitted projects' }
    Write-Host 'PASS: trusted HTTPS, agent authentication, MCP handshake, tools/list and list_projects.'
    if (-not $TestOnly) {
        & codex mcp add devmemory --url $uri.AbsoluteUri --bearer-token-env-var DEVMEMORY_AGENT_TOKEN
        if ($LASTEXITCODE -ne 0) { throw 'Codex registration failed' }
        $env:DEVMEMORY_AGENT_TOKEN = $token
        if ($PersistToken) {
            [Environment]::SetEnvironmentVariable('DEVMEMORY_AGENT_TOKEN',$token,'User')
            Write-Host 'Token saved as a Windows user environment variable; readable by processes under your account.'
        } else {
            Write-Host 'Token is available only in this PowerShell process. Start Codex from this window.'
        }
        Write-Host 'Codex registration complete. Start a new Codex session and ask it to call list_projects.'
    }
} finally {
    if ($session -cmatch '^[A-Za-z0-9_-]{43}$') {
        try { $null = Send-Mcp 'DELETE' $null $session $version } catch { }
    }
    $client.Dispose()
    $token = $null
}
