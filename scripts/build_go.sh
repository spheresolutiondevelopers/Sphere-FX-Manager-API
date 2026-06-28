#!/bin/bash
# Compile all Go workers.
# Usage: ./scripts/build_go.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

WORKERS=("extractor" "backtester" "live_worker")
OUTPUT_DIR="$REPO_ROOT/bin"

mkdir -p "$OUTPUT_DIR"

echo "Building Go workers..."

for worker in "${WORKERS[@]}"; do
    echo "  Building $worker..."
    cd "$REPO_ROOT/go_workers/$worker"
    CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o "$OUTPUT_DIR/$worker" .
    echo "    ✅ $OUTPUT_DIR/$worker"
done

echo "✅ All Go workers built successfully"