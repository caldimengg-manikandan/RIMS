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

function Check-Environment {
    Write-Host "Checking environment health..."
    
    if (!(Test-Path ".\venv")) {
        Write-Host "Warning: No virtual environment found! Please run '.\start.ps1 repair' to set it up." -ForegroundColor Yellow
        return $false
    }

    # Get python version suffix (e.g., 313)
    try {
        $pyVersion = & ".\venv\Scripts\python.exe" -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')"
    } catch {
        Write-Host "Error: Failed to run python from venv." -ForegroundColor Red
        return $false
    }
    
    $expectedSuffix = "cp$pyVersion"

    # Scan site-packages for .pyd files (compiled extensions)
    # We check a few key packages to avoid a massive recursive scan if possible, 
    # but a general check on site-packages is most robust.
    $pydFiles = Get-ChildItem -Path ".\venv\Lib\site-packages" -Filter "*.pyd" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 20
    
    $mismatched = $pydFiles | Where-Object { $_.Name -match "cp\d+" -and $_.Name -notmatch $expectedSuffix }
    
    if ($mismatched) {
        $foundVersion = ($mismatched[0].Name -replace ".*cp(\d+).*", '$1')
        Write-Host "CRITICAL: Detected Python version mismatch in venv components!" -ForegroundColor Red
        Write-Host "Environment packages are for CP$foundVersion but you are running CP$pyVersion." -ForegroundColor Red
        Write-Host "ACTION REQUIRED: Run '.\start.ps1 repair' to fix your environment." -ForegroundColor Yellow
        return $false
    }

    Write-Host "Environment health check passed." -ForegroundColor Green
    return $true
}

function Repair-Environment {
    Write-Host "Starting environment repair... This may take several minutes." -ForegroundColor Cyan
    Stop-Backend

    if (!(Test-Path ".\requirements_core.txt")) {
        Write-Host "Generating core requirements file..."
        if (Test-Path ".\requirements.txt") {
            Get-Content requirements.txt | Where-Object { $_ -notmatch 'chromadb' } | Set-Content requirements_core.txt
        } else {
            Write-Host "Error: requirements.txt not found. Cannot proceed." -ForegroundColor Red
            return
        }
    }

    Write-Host "Cleaning up corrupted and mismatched packages..."
    Remove-Item -Path ".\venv\Lib\site-packages\~*" -Recurse -Force -ErrorAction SilentlyContinue
    
    # NEW: Delete all .pyd files that don't match the current Python version
    $pyVersion = & ".\venv\Scripts\python.exe" -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')"
    $expectedSuffix = "cp$pyVersion"
    $mismatchedPyds = Get-ChildItem -Path ".\venv\Lib\site-packages" -Filter "*.pyd" -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "cp\d+" -and $_.Name -notmatch $expectedSuffix }
    
    if ($mismatchedPyds) {
        Write-Host "Removing $($mismatchedPyds.Count) mismatched compiled extensions..." -ForegroundColor Yellow
        $mismatchedPyds | Remove-Item -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "Force-reinstalling dependencies for the current Python version..."
    & ".\venv\Scripts\python.exe" -m pip install --force-reinstall -r requirements_core.txt

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Repair complete! Your environment is now healthy." -ForegroundColor Green
    } else {
        Write-Host "Repair failed. Please check the logs above." -ForegroundColor Red
    }
}

function Start-Backend {
    if (!(Check-Environment)) {
        exit 1
    }
    
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
    "repair"  { Repair-Environment }
    "check"   { Check-Environment }
    default   { Write-Host "Usage: .\start.ps1 [start|stop|restart|repair|check]" }
}
