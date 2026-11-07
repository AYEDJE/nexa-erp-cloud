"""Une seule session active par utilisateur, avec fermeture après inactivité."""
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.security import SecurityAlertORM, UserSessionORM


def idle_minutes() -> int:
    try:
        return max(0, int(os.getenv("SESSION_IDLE_MINUTES", "30")))
    except ValueError:
        return 30


def _naive(value):
    if value is None:
        return None
    if getattr(value, "tzinfo", None):
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def start_unique_session(db: Session, *, tenant_id: str, user_id: int, jti: str, device_id: str, ip_address: str, user_agent: str, os_name: str, browser: str, expires_at) -> int:
    """Ferme les sessions encore ouvertes, puis enregistre la nouvelle comme seule session autorisée."""
    now = datetime.utcnow()
    previous = db.query(UserSessionORM).filter(
        UserSessionORM.tenant_id == tenant_id,
        UserSessionORM.user_id == user_id,
        UserSessionORM.is_revoked == False,
    ).all()
    previous_ip = None
    for session in previous:
        session.is_revoked = True
        previous_ip = session.ip_address
    db.add(UserSessionORM(
        tenant_id=tenant_id,
        user_id=user_id,
        session_token=jti,
        device_id=device_id,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:500] or None,
        os=os_name,
        browser=browser,
        is_revoked=False,
        created_at=now,
        last_active_at=now,
        expires_at=_naive(expires_at) or (now + timedelta(days=30)),
    ))
    if previous:
        db.add(SecurityAlertORM(
            tenant_id=tenant_id,
            user_id=user_id,
            alert_type="session_replaced",
            severity="medium",
            ip_address=ip_address,
            details="La nouvelle connexion a fermé la session précédente.",
        ))
    if previous_ip and ip_address and previous_ip != ip_address:
        db.add(SecurityAlertORM(
            tenant_id=tenant_id,
            user_id=user_id,
            alert_type="suspicious_login",
            severity="medium",
            ip_address=ip_address,
            details=f"Connexion depuis une adresse différente ({previous_ip} puis {ip_address}).",
        ))
    return len(previous)


def assert_active_session(payload: dict) -> None:
    if payload.get("actor") == "super_admin":
        return
    if payload.get("token_type") not in (None, "access", "refresh"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton inutilisable pour cette opération. Reconnectez-vous.")
    tenant_id = payload.get("tenant_id")
    jti = payload.get("jti")
    if not tenant_id or not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session absente du jeton. Reconnectez-vous.")

    from app.core.tenant_db import get_tenant_sessionmaker

    db = get_tenant_sessionmaker(tenant_id)()
    try:
        session = db.query(UserSessionORM).filter(
            UserSessionORM.tenant_id == tenant_id,
            UserSessionORM.session_token == jti,
        ).first()
        if not session or session.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cette session a été fermée par une nouvelle connexion.",
            )
        now = datetime.utcnow()
        expires = _naive(session.expires_at)
        if expires and expires < now:
            session.is_revoked = True
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expirée. Reconnectez-vous.")
        last = _naive(session.last_active_at) or _naive(session.created_at) or now
        limit = idle_minutes()
        if limit and (now - last).total_seconds() > limit * 60:
            session.is_revoked = True
            db.add(SecurityAlertORM(
                tenant_id=tenant_id,
                user_id=session.user_id,
                alert_type="idle_timeout",
                severity="low",
                ip_address=session.ip_address,
                details=f"Session fermée après {limit} minutes sans activité.",
            ))
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Session fermée après {limit} minutes d'inactivité. Reconnectez-vous.",
            )
        if (now - last).total_seconds() >= 60:
            session.last_active_at = now
            db.commit()
    except HTTPException:
        raise
    finally:
        db.close()
