from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.database import Base, CentralSessionLocal
from app.core.tenant_db import BASE_DATABASE_URL, get_tenant_database_url, normalize_tenant_id, tenant_database_name
from app.models.tenant_registry import CompanyRegistryORM


def provision_new_tenant(tenant_id: str, company_name: str = "Entreprise") -> dict:
    """Provisionne une base ERP isolée et consigne son état dans le registre central.

    La création est idempotente. PostgreSQL requiert un compte de service autorisé
    à créer des bases; SQLite est destiné au développement et aux tests.
    """
    normalized = normalize_tenant_id(tenant_id)
    database_name = tenant_database_name(normalized)
    central = CentralSessionLocal()
    try:
        record = central.query(CompanyRegistryORM).filter_by(tenant_id=normalized).first()
        if record and record.status == "active":
            return {"tenant_id": normalized, "database_name": record.database_name, "status": record.status}

        if record is None:
            record = CompanyRegistryORM(
                tenant_id=normalized,
                company_name=(company_name or "Entreprise").strip()[:200],
                database_name=database_name,
                status="provisioning",
            )
            central.add(record)
            central.commit()

        if not BASE_DATABASE_URL.startswith("sqlite"):
            admin_url = make_url(BASE_DATABASE_URL).set(database="postgres")
            admin_engine = create_engine(str(admin_url), isolation_level="AUTOCOMMIT", pool_pre_ping=True)
            try:
                # Identifiant validé par regex stricte avant interpolation SQL.
                with admin_engine.connect() as conn:
                    exists = conn.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :name"),
                        {"name": database_name},
                    ).scalar()
                    if not exists:
                        conn.execute(text(f'CREATE DATABASE "{database_name}"'))
            finally:
                admin_engine.dispose()

        tenant_url = get_tenant_database_url(normalized)
        options = {"connect_args": {"check_same_thread": False}} if tenant_url.startswith("sqlite") else {"pool_pre_ping": True}
        tenant_engine = create_engine(tenant_url, **options)
        try:
            Base.metadata.create_all(bind=tenant_engine)
        finally:
            tenant_engine.dispose()

        record.status = "active"
        central.commit()
        return {"tenant_id": normalized, "database_name": database_name, "status": "active"}
    except Exception:
        central.rollback()
        record = central.query(CompanyRegistryORM).filter_by(tenant_id=normalized).first()
        if record:
            record.status = "provisioning_failed"
            central.commit()
        raise
    finally:
        central.close()
