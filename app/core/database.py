import os
from typing import Generator, Optional

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import ALGORITHM, SECRET_KEY

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./erp.db")
_engine_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {"pool_pre_ping": True}
engine = create_engine(DATABASE_URL, **_engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

CENTRAL_DATABASE_URL = os.getenv("CENTRAL_DATABASE_URL", "sqlite:///./nexa_central.db")
_central_options = {"connect_args": {"check_same_thread": False}} if CENTRAL_DATABASE_URL.startswith("sqlite") else {"pool_pre_ping": True}
central_engine = create_engine(CENTRAL_DATABASE_URL, **_central_options)
CentralSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=central_engine)
CentralBase = declarative_base()


_CENTRAL_COMPANY_COLUMNS = {
    "logical_database_name": "TEXT",
    "environment_code": "TEXT",
    "locale": "TEXT DEFAULT 'fr'",
}


def ensure_central_schema():
    """Crée le registre SaaS et ajoute les colonnes manquantes d'une base centrale déjà ouverte."""
    import app.models.tenant_registry  # noqa: F401

    CentralBase.metadata.create_all(bind=central_engine)
    if central_engine.dialect.name != "sqlite":
        return
    with central_engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(saas_companies)")).fetchall()
        if not rows:
            return
        existing = {row[1] for row in rows}
        for name, sql_type in _CENTRAL_COMPANY_COLUMNS.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE saas_companies ADD COLUMN {name} {sql_type}"))


def ensure_schema_up_to_date(target_engine):
    """Crée le schéma ERP et migre les colonnes SQLite historiques connues."""
    Base.metadata.create_all(bind=target_engine)
    if target_engine.dialect.name != "sqlite":
        return
    with target_engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        if not columns:
            return
        existing = {row[1] for row in columns}
        additions = {
            "full_name": "TEXT",
            "two_factor_secret": "TEXT",
            "is_two_factor_enabled": "BOOLEAN DEFAULT 0",
            "backup_codes": "TEXT",
            "failed_login_attempts": "INTEGER DEFAULT 0",
            "locked_until": "DATETIME",
            "last_login_at": "DATETIME",
            "last_login_ip": "TEXT",
            "created_at": "DATETIME",
        }
        for name, sql_type in additions.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {sql_type}"))


def get_central_db() -> Generator:
    db = CentralSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_verified_tenant_id(request: Request) -> Optional[str]:
    authorization = request.headers.get("Authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(None, 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalide ou expiré.") from exc
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant absent du jeton.")
    return tenant_id


def get_db(request: Request) -> Generator:
    """Ouvre uniquement la base signée dans le jeton. Aucun en-tête ne choisit l'entreprise."""
    tenant_id = _get_verified_tenant_id(request)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise pour sélectionner la base de l'entreprise.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from app.models.tenant_registry import CompanyRegistryORM
    central = CentralSessionLocal()
    try:
        company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id).first()
        if not company or company.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Environnement d'entreprise inactif ou inconnu.")
    finally:
        central.close()
    from app.core.tenant_db import get_tenant_sessionmaker
    db = get_tenant_sessionmaker(tenant_id)()
    try:
        yield db
    finally:
        db.close()
