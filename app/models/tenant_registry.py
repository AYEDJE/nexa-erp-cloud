from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.core.database import Base

class CompanyRegistryORM(Base):
    __tablename__ = "company_registry"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(80), unique=True, index=True, nullable=False)
    company_name = Column(String(150), nullable=False)
    domain = Column(String(100), nullable=True)
    db_name = Column(String(120), nullable=False)
    status = Column(String(30), default="pending")  # pending, active, suspended, refused
    is_trial = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TenantUserRegistryORM(Base):
    __tablename__ = "tenant_user_registry"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(80), index=True, nullable=False)
    email = Column(String(150), index=True, nullable=False)
    user_type = Column(String(50), default="admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)