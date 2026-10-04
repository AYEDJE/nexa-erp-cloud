from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class AuditLogBase(BaseModel):
    action: str
    resource: str
    details: Optional[Dict[str, Any]] = None

class AuditLogCreate(AuditLogBase):
    tenant_id: str
    user_id: Optional[int] = None

class AuditLogResponse(AuditLogBase):
    id: int
    tenant_id: str
    user_id: Optional[int] = None
    created_at: datetime

    class config:
        from_attributes = True
