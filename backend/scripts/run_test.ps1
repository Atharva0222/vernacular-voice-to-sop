<#
.SYNOPSIS
    One command to test the whole loop: sets the environment, starts the server on a
    scratch database, waits for health, and runs the end-to-end checks.

.EXAMPLE
    .\scripts\run_test.ps1            # start server, run scripts\e2e.py, stop server
    .\scripts\run_test.ps1 -Manual    # start server and leave it up for the browser walkthrough
    .\scripts\run_test.ps1 -Fresh     # wipe the scratch database first
#>
[CmdletBinding()]
param(
    [int]$Port = 8001,
    [switch]$Manual,
    [switch]$Fresh,
    [switch]$Keep
)

$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
Set-Location $backend

$python = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "No virtualenv at .venv - create it and install requirements.txt" }
if (-not (Test-Path (Join-Path $backend ".env"))) { throw "No backend\.env - copy .env.example and set V2S_AUTH_SECRET" }

# The backend tolerates a missing frontend/dist (logs a warning, /preview is just
# unavailable), but this is the manual browser walkthrough, so build it if needed.
$frontendDist = Join-Path $backend "frontend\dist"
if (-not (Test-Path $frontendDist)) {
    Write-Host "frontend\dist missing - building it (one-time)..."
    Push-Location (Join-Path $backend "frontend")
    try {
        npm install
        npm run build
    } finally { Pop-Location }
}

$certs = Join-Path $backend ".venv\windows-roots.pem"
if (Test-Path $certs) {
    $env:REQUESTS_CA_BUNDLE = $certs
    $env:SSL_CERT_FILE = $certs
}

$scratch = Join-Path $env:TEMP "v2s-test"
if ($Fresh -and (Test-Path $scratch)) {
    Remove-Item -Recurse -Force $scratch
    Write-Host "wiped $scratch"
}
New-Item -ItemType Directory -Force $scratch | Out-Null
$env:V2S_TMP_DIR = $scratch
$env:V2S_DB_PATH = Join-Path $scratch "test.db"

if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "port $Port is already in use - stop that server, or pass -Port"
}

$base = "http://localhost:$Port"
$log = Join-Path $scratch "server.log"
Write-Host "starting server on $base (log: $log)"
$server = Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "$Port" `
    -WorkingDirectory $backend -PassThru -NoNewWindow `
    -RedirectStandardOutput $log -RedirectStandardError "$log.err"

function Stop-Server {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
        Write-Host "server stopped"
    }
}

try {
    $ready = $false
    foreach ($i in 1..60) {
        if ($server.HasExited) { throw "server exited early - see $log.err" }
        try {
            if ((Invoke-RestMethod "$base/api/health" -TimeoutSec 3).status -eq "ok") { $ready = $true; break }
        } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ready) { throw "server did not become healthy - see $log.err" }
    Write-Host "server healthy"

    if ($Manual) {
        Write-Host ""
        Write-Host "worker cards: $base/preview/"
        Write-Host "manager inbox: $base/preview/#/inbox"
        Write-Host "press Ctrl+C to stop"
        while (-not $server.HasExited) { Start-Sleep -Seconds 2 }
        exit 0
    }

    & $python scripts\e2e.py $base
    $code = $LASTEXITCODE
    Write-Host ""
    Write-Host $(if ($code -eq 0) { "ALL CHECKS PASSED" } else { "CHECKS FAILED (exit $code) - see $log.err" })
    exit $code
}
finally {
    if (-not $Keep) { Stop-Server } else { Write-Host "server left running at $base (pid $($server.Id))" }
}
