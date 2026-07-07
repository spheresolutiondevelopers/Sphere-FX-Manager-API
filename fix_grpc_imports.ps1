# fix_grpc_imports.ps1
$files = @(
    "app/gen_proto/extractor_pb2_grpc.py",
    "app/gen_proto/backtester_pb2_grpc.py",
    "app/gen_proto/live_pb2_grpc.py"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        (Get-Content $file) -replace 'import extractor_pb2', 'from . import extractor_pb2' -replace 'import backtester_pb2', 'from . import backtester_pb2' -replace 'import live_pb2', 'from . import live_pb2' | Set-Content $file
        Write-Host "✅ Fixed $file"
    } else {
        Write-Host "⚠️ File not found: $file"
    }
}