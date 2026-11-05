import os
from typing import Generator, Optional

from fastapi import Header, HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Base métier conservée pour les modèles ERP, à provisionner dans les bases tenant.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./erp.db")
_engine_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {"pool_pre_ping": True}
engine = create_engine(DATABASE_URL, **_engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Métadonnées SaaS strictement séparées des modèles métier.
CENTRAL_DATABASE_URL = os.getenv("CENTRAL_DATABASE_URL", "sqlite:///./nexa_central.db")
_central_options = {"connect_args": {"check_same_thread": False}} if CENTRAL_DATABASE_URL.startswith("sqlite") else {"pool_pre_ping": True}
central_engine = create_engine(CENTRAL_DATABASE_URL, **_central_options)
CentralSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=central_engine)
CentralBase = declarative_base()


def ensure_schema_up_to_date(target_engine):
    """Crée le schéma métier et ajoute les colonnes SQLite historiques manquantes."""
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


def get_db(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> Generator:
    """Compatibilité historique. Les routes tenant doivent migrer vers le tenant du JWT.

    Le header est encore utilisé par les routes et tests existants; ne l'exposez pas
    comme mécanisme d'autorisation en production. Le routage JWT/registre est le
    prochain volet de migration, car l'authentification actuelle ne l'utilise pas encore.
    """
    if x_tenant_id and x_tenant_id.strip():
        from app.core.tenant_db import get_tenant_sessionmaker
        db = get_tenant_sessionmaker(x_tenant_id.strip())()
    else:
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
