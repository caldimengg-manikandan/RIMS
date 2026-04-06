Set-Location $PSScriptRoot

$PORT = 10000

function Stop-Backend {
    Write-Host "Stopping backend on port $PORT..."
    $connections = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Write-Host "Backend stopped."
    } else {
        Write-Host "No backend process found on port $PORT."
    }
}

function Start-Backend {
    Write-Host "Clearing port $PORT..."
    Write-Host "Starting backend..."

    # Guard: backend must only be started via this script.
    $env:BACKEND_START_MODE = "script"

    if (Test-Path ".\venv\Scripts\Activate.ps1") {
        & ".\venv\Scripts\Activate.ps1"
    }

    # Strict single-instance check (pure guard mode: do NOT kill).
    $portInUse = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Host "Port $PORT already in use. Skipping start."
        exit 0
    }

    $proc = Start-Process -FilePath python -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info" -NoNewWindow -PassThru
    Write-Host "Backend PID: $($proc.Id)"
    Write-Host "Server running on http://0.0.0.0:$PORT"
    $proc.WaitForExit()
}

function Restart-Backend {
    Stop-Backend
    Start-Sleep -Seconds 2
    Start-Backend
}

$action = if ($args.Count -gt 0) { $args[0] } else { "start" }

switch ($action) {
    "start"   { Start-Backend }
    "stop"    { Stop-Backend }
    "restart" { Restart-Backend }
    default   { Write-Host "Usage: .\start.ps1 [start|stop|restart]" }
}
