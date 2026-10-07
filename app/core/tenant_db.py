import os
from typing import Dict

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DATABASE_URL = os.getenv("DATABASE_URL_BASE", "sqlite:///./")
tenant_session_factories: Dict[str, sessionmaker] = {}


def get_tenant_database_url(tenant_id: str) -> str:
    clean_tenant_id = tenant_id.lower().replace("-", "_")
    if BASE_DATABASE_URL.startswith("sqlite"):
        return f"sqlite:///./tenant_{clean_tenant_id}.db"
    return f"{BASE_DATABASE_URL.rstrip('/')}/nexa_tenant_{clean_tenant_id}"


def get_tenant_sessionmaker(tenant_id: str):
    if tenant_id not in tenant_session_factories:
        db_url = get_tenant_database_url(tenant_id)
        try:
            engine = create_engine(db_url, pool_pre_ping=True)
            tenant_session_factories[tenant_id] = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur de connexion à la base de données du Tenant '{tenant_id}': {str(e)}",
            ) from e
    return tenant_session_factories[tenant_id]
