from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base


class AccessLogORM(Base):
    """Connexion ou activité d'un utilisateur, conservée dans la base de son entreprise."""

    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(80), index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=True)
    email = Column(String(320), index=True, nullable=True)
    event_type = Column(String(40), index=True, nullable=False)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(240), nullable=True)
    method = Column(String(12), nullable=True)
    resource = Column(String(180), nullable=True)
    detail = Column(String(240), nullable=True)


class SecurityPolicyORM(Base):
    """Canaux de notification activés pour toute l'entreprise."""

    __tablename__ = "security_policies"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(80), unique=True, index=True, nullable=False)
    email_enabled = Column(Boolean, default=True, nullable=False)
    sms_enabled = Column(Boolean, default=True, nullable=False)
    whatsapp_enabled = Column(Boolean, default=True, nullable=False)
    telegram_enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SecurityNotificationORM(Base):
    """Suivi central des alertes de connexion, un enregistrement par canal."""

    __tablename__ = "security_notifications"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(80), index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=True)
    email = Column(String(320), nullable=True)
    channel = Column(String(20), index=True, nullable=False)
    destination = Column(String(320), nullable=True)
    status = Column(String(32), index=True, nullable=False)
    message = Column(Text, nullable=True)
    provider_detail = Column(String(240), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
