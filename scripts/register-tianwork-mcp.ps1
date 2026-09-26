param(
    [string]$Python = "python",
    [string]$Interpreter = "interpreter"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$bridge = Join-Path $repoRoot "integrations\tianwork_mcp.py"
$tianWorkCli = Join-Path $env:LOCALAPPDATA "TianWork\App\Cli\TianWork.Cli.exe"

if (-not (Test-Path -LiteralPath $bridge)) {
    throw "TianWork MCP bridge not found: $bridge"
}

if (-not (Test-Path -LiteralPath $tianWorkCli)) {
    throw "TianWork CLI not found: $tianWorkCli"
}

& $Python --version
if ($LASTEXITCODE -ne 0) {
    throw "Python is not available through '$Python'."
}

& $Interpreter --version
if ($LASTEXITCODE -ne 0) {
    throw "Open Interpreter is not available through '$Interpreter'."
}

$env:TIANWORK_CLI_PATH = $tianWorkCli
[Environment]::SetEnvironmentVariable("TIANWORK_CLI_PATH", $tianWorkCli, "User")

& $Interpreter mcp remove tianwork 2>$null
& $Interpreter mcp add tianwork -- $Python $bridge

Write-Host ""
Write-Host "TianWork MCP registered."
Write-Host "Verify with:"
Write-Host "  interpreter mcp get tianwork"
Write-Host "  interpreter mcp list"
