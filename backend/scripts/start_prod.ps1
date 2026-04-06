# Production Startup Script for Windows (PowerShell)
# Maximizes backend concurrency using multi-worker Uvicorn.

Write-Host "🚀 Starting Automated Recruitment System Backend in Production Mode..." -ForegroundColor Cyan

# Ensure logs directory exists
if (!(Test-Path -Path "logs")) {
    New-Item -ItemType Directory -Path "logs"
}


# Detect CPU cores
$cores = (Get-WmiObject -Class Win32_Processor).NumberOfCores
$workers = ($cores * 2) + 1
Write-Host "📦 Scaling to $workers worker processes..." -ForegroundColor Green

# Start Uvicorn with multiple workers (Linux uses Gunicorn, Windows uses Uvicorn workers directly)
uvicorn app.main:app --host 0.0.0.0 --port 10000 --workers $workers --no-access-log --log-level info
