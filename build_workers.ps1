# ============================================================
#  build_workers.ps1  –  Build all Go workers
# ============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Go worker build process..." -ForegroundColor Cyan

# ------------------------------------------------------------
#  Step 1: Ensure protoc is installed
# ------------------------------------------------------------
$protocPath = (Get-Command protoc -ErrorAction SilentlyContinue).Source
if (-not $protocPath) {
    Write-Host "❌ protoc not found. Please install it and add to PATH." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Using protoc from: $protocPath" -ForegroundColor Green
Write-Host "   version: $(protoc --version)" -ForegroundColor Green

# ------------------------------------------------------------
#  Step 2: Ensure protoc-gen-go and protoc-gen-go-grpc are installed
# ------------------------------------------------------------
$goBin = "$env:USERPROFILE\go\bin"
$plugins = @("protoc-gen-go.exe", "protoc-gen-go-grpc.exe")
$missing = $false
foreach ($p in $plugins) {
    if (-not (Test-Path "$goBin\$p")) {
        Write-Host "⚠️  Missing: $p" -ForegroundColor Yellow
        $missing = $true
    }
}
if ($missing) {
    Write-Host "⏳ Installing protoc plugins..." -ForegroundColor Yellow
    $env:GOPROXY = "https://goproxy.io,direct"
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
}
Write-Host "✅ Protoc plugins ready." -ForegroundColor Green

# ------------------------------------------------------------
#  Step 3: Regenerate protobuf stubs (with module option)
# ------------------------------------------------------------
Write-Host "⏳ Regenerating protobuf stubs..." -ForegroundColor Yellow
if (-not (Test-Path "proto\extractor.proto")) {
    Write-Host "❌ proto\extractor.proto not found. Are you in the right directory?" -ForegroundColor Red
    exit 1
}

# ★ KEY CHANGE: use --go_opt=module=sphere-fx-manager-api
protoc -Iproto --go_out=. --go_opt=module=sphere-fx-manager-api --go-grpc_out=. --go-grpc_opt=module=sphere-fx-manager-api proto/*.proto

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Protobuf generation failed." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Protobuf stubs regenerated." -ForegroundColor Green

# ------------------------------------------------------------
#  Step 4: Fix package declarations (ensure all are 'package main')
# ------------------------------------------------------------
$workers = @("extractor", "backtester", "live_worker")
foreach ($w in $workers) {
    $dir = "go_workers\$w"
    Write-Host "🔍 Checking $dir..." -ForegroundColor Yellow
    Get-ChildItem "$dir\*.go" -Exclude "main.go" | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        if ($content -match '^package\s+\w+') {
            $newContent = $content -replace '^package\s+\w+', 'package main'
            Set-Content -Path $_.FullName -Value $newContent -NoNewline
            Write-Host "   ✅ Fixed package in $($_.Name)" -ForegroundColor Green
        }
    }
}

# ------------------------------------------------------------
#  Step 5: Run go mod tidy and build each worker
# ------------------------------------------------------------
foreach ($w in $workers) {
    $dir = "go_workers\$w"
    Write-Host "🛠️  Building $w..." -ForegroundColor Yellow
    Push-Location $dir
    go mod tidy
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ go mod tidy failed in $dir" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    go build -o "$w.exe" .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed in $dir" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
    Write-Host "✅ $w.exe built successfully." -ForegroundColor Green
}

Write-Host "🎉 All workers built successfully!" -ForegroundColor Green