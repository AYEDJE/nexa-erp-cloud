from typing import Generator, Optional
from fastapi import Header
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.tenant_db import get_tenant_sessionmaker

DATABASE_URL = "sqlite:///./erp.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> Generator:
    if x_tenant_id and x_tenant_id.strip():
        session_factory = get_tenant_sessionmaker(x_tenant_id.strip())
        db = session_factory()
    else:
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()