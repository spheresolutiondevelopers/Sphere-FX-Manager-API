"""Prometheus metrics definitions and exposition."""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Response
from app.config import settings
import time
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  HTTP / API Metrics
# ──────────────────────────────────────────────────────────────

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

# ──────────────────────────────────────────────────────────────
#  Signal Extraction Metrics (Go Extractor via gRPC)
# ──────────────────────────────────────────────────────────────

signal_extraction_total = Counter(
    "signal_extraction_total",
    "Total signal extraction attempts",
    ["status"],  # success, failure, timeout
)

signal_extraction_duration_seconds = Histogram(
    "signal_extraction_duration_seconds",
    "Signal extraction duration in seconds",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

# ──────────────────────────────────────────────────────────────
#  Job Queue Metrics (MS SQL)
# ──────────────────────────────────────────────────────────────

job_queue_depth = Gauge(
    "job_queue_depth",
    "Number of pending jobs in the queue",
    ["status"],  # pending, claimed, failed, success
)

job_processing_duration_seconds = Histogram(
    "job_processing_duration_seconds",
    "Time from job creation to completion",
    buckets=(0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)

job_status_total = Counter(
    "job_status_total",
    "Total jobs by final status",
    ["status"],  # success, failed, canceled
)

# ──────────────────────────────────────────────────────────────
#  MT5 Order Metrics
# ──────────────────────────────────────────────────────────────

mt5_order_total = Counter(
    "mt5_order_total",
    "Total MT5 orders placed",
    ["status"],  # filled, rejected, timeout
)

mt5_order_duration_seconds = Histogram(
    "mt5_order_duration_seconds",
    "MT5 order execution duration in seconds",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

# ──────────────────────────────────────────────────────────────
#  License Check Metrics
# ──────────────────────────────────────────────────────────────

license_check_total = Counter(
    "license_check_total",
    "Total license validation attempts",
    ["status"],  # valid, invalid, expired
)

# ──────────────────────────────────────────────────────────────
#  WebSocket Metrics
# ──────────────────────────────────────────────────────────────

websocket_connections_current = Gauge(
    "websocket_connections_current",
    "Number of currently open WebSocket connections",
)

# ──────────────────────────────────────────────────────────────
#  gRPC Client Metrics
# ──────────────────────────────────────────────────────────────

grpc_requests_total = Counter(
    "grpc_requests_total",
    "Total gRPC requests made by FastAPI",
    ["service", "method", "status_code"],
)

grpc_request_duration_seconds = Histogram(
    "grpc_request_duration_seconds",
    "gRPC request duration in seconds",
    ["service", "method"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

# ──────────────────────────────────────────────────────────────
#  Database Metrics
# ──────────────────────────────────────────────────────────────

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Current size of the SQLAlchemy connection pool",
    ["pool_type"],  # async, sync
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],  # select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

# ──────────────────────────────────────────────────────────────
#  Init and Export Functions
# ──────────────────────────────────────────────────────────────

def init_metrics():
    """
    Initialize any metrics that need to be set at startup.
    This function is called during application startup.
    """
    # Set default values for gauges
    websocket_connections_current.set(0)
    job_queue_depth.labels(status="pending").set(0)
    job_queue_depth.labels(status="claimed").set(0)
    job_queue_depth.labels(status="failed").set(0)
    job_queue_depth.labels(status="success").set(0)
    db_connection_pool_size.labels(pool_type="async").set(0)
    db_connection_pool_size.labels(pool_type="sync").set(0)
    logger.info("Prometheus metrics initialized")


def get_metrics() -> Response:
    """
    FastAPI endpoint handler for /metrics.
    Returns the latest Prometheus metrics in plain text format.
    """
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# ──────────────────────────────────────────────────────────────
#  Helper Functions for Instrumentation
# ──────────────────────────────────────────────────────────────

def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def record_signal_extraction(status: str, duration: float):
    """Record signal extraction attempt."""
    signal_extraction_total.labels(status=status).inc()
    signal_extraction_duration_seconds.observe(duration)


def record_job_status(status: str, duration: float):
    """Record job completion status and duration."""
    job_status_total.labels(status=status).inc()
    job_processing_duration_seconds.observe(duration)


def record_mt5_order(status: str, duration: float):
    """Record MT5 order outcome."""
    mt5_order_total.labels(status=status).inc()
    mt5_order_duration_seconds.observe(duration)


def record_license_check(status: str):
    """Record license validation result."""
    license_check_total.labels(status=status).inc()


def record_grpc_request(service: str, method: str, status_code: int, duration: float):
    """Record gRPC client request."""
    grpc_requests_total.labels(service=service, method=method, status_code=str(status_code)).inc()
    grpc_request_duration_seconds.labels(service=service, method=method).observe(duration)


def record_db_query(operation: str, duration: float):
    """Record database query execution."""
    db_query_duration_seconds.labels(operation=operation).observe(duration)