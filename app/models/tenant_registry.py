from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String

from app.core.database import CentralBase


class CompanyRegistryORM(CentralBase):
    """Registre central: identité de l'entreprise et routage, jamais les données métier."""

    __tablename__ = "saas_companies"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(80), unique=True, index=True, nullable=False)
    company_name = Column(String(200), nullable=False)
    database_name = Column(String(120), unique=True, nullable=False)
    logical_database_name = Column(String(160), nullable=True)
    environment_code = Column(String(16), unique=True, nullable=True)
    locale = Column(String(10), nullable=False, default="fr")
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


class SaasSubscriptionORM(CentralBase):
    """Abonnement, licence et période d'essai. Aucune donnée ERP."""

    __tablename__ = "saas_subscriptions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(80), unique=True, index=True, nullable=False)
    plan = Column(String(30), nullable=False, default="trial")
    status = Column(String(30), nullable=False, default="trialing", index=True)
    licensed_users = Column(Integer, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SaasSuperAdminORM(CentralBase):
    """Super administrateur de la plateforme. Il n'appartient à aucune entreprise cliente."""

    __tablename__ = "saas_super_admins"

    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class SaasPlatformSettingORM(CentralBase):
    """Paramètres globaux: langue, sécurité, politique d'authentification."""

    __tablename__ = "saas_platform_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, index=True, nullable=False)
    value = Column(String(500), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SaasAuditLogORM(CentralBase):
    """Journal d'audit de la plateforme (pas le journal métier d'une entreprise)."""

    __tablename__ = "saas_audit_logs"

    id = Column(Integer, primary_key=True)
    actor_type = Column(String(40), nullable=False)
    actor_email = Column(String(320), nullable=True)
    action = Column(String(80), nullable=False, index=True)
    tenant_id = Column(String(80), index=True, nullable=True)
    detail = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SaasLoginEventORM(CentralBase):
    """Historique de connexion vu par la plateforme, sans contenu métier."""

    __tablename__ = "saas_login_events"

    id = Column(Integer, primary_key=True)
    email = Column(String(320), index=True, nullable=True)
    tenant_id = Column(String(80), index=True, nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    ip_address = Column(String(64), nullable=True)
    detail = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SaasAccessGrantORM(CentralBase):
    """Accès exceptionnel d'un super admin à une entreprise: limité dans le temps et audité."""

    __tablename__ = "saas_access_grants"

    id = Column(Integer, primary_key=True)
    super_admin_id = Column(Integer, index=True, nullable=False)
    tenant_id = Column(String(80), index=True, nullable=False)
    reason = Column(String(300), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
