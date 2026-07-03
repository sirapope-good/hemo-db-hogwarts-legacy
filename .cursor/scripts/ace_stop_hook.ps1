# ACE Stop Hook - Hybrid: trajectory summary + ace_learn fallback nudge
# Primary: afterMCPExecution detects ace_learn (via rules instruction)
# Fallback: if ace_learn wasn't called, nudge the AI via followup_message
# Input: status, loop_count, transcript_path, conversation_id

$inputJson = [Console]::In.ReadToEnd()
$data = $inputJson | ConvertFrom-Json -ErrorAction SilentlyContinue
$status = $data.status
$loopCount = if ($data.loop_count) { $data.loop_count } else { 0 }
$transcriptPath = $data.transcript_path
$convId = $data.conversation_id

$aceDir = ".cursor\ace"
if (-not (Test-Path $aceDir)) { New-Item -ItemType Directory -Path $aceDir -Force | Out-Null }

# Only process completed tasks
if ($status -ne "completed") {
    Write-Output '{}'
    exit 0
}

# Aggregate trajectory — v0.2.91: count ONLY entries from current conversation.
# See bash counterpart for rationale (cross-session contamination fix).
$gitBranch = git rev-parse --abbrev-ref HEAD 2>$null
if (-not $gitBranch) { $gitBranch = "unknown" }
$gitHash = git rev-parse --short HEAD 2>$null
if (-not $gitHash) { $gitHash = "unknown" }

$mcpCount = 0; $shellCount = 0; $editCount = 0; $responseCount = 0
if ($convId) {
    $q = [char]34
    $convPattern = $q + 'conversation_id' + $q + ':' + $q + $convId + $q
    if (Test-Path "$aceDir\mcp_trajectory.jsonl") {
        $mcpCount = (Select-String -Path "$aceDir\mcp_trajectory.jsonl" -Pattern $convPattern -SimpleMatch).Count
    }
    if (Test-Path "$aceDir\shell_trajectory.jsonl") {
        $shellCount = (Select-String -Path "$aceDir\shell_trajectory.jsonl" -Pattern $convPattern -SimpleMatch).Count
    }
    if (Test-Path "$aceDir\edit_trajectory.jsonl") {
        $editCount = (Select-String -Path "$aceDir\edit_trajectory.jsonl" -Pattern $convPattern -SimpleMatch).Count
    }
    if (Test-Path "$aceDir\response_trajectory.jsonl") {
        $responseCount = (Select-String -Path "$aceDir\response_trajectory.jsonl" -Pattern $convPattern -SimpleMatch).Count
    }
}

if ($transcriptPath) {
    @{transcript_path=$transcriptPath; saved_at=(Get-Date -Format "o")} | ConvertTo-Json -Compress | Out-File -FilePath "$aceDir\last_transcript.json" -Encoding utf8
}

$summary = "MCP:$mcpCount Shell:$shellCount Edits:$editCount Responses:$responseCount"
$entry = @{event="stop"; summary=$summary; git_branch=$gitBranch; git_hash=$gitHash; timestamp=(Get-Date -Format "o")} | ConvertTo-Json -Compress
$entry | Out-File -Append -FilePath "$aceDir\ace-relevance.jsonl" -Encoding utf8

# v0.2.89: edits-only gate. Shell alone (ls /path) is exploration, not
# implementation. AI ran shell to check path missing then asked user, hook
# nudged ace_learn prematurely with success=false. See bash counterpart.
$didRealWork = $editCount -gt 0

if ($loopCount -eq 0 -and -not (Test-Path "$aceDir\ace-review-result.json") -and $didRealWork) {
    # ace_learn was NOT called and AI did productive work — nudge.
    $msg = "Now call ace_learn to capture what you learned. Start the output field with TIME_SAVED: Xm | reason (estimate minutes saved by ACE patterns, 0 if none helped)."
    Write-Output "{`"followup_message`": `"$msg`"}"
} else {
    # Either ace_learn already ran, retry loop, OR AI did nothing — stay quiet.
    Write-Output '{}'
}
