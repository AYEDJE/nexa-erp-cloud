from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    user_type: str = "staff"


class UserCreate(UserBase):
    password: str
    tenant_id: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    user_type: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    id: int
    tenant_id: str
    is_active: bool

    class Config:
        from_attributes = True