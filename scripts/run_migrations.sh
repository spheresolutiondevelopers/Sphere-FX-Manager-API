#!/bin/bash
# Run Alembic migrations (idempotent).
# Usage: ./scripts/run_migrations.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Set PYTHONPATH so app modules can be imported
export PYTHONPATH="$REPO_ROOT:$PYTHONPATH"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "Running Alembic migrations..."
alembic upgrade head

echo "✅ Migrations applied successfully"