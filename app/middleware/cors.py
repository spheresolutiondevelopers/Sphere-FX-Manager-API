"""CORS middleware configuration."""

from fastapi.middleware.cors import CORSMiddleware
from app.config import settings


def setup_cors(app):
    """Configure CORS for the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
        expose_headers=settings.CORS_EXPOSE_HEADERS,
        max_age=settings.CORS_MAX_AGE,
    )