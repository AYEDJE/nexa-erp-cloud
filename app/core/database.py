from typing import Generator

from fastapi import Header, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.tenant_db import get_tenant_sessionmaker

DATABASE_URL = "sqlite:///./erp.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db(x_tenant_id: str = Header(..., alias="X-Tenant-ID")) -> Generator:
    if not x_tenant_id or not x_tenant_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le header X-Tenant-ID est obligatoire pour cette action.",
        )

    session_factory = get_tenant_sessionmaker(x_tenant_id)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
