import re
from typing import Dict

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

BASE_DATABASE_URL = __import__("os").getenv("DATABASE_URL", "sqlite:///./erp.db")
tenant_session_factories: Dict[str, sessionmaker] = {}
_TENANT_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,78}[a-z0-9])?$")


def normalize_tenant_id(tenant_id: str) -> str:
    value = (tenant_id or "").strip().lower().replace(" ", "-")
    if not _TENANT_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Identifiant d'entreprise invalide.")
    return value


def tenant_database_name(tenant_id: str) -> str:
    return f"nexa_tenant_{normalize_tenant_id(tenant_id).replace('-', '_')}"[:63]


def get_tenant_database_url(tenant_id: str) -> str:
    db_name = tenant_database_name(tenant_id)
    url = make_url(BASE_DATABASE_URL)
    if url.drivername.startswith("sqlite"):
        return str(url.set(database=f"{db_name}.db"))
    return str(url.set(database=db_name))


def get_tenant_sessionmaker(tenant_id: str, allow_unregistered: bool = False):
    normalized = normalize_tenant_id(tenant_id)
    if not allow_unregistered:
        from app.core.database import CentralSessionLocal
        from app.models.tenant_registry import CompanyRegistryORM
        central = CentralSessionLocal()
        try:
            record = central.query(CompanyRegistryORM).filter_by(tenant_id=normalized, status="active").first()
            if not record:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Entreprise inconnue ou inactive.")
        finally:
            central.close()

    if normalized not in tenant_session_factories:
        db_url = get_tenant_database_url(normalized)
        try:
            options = {"connect_args": {"check_same_thread": False}} if db_url.startswith("sqlite") else {"pool_pre_ping": True}
            tenant_engine = create_engine(db_url, **options)
            from app.core.database import ensure_schema_up_to_date
            ensure_schema_up_to_date(tenant_engine)
            tenant_session_factories[normalized] = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Impossible d'ouvrir la base de l'entreprise.") from exc
    return tenant_session_factories[normalized]
