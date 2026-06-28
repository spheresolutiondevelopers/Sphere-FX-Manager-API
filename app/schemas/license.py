"""License schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict


class LicenseActivate(BaseModel):
    license_key: str = Field(..., min_length=32)


class LicenseStatus(BaseModel):
    is_active: bool
    features: Dict[str, bool]  # feature flags
    issued_at: datetime
    expires_at: datetime