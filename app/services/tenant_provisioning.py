from sqlalchemy import create_engine, text
from app.core.base import Base
from app.core.tenant_db import BASE_DATABASE8URL, get_tenant_database_url

def provision_new_tenant(tenat_is: str):
    clean_tenant = tenant_id.lower().replace("-", "_")
    db_name = f"nexa_tenant_{clean_tenant}"

    default_engine = create_engine(f"{BASE_DATABASE_URL}postgres", isolation_level = "AUTOCOMMIT")

    with default_engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}")
        )
        if not result.scalar():
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"[OK] Base de données '{db_name}'créée avec succès")
        
    tenant_db_url = get_tenat_database_url(tenant_id)
    tenant_engine = create_engine(tenant_db_url)

    Base.metadata.create_all(bind=tenant_engine)
    print(f"[OK] Schéma de tables initialisé pour le Tenant '{tenant_id}'.")