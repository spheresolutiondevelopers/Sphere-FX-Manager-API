"""Custom exception classes and FastAPI exception handlers."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)


class SphereFXError(Exception):
    """Base exception for all Sphere FX Manager errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class AuthenticationError(SphereFXError):
    """Raised when authentication fails (invalid credentials, expired token)."""

    def __init__(self, message: str = "Authentication failed", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, detail)


class AuthorizationError(SphereFXError):
    """Raised when user lacks permission for a resource or action."""

    def __init__(self, message: str = "Insufficient permissions", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, detail)


class LicenseError(SphereFXError):
    """Raised when license is invalid, expired, or insufficient features."""

    def __init__(self, message: str = "License validation failed", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, detail)


class ValidationError(SphereFXError):
    """Raised when request data fails business validation."""

    def __init__(self, message: str = "Validation failed", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, detail)


class NotFoundError(SphereFXError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, detail)


class RateLimitError(SphereFXError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS, detail)


class ConflictError(SphereFXError):
    """Raised when a duplicate or conflicting resource exists."""

    def __init__(self, message: str = "Resource conflict", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_409_CONFLICT, detail)


class ExternalServiceError(SphereFXError):
    """Raised when an external service (gRPC, MT5, Telegram) fails."""

    def __init__(self, message: str = "External service error", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_502_BAD_GATEWAY, detail)


class DatabaseError(SphereFXError):
    """Raised when a database operation fails."""

    def __init__(self, message: str = "Database error", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, detail)


# ──────────────────────────────────────────────────────────────────
#  FastAPI Exception Handlers
# ──────────────────────────────────────────────────────────────────

def _build_problem_details(
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build RFC 7807 Problem Details response body.
    """
    problem = {
        "type": f"https://api.spherefx.com/errors/{status_code}",
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    if extra:
        problem.update(extra)
    return problem


async def sphere_fx_error_handler(request: Request, exc: SphereFXError) -> JSONResponse:
    """
    Handler for all SphereFXError exceptions.
    """
    logger.warning(
        f"SphereFXError: {exc.message} (status={exc.status_code})",
        extra={"path": request.url.path, "detail": exc.detail},
    )
    body = _build_problem_details(
        status_code=exc.status_code,
        title=exc.message,
        detail=exc.detail.get("detail", exc.message),
        instance=str(request.url),
        extra=exc.detail,
    )
    return JSONResponse(status_code=exc.status_code, content=body)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for FastAPI's built-in RequestValidationError (422).
    """
    from fastapi.exceptions import RequestValidationError

    if isinstance(exc, RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "loc": ".".join(str(loc) for loc in error["loc"]),
                "msg": error["msg"],
                "type": error["type"],
            })
        body = _build_problem_details(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation Error",
            detail="Request validation failed",
            instance=str(request.url),
            extra={"errors": errors},
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body)

    # Fallback for other exceptions
    return await generic_exception_handler(request, exc)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unhandled exceptions.
    """
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=exc,
        extra={"path": request.url.path},
    )
    body = _build_problem_details(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        title="Internal Server Error",
        detail="An unexpected error occurred. Please try again later.",
        instance=str(request.url),
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for FastAPI's HTTPException.
    """
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        body = _build_problem_details(
            status_code=exc.status_code,
            title=exc.detail or "HTTP Exception",
            detail=exc.detail or "",
            instance=str(request.url),
        )
        return JSONResponse(status_code=exc.status_code, content=body)

    return await generic_exception_handler(request, exc)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI app.
    """
    # Custom SphereFXError hierarchy
    app.add_exception_handler(SphereFXError, sphere_fx_error_handler)

    # Pydantic validation errors
    from fastapi.exceptions import RequestValidationError
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # FastAPI's HTTPException
    from fastapi import HTTPException
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Catch-all for any other exception
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered")