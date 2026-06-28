#!/bin/bash
# Generate gRPC stubs for both Python and Go from the same .proto files.
# Usage: ./scripts/generate_proto.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Paths
PROTO_DIR="$REPO_ROOT/proto"
PYTHON_OUT="$REPO_ROOT/app/gen_proto"
GO_OUT="$REPO_ROOT/go_workers/pb"

# Ensure output directories exist
mkdir -p "$PYTHON_OUT"
mkdir -p "$GO_OUT"

# Touch __init__.py for Python package
touch "$PYTHON_OUT/__init__.py"

echo "Generating protobuf stubs..."

# Find all .proto files
PROTO_FILES=$(find "$PROTO_DIR" -name "*.proto" -type f)

if [ -z "$PROTO_FILES" ]; then
    echo "No .proto files found in $PROTO_DIR"
    exit 1
fi

# Generate Python stubs
echo "Generating Python stubs..."
python -m grpc_tools.protoc \
    -I="$PROTO_DIR" \
    --python_out="$PYTHON_OUT" \
    --grpc_python_out="$PYTHON_OUT" \
    $PROTO_FILES

# Generate Go stubs
echo "Generating Go stubs..."
protoc \
    -I="$PROTO_DIR" \
    --go_out="$GO_OUT" \
    --go-grpc_out="$GO_OUT" \
    $PROTO_FILES

echo "✅ Protobuf stubs generated successfully"
echo "  Python: $PYTHON_OUT"
echo "  Go:     $GO_OUT"