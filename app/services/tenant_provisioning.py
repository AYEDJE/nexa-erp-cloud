import secrets
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, CentralSessionLocal
from app.core.tenant_db import BASE_DATABASE_URL, get_tenant_database_url, normalize_tenant_id, tenant_database_name
from app.models.company import CompanyORM
from app.models.tenant_registry import CompanyRegistryORM
from app.services.saas_platform_service import open_subscription, record_audit
from app.services.seed_rbac import seed_tenant_rbac


def _import_erp_models() -> None:
    import app.models.audit  # noqa: F401
    import app.models.company  # noqa: F401
    import app.models.invoice  # noqa: F401
    import app.models.product  # noqa: F401
    import app.models.rbac  # noqa: F401
    import app.models.security  # noqa: F401
    import app.models.user  # noqa: F401
    import app.models.warehouse  # noqa: F401
    import app.models.purchase  # noqa: F401
    import app.models.treasury  # noqa: F401
    import app.models.activity  # noqa: F401


def generate_environment_code(central) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    for _ in range(20):
        code = "".join(secrets.choice("0123456789") for _ in range(6)) + secrets.choice(alphabet)
        if not central.query(CompanyRegistryORM).filter_by(environment_code=code).first():
            return code
    raise RuntimeError("Impossible de générer un code d'environnement unique.")


def logical_database_name(tenant_id: str, environment_code: str) -> str:
    slug = tenant_id.replace("-", "_")
    return f"societe_{slug}_{environment_code}"[:160]


def initialize_tenant_base_data(
    tenant_id: str,
    company_name: str = None,
    legal_form: str = None,
    tax_id: str = None,
    activity: str = None,
) -> None:
    """Tables métier, rôles de l'équipe et fiche entreprise. Idempotent."""
    normalized = normalize_tenant_id(tenant_id)
    _import_erp_models()
    central = CentralSessionLocal()
    try:
        record = central.query(CompanyRegistryORM).filter_by(tenant_id=normalized).first()
        name = (company_name or (record.company_name if record else None) or "Entreprise").strip()[:200]
    finally:
        central.close()

    tenant_url = get_tenant_database_url(normalized)
    options = {"connect_args": {"check_same_thread": False}} if tenant_url.startswith("sqlite") else {"pool_pre_ping": True}
    tenant_engine = create_engine(tenant_url, **options)
    try:
        Base.metadata.create_all(bind=tenant_engine)
        db = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine)()
        try:
            seed_tenant_rbac(db, normalized)
            profile = db.query(CompanyORM).filter_by(tenant_id=normalized).first()
            if profile is None:
                db.add(
                    CompanyORM(
                        tenant_id=normalized,
                        name=name,
                        legal_form=(legal_form or None),
                        tax_id=(tax_id or None),
                        activity=(activity or None),
                    )
                )
                db.commit()
        finally:
            db.close()
    finally:
        tenant_engine.dispose()


def provision_new_tenant(
    tenant_id: str,
    company_name: str = "Entreprise",
    plan: str = "trial",
    legal_form: str = None,
    tax_id: str = None,
    activity: str = None,
) -> dict:
    """Crée une base métier isolée, son abonnement et les données de départ."""
    normalized = normalize_tenant_id(tenant_id)
    database_name = tenant_database_name(normalized)
    created = False
    central = CentralSessionLocal()
    try:
        record = central.query(CompanyRegistryORM).filter_by(tenant_id=normalized).first()
        if record and record.status == "active":
            if not record.environment_code:
                record.environment_code = generate_environment_code(central)
                record.logical_database_name = logical_database_name(normalized, record.environment_code)
                central.commit()
            return {
                "tenant_id": normalized,
                "database_name": record.database_name,
                "logical_database_name": record.logical_database_name,
                "environment_code": record.environment_code,
                "status": record.status,
                "created": False,
            }
        if record is None:
            code = generate_environment_code(central)
            record = CompanyRegistryORM(
                tenant_id=normalized,
                company_name=(company_name or "Entreprise").strip()[:200],
                database_name=database_name,
                logical_database_name=logical_database_name(normalized, code),
                environment_code=code,
                locale="fr",
                status="provisioning",
            )
            central.add(record)
            central.commit()

        if not BASE_DATABASE_URL.startswith("sqlite"):
            admin_url = make_url(BASE_DATABASE_URL).set(database="postgres")
            admin_engine = create_engine(str(admin_url), isolation_level="AUTOCOMMIT", pool_pre_ping=True)
            try:
                with admin_engine.connect() as conn:
                    exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database_name}).scalar()
                    if not exists:
                        conn.execute(text(f'CREATE DATABASE "{database_name}"'))
            finally:
                admin_engine.dispose()

        initialize_tenant_base_data(normalized, record.company_name, legal_form, tax_id, activity)
        open_subscription(central, normalized, plan)
        record.status = "active"
        record.activated_at = record.activated_at or datetime.utcnow()
        central.commit()
        created = True
        result = {
            "tenant_id": normalized,
            "database_name": record.database_name,
            "logical_database_name": record.logical_database_name,
            "environment_code": record.environment_code,
            "status": "active",
            "created": True,
        }
    except Exception:
        central.rollback()
        record = central.query(CompanyRegistryORM).filter_by(tenant_id=normalized).first()
        if record and record.status != "active":
            record.status = "provisioning_failed"
            central.commit()
        raise
    finally:
        central.close()

    if created:
        record_audit(
            "system",
            "environment_provisioned",
            tenant_id=normalized,
            detail=f"{result['logical_database_name']} / {result['database_name']}",
        )
    return result
