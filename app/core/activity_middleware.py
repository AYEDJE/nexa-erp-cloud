from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.security import get_client_ip


class ActivityTraceMiddleware(BaseHTTPMiddleware):
    """Met à jour la dernière activité et journalise les actions d'écriture authentifiées."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if response.status_code == 403 or (response.status_code < 400 and request.method in {"POST", "PUT", "PATCH", "DELETE"}):
            payload = _payload(request)
            if payload and payload.get("tenant_id") and not path.startswith("/auth"):
                try:
                    _audit(payload.get("tenant_id"), payload.get("sub"), request.method, path, response.status_code, get_client_ip(request))
                except Exception:
                    pass
        if response.status_code >= 400:
            return response
        if path.startswith("/auth") or path in {"/", "/health", "/openapi.json", "/docs", "/redoc"}:
            return response
        payload = _payload(request)
        tenant_id = payload.get("tenant_id") if payload else None
        email = payload.get("sub") if payload else None
        if not tenant_id or not email or payload.get("actor") == "super_admin":
            return response
        try:
            _trace(tenant_id, email, request.method, path, get_client_ip(request), payload.get("jti"))
        except Exception:
            return response
        return response


def _payload(request):
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(None, 1)[1]
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def _audit(tenant_id: str, email: str, method: str, path: str, status_code: int, ip_address: str) -> None:
    from app.core.tenant_db import get_tenant_sessionmaker
    from app.models.audit import AuditLogORM
    from app.models.user import UserORM

    db = get_tenant_sessionmaker(tenant_id)()
    try:
        user = db.query(UserORM).filter(UserORM.email == str(email or "").strip().lower(), UserORM.tenant_id == tenant_id).first()
        db.add(AuditLogORM(
            tenant_id=tenant_id,
            user_id=user.id if user else None,
            action="access_denied" if status_code == 403 else method,
            resource=path[:100],
            details={"status": status_code, "ip": ip_address, "email": email},
        ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _trace(tenant_id: str, email: str, method: str, path: str, ip_address: str, session_token: str = None) -> None:
    from app.core.tenant_db import get_tenant_sessionmaker
    from app.models.security import UserSessionORM
    from app.models.user import UserORM
    from app.services.access_trace import record_activity, touch_activity

    db = get_tenant_sessionmaker(tenant_id)()
    try:
        user = db.query(UserORM).filter(UserORM.email == str(email).strip().lower(), UserORM.tenant_id == tenant_id).first()
        if not user:
            return
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            record_activity(db, user, method=method, resource=path, ip_address=ip_address)
        else:
            touch_activity(db, user)
        if session_token:
            session = db.query(UserSessionORM).filter_by(tenant_id=tenant_id, session_token=session_token).first()
            if session and user.last_activity_at:
                session.last_active_at = user.last_activity_at
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
