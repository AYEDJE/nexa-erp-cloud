from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import Optional
from app.core.database import Base


class UserSessionORM(Base):
    """
    Gestion intelligente des sessions actives, expiration et révocation.
    """
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String, unique=True, index=True, nullable=False)  # jti ou refresh hash
    device_id = Column(String, index=True, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    os = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    location_approx = Column(String, nullable=True)  # Ville / Pays approximatif (respect de la vie privée)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("UserORM", back_populates="sessions")


class UserDeviceORM(Base):
    """
    Contrôle et gestion des appareils autorisés par utilisateur.
    """
    __tablename__ = "user_devices"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_identifier = Column(String, index=True, nullable=False)  # Empreinte unique (hash ua + specs)
    device_name = Column(String, nullable=True)                     # Ex: "Chrome sur Windows 11"
    os = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    last_ip = Column(String, nullable=True)
    status = Column(String, default="authorized")                  # "authorized", "blocked", "pending"
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserORM", back_populates="devices")


class SecurityAlertORM(Base):
    """
    Journalisation des alertes de sécurité et comportements anormaux.
    """
    __tablename__ = "security_alerts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, nullable=True)
    alert_type = Column(String, nullable=False)   # "suspicious_login", "brute_force", "unauthorized_access", "device_blocked"
    severity = Column(String, default="medium")   # "low", "medium", "high", "critical"
    ip_address = Column(String, nullable=True)
    details = Column(Text, nullable=True)         # JSON string
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# --- Schémas Pydantic ---

class SessionResponse(BaseModel):
    id: int
    user_id: int
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    location_approx: Optional[str] = None
    is_revoked: bool
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class DeviceResponse(BaseModel):
    id: int
    user_id: int
    device_identifier: str
    device_name: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    last_ip: Optional[str] = None
    status: str
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


class SecurityAlertResponse(BaseModel):
    id: int
    tenant_id: str
    user_id: Optional[int] = None
    alert_type: str
    severity: str
    ip_address: Optional[str] = None
    details: Optional[str] = None
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True
