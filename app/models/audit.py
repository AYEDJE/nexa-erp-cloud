from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from datetime import datetime
from app.core.database import Base

class AuditLogORM(Base):
    _tablename_ = "audit_logs"

    id = column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), nullable= False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable= True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)