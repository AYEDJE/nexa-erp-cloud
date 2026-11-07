from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.rbac import canonical_user_type

MODULE_BY_PREFIX = (
    ("/products", "stocks"),
    ("/warehouses", "stocks"),
    ("/invoices", "facturation"),
    ("/purchases", "achats"),
    ("/treasury", "tresorerie"),
    ("/documents", "documents"),
    ("/ocr", "documents"),
    ("/company", "rh"),
    ("/users", "rh"),
    ("/admin/backups", "documents"),
    ("/audit", "rh"),
)


class ModulePermissionMiddleware(BaseHTTPMiddleware):
    """Applique le rôle de l'entreprise avant d'exécuter l'API du module."""

    async def dispatch(self, request, call_next):
        if request.method in {"OPTIONS", "HEAD"}:
            return await call_next(request)
        module = _module(request.url.path)
        if not module:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            return await call_next(request)
        try:
            _enforce(authorization.split(None, 1)[1], module, request.method)
        except PermissionError as exc:
            return JSONResponse(status_code=403, content={"detail": str(exc)})
        return await call_next(request)


def _module(path: str):
    for prefix, module in MODULE_BY_PREFIX:
        if path == prefix or path.startswith(prefix + "/"):
            return module
    return None


def _enforce(token: str, module: str, method: str) -> None:
    from jose import JWTError, jwt

    from app.core.config import ALGORITHM, SECRET_KEY
    from app.core.tenant_db import get_tenant_sessionmaker
    from app.models.rbac import PermissionORM
    from app.models.user import UserORM

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return
    if payload.get("actor") == "super_admin":
        return
    tenant_id = payload.get("tenant_id")
    email = str(payload.get("sub") or "").strip().lower()
    if not tenant_id or not email:
        return
    if canonical_user_type(payload.get("user_type")) in {"admin", "super_admin"}:
        return
    db = get_tenant_sessionmaker(tenant_id)()
    try:
        user = db.query(UserORM).filter(UserORM.email == email, UserORM.tenant_id == tenant_id).first()
        if not user or canonical_user_type(user.user_type) in {"admin", "super_admin"} or not user.role_id:
            return
        permission = db.query(PermissionORM).filter_by(role_id=user.role_id, module_name=module).first()
        writing = method not in {"GET", "OPTIONS", "HEAD"}
        allowed = False
        if permission:
            allowed = bool(permission.can_create or permission.can_update or permission.can_delete or permission.can_validate) if writing else bool(permission.can_read)
        if not allowed:
            raise PermissionError(f"Le rôle de ce compte n'autorise pas cette opération sur le module « {module} ».")
    finally:
        db.close()
