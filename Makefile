.PHONY: help proto build-go migrate test up

SHELL := /bin/bash

help:
	@echo "Available targets:"
	@echo "  proto       - regenerate gRPC stubs for Python and Go"
	@echo "  build-go    - compile all Go workers"
	@echo "  migrate     - run Alembic migrations (SQL Server must be running)"
	@echo "  test        - run Python and Go tests"
	@echo "  up          - start all services with docker-compose"
	@echo "  down        - stop all services"

proto:
	@echo "Generating protobuf stubs..."
	@bash scripts/generate_proto.sh

build-go:
	@echo "Building Go workers..."
	@bash scripts/build_go.sh

migrate:
	@echo "Running database migrations..."
	@bash scripts/run_migrations.sh

test:
	@echo "Running Python tests..."
	pytest tests/
	@echo "Running Go tests..."
	@cd go_workers/extractor && go test ./...
	@cd go_workers/backtester && go test ./...
	@cd go_workers/live_worker && go test ./...

up:
	docker-compose up -d

down:
	docker-compose down