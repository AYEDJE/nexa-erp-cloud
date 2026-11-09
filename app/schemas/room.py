from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


RoomRole = Literal["owner", "admin", "member", "observer"]
InviteRole = Literal["admin", "member", "observer"]


class RoomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)


class RoomUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_archived: Optional[bool] = None


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    created_by: int
    is_archived: bool
    created_at: datetime


class InvitationCreate(BaseModel):
    email: EmailStr
    role: InviteRole = "member"


class AcceptInvitation(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class MemberRoleUpdate(BaseModel):
    role: Literal["admin", "member", "observer"]


class MemberOut(BaseModel):
    id: int
    user_id: int
    email: str
    full_name: Optional[str]
    role: RoomRole
    joined_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    user_id: int
    content: str
    created_at: datetime


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    uploaded_by: int
    original_name: str
    media_type: str
    size_bytes: int
    created_at: datetime


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    user_id: Optional[int]
    kind: str
    details: dict
    created_at: datetime