import os
from typing import Generator, Optional

from fastapi import Header, HTTPException, Request, status
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
    if payload.get("token_type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Un jeton d'accès est requis.")
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant absent du jeton.")
    return tenant_id


def get_db(request: Request, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> Generator:
    """Route vers la base identifiée par un JWT vérifié; le header n'est jamais autorité en production."""
    tenant_id = _get_verified_tenant_id(request)
    if tenant_id:
        from app.models.tenant_registry import CompanyRegistryORM
        central = CentralSessionLocal()
        try:
            company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id, status="active").first()
            if not company:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Environnement d'entreprise inactif ou inconnu.")
        finally:
            central.close()
        from app.core.tenant_db import get_tenant_sessionmaker
        db = get_tenant_sessionmaker(tenant_id)()
    else:
        # Compatibilité tests uniquement, opt-in explicite. Désactivée par défaut.
        allow_legacy = (
            os.getenv("APP_ENV", "production").lower() in {"development", "test"}
            and os.getenv("ALLOW_LEGACY_TENANT_HEADER", "false").lower() == "true"
        )
        if not allow_legacy or not x_tenant_id or not x_tenant_id.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Jeton d'accès requis pour sélectionner la base de l'entreprise.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        from app.core.tenant_db import get_tenant_sessionmaker
        db = get_tenant_sessionmaker(x_tenant_id.strip(), allow_unregistered=True)()
    try:
        yield db
    finally:
        db.close()
