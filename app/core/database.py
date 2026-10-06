from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator
from app.core.tenant_db import get_tenant_sessionmaker
DATABASE_URL = "sqlite:///./erp.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # nécessaire uniquement pour SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
   x_tenant_id: str = Header(..., alias="X-Tenant-ID") -> Generator[session, None, None]:
   if not x_tenant_id:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST
        detatil="En-tete x-Tenant-ID obligatoire"
    )
   session_factory = get_tenant_sessionmaker(x_tenant_id)
   db = session_factory()
   try:
     yield db
    finally:
        db.close()
