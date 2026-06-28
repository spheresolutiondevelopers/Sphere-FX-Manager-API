"""Custom exceptions and FastAPI error handlers."""

from .handlers import (
    SphereFXError,
    AuthenticationError,
    AuthorizationError,
    LicenseError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    ConflictError,
    ExternalServiceError,
    DatabaseError,
    register_exception_handlers,
)

__all__ = [
    "SphereFXError",
    "AuthenticationError",
    "AuthorizationError",
    "LicenseError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "ConflictError",
    "ExternalServiceError",
    "DatabaseError",
    "register_exception_handlers",
]