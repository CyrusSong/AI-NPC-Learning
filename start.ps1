$ErrorActionPreference = 'Stop'

$pythonCandidates = @((Join-Path $PSScriptRoot '.venv\Scripts\python.exe'))
$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
if ($pythonCommand -and $pythonCommand.Source -notlike '*\WindowsApps\*') {
    $pythonCandidates += $pythonCommand.Source
}
$pythonCandidates += Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'

$pythonPath = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $pythonPath) {
    Write-Error 'Python was not found. Install Python 3.10+ or create .venv in this folder.'
    exit 1
}

& $pythonPath -X utf8 (Join-Path $PSScriptRoot 'main.py') @args
exit $LASTEXITCODE

