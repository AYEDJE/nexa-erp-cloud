from typing import Generator, Optional
from fastapi import Header
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./erp.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_schema_up_to_date(target_engine):
    """
    Migration automatique légère pour SQLite :
    Garantit que toutes les tables et colonnes ajoutées sont créées sur la base cible.
    """
    Base.metadata.create_all(bind=target_engine)
    try:
        with target_engine.connect() as conn:
            # Vérification et migration de la table users
            res = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            if res:
                existing_cols = [r[1] for r in res]
                new_cols = [
                    ("full_name", "TEXT"),
                    ("two_factor_secret", "TEXT"),
                    ("is_two_factor_enabled", "BOOLEAN DEFAULT 0"),
                    ("backup_codes", "TEXT"),
                    ("failed_login_attempts", "INTEGER DEFAULT 0"),
                    ("locked_until", "DATETIME"),
                    ("last_login_at", "DATETIME"),
                    ("last_login_ip", "TEXT"),
                    ("created_at", "DATETIME"),
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                conn.commit()
    except Exception:
        pass


# Migration automatique de la base par défaut
ensure_schema_up_to_date(engine)


def get_db(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> Generator:
    from app.core.tenant_db import get_tenant_sessionmaker
    if x_tenant_id and x_tenant_id.strip():
        session_factory = get_tenant_sessionmaker(x_tenant_id.strip())
        db = session_factory()
    else:
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
