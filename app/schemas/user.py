from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UserBase(BaseModel):
    email: EmailStr
    user_type: str = "staff"


class UserCreate(UserBase):
    password: str
    tenant_id: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    user_type: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    tenant_id: str
    full_name: Optional[str] = None
    is_active: bool
    is_two_factor_enabled: bool = False
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Schémas 2FA / MFA ---
class TwoFactorSetupResponse(BaseModel):
    secret: str
    otpauth_url: str
    backup_codes: List[str]


class TwoFactorVerifyRequest(BaseModel):
    code: str
    temp_token: Optional[str] = None  # Si utilisé pendant le login


class RefreshTokenRequest(BaseModel):
    refresh_token: str
