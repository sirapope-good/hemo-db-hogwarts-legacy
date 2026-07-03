# ACE MCP Tracking Hook - Captures tool executions for AI-Trail
# Also detects ace_learn calls and extracts task helpfulness (TIME_SAVED)
# Input: tool_name, tool_input, result_json, duration, conversation_id

$inputJson = [Console]::In.ReadToEnd()

$aceDir = ".cursor\ace"
if (-not (Test-Path $aceDir)) {
    New-Item -ItemType Directory -Path $aceDir -Force | Out-Null
}

# Parse input early so we can use conversation_id for per-conv routing.
try {
    $data = $inputJson | ConvertFrom-Json -ErrorAction SilentlyContinue
    $toolName = if ($data.tool_name) { $data.tool_name } else { "" }
    $convIdForTraj = if ($data.conversation_id) { $data.conversation_id } elseif ($data.conv_id) { $data.conv_id } else { "" }
} catch {
    $toolName = ""
    $convIdForTraj = ""
}

# v0.5.1 per-conv trajectory rotation. Mirror bash ace_track_mcp.sh logic.
if ($convIdForTraj -and $convIdForTraj -ne "null") {
    $perConvDir = "$aceDir\tasks\$convIdForTraj"
    if (-not (Test-Path $perConvDir)) {
        New-Item -ItemType Directory -Path $perConvDir -Force | Out-Null
    }
    $inputJson | Out-File -Append -FilePath "$perConvDir\mcp_trajectory.jsonl" -Encoding utf8
} else {
    $inputJson | Out-File -Append -FilePath "$aceDir\mcp_trajectory.jsonl" -Encoding utf8
}

# Detect ace_learn call — extract helpfulness from tool_input.output
if ($toolName -match "ace_learn") {
    try {
        # tool_input may be string or object
        $toolInput = $data.tool_input
        if ($toolInput -is [string]) {
            $toolInput = $toolInput | ConvertFrom-Json -ErrorAction SilentlyContinue
        }
        $outputField = if ($toolInput.output) { $toolInput.output } else { "" }
    } catch {
        $outputField = ""
    }

    # Look for TIME_SAVED: Xm | reason on the first line
    $firstLine = ($outputField -split "\n")[0]
    if ($firstLine -match "^TIME_SAVED:\s*([^|]+?)\s*(?:\|\s*(.+))?$") {
        $timeSaved = $Matches[1].Trim()
        $reason = if ($Matches[2]) { $Matches[2].Trim().Substring(0, [Math]::Min(200, $Matches[2].Trim().Length)) } else { "" }

        # Extract numeric minutes for helpful_pct
        if ($timeSaved -match "(\d+)") {
            $minutes = [int]$Matches[1]
        } else {
            $minutes = 0
        }
        # Map time to helpful %: 0m=0%, 1-4m=15%, 5-14m=30%, 15-29m=60%, 30m+=80%
        if ($minutes -ge 30) { $helpfulPct = 80 }
        elseif ($minutes -ge 15) { $helpfulPct = 60 }
        elseif ($minutes -ge 5) { $helpfulPct = 30 }
        elseif ($minutes -gt 0) { $helpfulPct = 15 }
        else { $helpfulPct = 0 }

        # Write review result (overwrites previous)
        $reviewResult = @{
            helpful_pct = $helpfulPct
            time_saved = $timeSaved
            reason = $reason
            timestamp = (Get-Date -Format "o")
        } | ConvertTo-Json -Compress
        $reviewResult | Out-File -FilePath "$aceDir\ace-review-result.json" -Encoding utf8
    }
}
