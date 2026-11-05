from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String

from app.core.database import CentralBase


class CompanyRegistryORM(CentralBase):
    """Registre central: métadonnées SaaS uniquement, sans données ERP métier."""

    __tablename__ = "saas_companies"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(80), unique=True, index=True, nullable=False)
    company_name = Column(String(200), nullable=False)
    database_name = Column(String(120), unique=True, nullable=False)
    status = Column(String(30), nullable=False, default="provisioning", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)


class TenantUserRegistryORM(CentralBase):
    """Index central minimal pour router le login vers la base de l'utilisateur."""

    __tablename__ = "saas_tenant_users"
    __table_args__ = (Index("ix_saas_tenant_user_email_tenant", "email", "tenant_id", unique=True),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(80), index=True, nullable=False)
    email = Column(String(320), index=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
