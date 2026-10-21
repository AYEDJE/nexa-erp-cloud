from sqlalchemy import create_engine, text
from app.core.database import Base
from app.core.tenant_db import BASE_DATABASE_URL, get_tenant_database_url


def provision_new_tenant(tenant_id: str):
    clean_tenant = tenant_id.lower().replace("-", "_")
    db_name = f"nexa_tenant_{clean_tenant}"

    if not BASE_DATABASE_URL.startswith("sqlite"):
        default_engine = create_engine(f"{BASE_DATABASE_URL.rstrip('/')}/postgres", isolation_level="AUTOCOMMIT")
        with default_engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            )
            if not result.scalar():
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                print(f"[OK] Base de données '{db_name}' créée avec succès.")

    tenant_db_url = get_tenant_database_url(tenant_id)
    connect_args = {"check_same_thread": False} if tenant_db_url.startswith("sqlite") else {}
    tenant_engine = create_engine(tenant_db_url, connect_args=connect_args)

    Base.metadata.create_all(bind=tenant_engine)
    print(f"[OK] Schéma de tables initialisé pour le Tenant '{tenant_id}'.")