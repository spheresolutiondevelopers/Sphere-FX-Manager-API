# ============================================================
#  start_all_visible.ps1  –  Start all services in visible windows
#  Reads .env file for secrets (no hardcoding)
# ============================================================

Write-Host "🚀 Starting Sphere FX Manager API Stack..." -ForegroundColor Cyan

# Get project root path
$projectRoot = Get-Location

# ------------------------------------------------------------
#  Step 1: Check if .env exists
# ------------------------------------------------------------
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found! Please create it from .env.example" -ForegroundColor Red
    Write-Host "   Location: $projectRoot\.env" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ .env file found." -ForegroundColor Green

# ------------------------------------------------------------
#  Step 2: Start FastAPI (uses .env automatically)
# ------------------------------------------------------------
Write-Host "⏳ Starting FastAPI..." -ForegroundColor Yellow
Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList @"
    cd '$projectRoot'
    Write-Host '🚀 FastAPI Server' -ForegroundColor Cyan
    Write-Host '📍 http://localhost:8000/docs' -ForegroundColor Green
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"@

Start-Sleep -Seconds 2

# ------------------------------------------------------------
#  Step 3: Start Extractor (reads config.yaml)
# ------------------------------------------------------------
Write-Host "⏳ Starting Extractor..." -ForegroundColor Yellow
Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList @"
    cd '$projectRoot\go_workers\extractor'
    Write-Host '🔌 Extractor gRPC Server' -ForegroundColor Cyan
    Write-Host '📍 localhost:50051' -ForegroundColor Green
    .\extractor.exe
"@

Start-Sleep -Seconds 1

# ------------------------------------------------------------
#  Step 4: Start Backtester (reads config.yaml)
# ------------------------------------------------------------
Write-Host "⏳ Starting Backtester..." -ForegroundColor Yellow
Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList @"
    cd '$projectRoot\go_workers\backtester'
    Write-Host '📊 Backtester gRPC Server' -ForegroundColor Cyan
    Write-Host '📍 localhost:50052' -ForegroundColor Green
    .\backtester.exe
"@

Start-Sleep -Seconds 1

# ------------------------------------------------------------
#  Step 5: Start Live Worker (reads .env automatically)
# ------------------------------------------------------------
Write-Host "⏳ Starting Live Worker..." -ForegroundColor Yellow
Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList @"
    cd '$projectRoot\go_workers\live_worker'
    Write-Host '⚡ Live Worker (DB Consumer)' -ForegroundColor Cyan
    Write-Host '📡 Polling database for jobs' -ForegroundColor Green
    .\live_worker.exe
"@

Write-Host ""
Write-Host "✅ All services started in separate windows!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Service Endpoints:" -ForegroundColor Cyan
Write-Host "   📡 FastAPI:      http://localhost:8000"
Write-Host "   📡 FastAPI Docs: http://localhost:8000/docs"
Write-Host "   📡 Extractor:    localhost:50051 (gRPC)"
Write-Host "   📡 Backtester:   localhost:50052 (gRPC)"
Write-Host "   📡 Live Worker:  polling database"
Write-Host ""
Write-Host "🔍 Check each window for logs and errors."
Write-Host "🛑 Close each window individually to stop services."