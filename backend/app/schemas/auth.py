from __future__ import annotations

from typing import Optional

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SetupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None
