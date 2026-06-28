# Sphere FX Manager API

Production‑grade backend for the Sphere FX Manager desktop application. Built on FastAPI + Go gRPC workers + MS SQL Server (with Service Broker for pub/sub). No Redis – all queuing and real‑time messaging are handled inside the database.

## Architecture Overview

- **FastAPI Gateway** – REST API, WebSocket endpoints, JWT auth, license enforcement.
- **Go Extractor** – gRPC service that parses raw Telegram text into structured trading signals using JSON pattern rules.
- **Go Backtester** – gRPC service that runs historical simulations on signals and returns performance metrics.
- **Go Live Worker** – DB consumer that polls the `jobs` table (ROWLOCK+READPAST) and executes trades via the MT5 Bridge.
- **MS SQL Server** – Primary datastore, job queue, and Service Broker for cross‑process pub/sub.
- **MT5 Bridge** – Windows VPS service that interfaces with MetaTrader 5 (Python, Windows‑only).
- **Telethon Listener** – Async Python service that ingests messages from Telegram channels.

## Quick Start

1. Copy `.env.example` to `.env` and fill in your credentials.
2. Run `docker-compose up -d` to start all Linux‑based services.
3. The FastAPI will be available at `http://localhost:8000`.
4. The MT5 Bridge must be deployed separately on a Windows VPS (see `containers/mt5_bridge/`).

## Development

- `make proto` – regenerates gRPC stubs for Python and Go from `proto/*.proto`.
- `make migrate` – runs Alembic migrations (SQL Server must be running).
- `make build-go` – compiles all Go workers.
- `make test` – runs Python and Go tests.

## Key Architectural Decisions

- **No Redis**: Service Broker provides reliable pub/sub with guaranteed delivery and transaction‑consistent ordering.
- **All Go workers are stateless** (except the Live Worker, which is a pure consumer; it never runs a gRPC server).
- **Configuration is shared** between Python and Go via `config/config.yaml`.
- **Alembic migrations** conditionally skip SQL Server‑specific DDL when running against SQLite (for tests).

## License

Proprietary – all rights reserved.