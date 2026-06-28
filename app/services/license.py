"""License validation and enforcement."""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import base64
import json

from app.config import settings


def validate_license_key(license_key: str) -> Optional[Dict[str, Any]]:
    """
    Validate an ED25519-signed license key.
    Returns the decoded payload if valid, else None.
    """
    try:
        # Split the key: signature_base64 + payload_base64
        parts = license_key.split(".")
        if len(parts) != 2:
            return None

        signature = base64.urlsafe_b64decode(parts[0] + "==")
        payload_bytes = base64.urlsafe_b64decode(parts[1] + "==")

        # Load public key from environment (base64 encoded)
        public_key_bytes = base64.urlsafe_b64decode(settings.LICENSE_PUBLIC_KEY + "==")
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)

        # Verify signature
        public_key.verify(signature, payload_bytes)

        # Parse payload
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check expiry
        expires_at = datetime.fromisoformat(payload.get("expires_at"))
        if expires_at < datetime.utcnow():
            return None

        return payload

    except (InvalidSignature, ValueError, KeyError, TypeError, base64.binascii.Error):
        return None


def check_license_active(license_key: str, user_id: int) -> bool:
    """
    Check if a license is active for a given user.
    This is a high-level function that should query the database.
    """
    # This function is meant to be called from within the database session context.
    # We'll implement the DB check in the dependency layer.
    # For now, we'll return True if validation passes.
    # The actual DB check is done in dependencies.py with the license record.
    payload = validate_license_key(license_key)
    if not payload:
        return False
    # Also ensure user_id matches payload.get("user_id")
    return payload.get("user_id") == user_id


def get_license_features(license_key: str) -> Dict[str, Any]:
    """Extract feature flags from a valid license key."""
    payload = validate_license_key(license_key)
    if not payload:
        return {}
    return payload.get("features", {})