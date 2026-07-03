# ACE Post-Tool Use Hook (v0.4.1) - tracking + helper.js pattern injection
# Input: tool_type, tool_name, tool_input, tool_output, duration, transcript_path, conversation_id, generation_id

$helper = "c:\Users\ABBY\.cursor\extensions\ce-dot-net.cursor-ace-extension-0.5.2-universal/scripts/ace_search_helper.js"

$inputJson = [Console]::In.ReadToEnd()
$input = $inputJson | ConvertFrom-Json -ErrorAction SilentlyContinue

$aceDir = ".cursor\ace"
if (-not (Test-Path $aceDir)) {
    New-Item -ItemType Directory -Path $aceDir -Force | Out-Null
}

$toolType = if ($input.tool_type) { $input.tool_type } else { "unknown" }
$toolName = if ($input.tool_name) { $input.tool_name } else { "unknown" }
$toolOutput = if ($input.tool_output) { $input.tool_output.Substring(0, [Math]::Min(500, $input.tool_output.Length)) } else { "" }
$duration = if ($input.duration) { $input.duration } else { 0 }
$convId = if ($input.conversation_id) { $input.conversation_id } else { "" }
$genId = if ($input.generation_id) { $input.generation_id } else { "" }
$transcript = if ($input.transcript_path) { $input.transcript_path } else { "" }

$entry = @{event="post_tool_use"; tool_type=$toolType; tool_name=$toolName; tool_output=$toolOutput; duration=$duration; timestamp=(Get-Date -Format "o")} | ConvertTo-Json -Compress
$entry | Out-File -FilePath "$aceDir\mcp_trajectory.jsonl" -Encoding utf8 -Append

# v0.3.1 injection: only on first non-search tool of generation
if ([string]::IsNullOrEmpty($convId) -or [string]::IsNullOrEmpty($genId)) { Write-Output '{}'; exit 0 }
$flagDir = "$aceDir\sessions\$convId"
if (-not (Test-Path $flagDir)) { New-Item -ItemType Directory -Path $flagDir -Force | Out-Null }
$flagFile = "$flagDir\$genId.patterns-injected"
if (Test-Path $flagFile) { Write-Output '{}'; exit 0 }

# v0.5.0-dev.4 TASK 6 — privacy opt-in via runtime-settings.json. Legacy
# marker file removed in v0.5.0-dev.4 cleanup.
$optIn = $false
$settingsFile = "$aceDir\runtime-settings.json"
if (Test-Path $settingsFile) {
    try {
        $settings = Get-Content $settingsFile -Raw | ConvertFrom-Json
        if ($settings.shareRawPromptsForRetrievalAnalysis -eq $true) { $optIn = $true }
    } catch {}
}
if (-not $optIn) { Write-Output '{}'; exit 0 }

# If AI already called search-style tool, mark flag and skip
if ($toolName -eq "MCP:ace_search" -or $toolName -eq "ace_search") {
    New-Item -ItemType File -Path $flagFile -Force | Out-Null
    Write-Output '{}'; exit 0
}

# Read user prompt from transcript (last user message, char-truncated to 500).
$prompt = ""
if ((-not [string]::IsNullOrEmpty($transcript)) -and (Test-Path $transcript)) {
    try {
        $userLines = Get-Content -Path $transcript -ErrorAction SilentlyContinue | Where-Object { $_ -match '"role":"user"' }
        if ($userLines -and $userLines.Count -gt 0) {
            $last = $userLines[-1]
            $obj = $last | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($obj.message -and $obj.message.content) {
                $textParts = @()
                foreach ($c in $obj.message.content) {
                    if ($c.type -eq "text" -and $c.text) { $textParts += $c.text }
                }
                $prompt = ($textParts -join " ")
            } elseif ($obj.content) {
                $prompt = [string]$obj.content
            }
            if ($prompt.Length -gt 500) { $prompt = $prompt.Substring(0, 500) }
        }
    } catch {}
}
if ([string]::IsNullOrEmpty($prompt)) { Write-Output '{}'; exit 0 }

# Helper file must exist; node must be on PATH. Otherwise fail-open.
if (-not (Test-Path $helper)) { Write-Output '{}'; exit 0 }
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) { Write-Output '{}'; exit 0 }

# Spawn node with timeout. PS lacks alarm; use Wait-Process with TimeoutSec.
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "node"
$psi.ArgumentList.Add($helper)
$psi.ArgumentList.Add($prompt)
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$proc = [System.Diagnostics.Process]::Start($psi)
$patternsJson = ""
$rc = 5
if ($proc.WaitForExit(8000)) {
    $patternsJson = $proc.StandardOutput.ReadToEnd()
    $rc = $proc.ExitCode
} else {
    try { $proc.Kill() } catch {}
    $rc = 4
}

# v0.4.1 — helper exit code taxonomy (SDK team contract).
if ($rc -eq 2) {
    "auth_expired" | Out-File -FilePath "$aceDir\auth-status.txt" -Encoding utf8
    $warn = "ACE: session expired. Run /ace-login. Pattern injection paused until you re-authenticate."
    $payload = @{additional_context=$warn} | ConvertTo-Json -Compress
    Write-Output $payload
    # Caveman: do NOT touch flag — let next tool call retry once user re-logs in.
    exit 0
}

# Network/server/unknown — silently fail-open, no flag.
if ($rc -ne 0 -or [string]::IsNullOrEmpty($patternsJson) -or $patternsJson.Trim() -eq "{}") {
    Write-Output '{}'; exit 0
}

# Parse similar_patterns array.
try {
    $parsed = $patternsJson | ConvertFrom-Json -ErrorAction SilentlyContinue
} catch {
    Write-Output '{}'; exit 0
}
if (-not $parsed -or -not $parsed.similar_patterns) { Write-Output '{}'; exit 0 }

$lines = @()
foreach ($p in $parsed.similar_patterns) {
    $section = if ($p.section) { $p.section } else { "?" }
    $domain = if ($p.domain) { $p.domain } else { "?" }
    $content = if ($p.content) { $p.content } else { "?" }
    if ($content.Length -gt 200) { $content = $content.Substring(0, 200) }
    $lines += "- [$section/$domain] $content"
}
if ($lines.Count -eq 0) { Write-Output '{}'; exit 0 }

$ctxMsg = "📚 ACE patterns retrieved for: $prompt`n`n" + ($lines -join "`n") + "`n`n(Patterns auto-fetched by ACE extension. Do NOT call ace_search unless you need fresh patterns mid-task.)"
$payload = @{additional_context=$ctxMsg} | ConvertTo-Json -Compress
Write-Output $payload

# v0.4.0 plan §5.3 — flag-after-success.
New-Item -ItemType File -Path $flagFile -Force | Out-Null
