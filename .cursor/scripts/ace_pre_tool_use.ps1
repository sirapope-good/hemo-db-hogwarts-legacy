# ACE Pre-Tool Use Hook (PowerShell) — v0.5.0-dev.4 fail-open stub.
# Bash counterpart does pattern injection + updated_input rewrite via
# @ace-sdk/core helper. PS variant fail-open (Windows users skip the gate;
# manual ace_search works; MCP proxy hides ace_get_playbook + ace_learn).

$inputJson = [Console]::In.ReadToEnd()
$aceDir = ".cursor/ace"
if (-not (Test-Path $aceDir)) { New-Item -ItemType Directory -Path $aceDir -Force | Out-Null }

Write-Output '{"permission":"allow"}'
exit 0
