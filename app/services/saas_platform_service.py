from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import CentralSessionLocal
from app.models.tenant_registry import (
    SaasAuditLogORM,
    SaasLoginEventORM,
    SaasPlatformSettingORM,
    SaasSubscriptionORM,
)

ALLOWED_PLANS = {"trial", "business", "enterprise"}
PLAN_USERS = {"trial": 3, "business": 25, "enterprise": None}
DEFAULT_SETTINGS = {
    "default_locale": "fr",
    "supported_locales": "fr,en,ar",
    "trial_days": "14",
    "auth_policy": "local_password",
    "mfa_available": "true",
}


def ensure_platform_defaults() -> None:
    db = CentralSessionLocal()
    try:
        existing = {row.key for row in db.query(SaasPlatformSettingORM).all()}
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing:
                db.add(SaasPlatformSettingORM(key=key, value=value))
        if db.new:
            db.commit()
    finally:
        db.close()


def trial_days(db: Session) -> int:
    row = db.query(SaasPlatformSettingORM).filter_by(key="trial_days").first()
    try:
        return max(int(row.value), 1) if row else 14
    except (TypeError, ValueError):
        return 14


def open_subscription(db: Session, tenant_id: str, plan: str) -> SaasSubscriptionORM:
    normalized_plan = (plan or "trial").strip().lower()
    if normalized_plan not in ALLOWED_PLANS:
        normalized_plan = "trial"
    current = db.query(SaasSubscriptionORM).filter_by(tenant_id=tenant_id).first()
    if current:
        return current
    days = trial_days(db) if normalized_plan == "trial" else 0
    current = SaasSubscriptionORM(
        tenant_id=tenant_id,
        plan=normalized_plan,
        status="trialing" if normalized_plan == "trial" else "active",
        licensed_users=PLAN_USERS[normalized_plan],
        trial_ends_at=datetime.utcnow() + timedelta(days=days) if days else None,
    )
    db.add(current)
    return current


def record_audit(actor_type: str, action: str, actor_email: str = None, tenant_id: str = None, detail: str = None) -> None:
    db = CentralSessionLocal()
    try:
        db.add(
            SaasAuditLogORM(
                actor_type=actor_type,
                actor_email=actor_email,
                action=action,
                tenant_id=tenant_id,
                detail=(detail or None) and str(detail)[:500],
            )
        )
        db.commit()
    finally:
        db.close()


def record_login_event(email: str = None, tenant_id: str = None, success: bool = False, ip_address: str = None, detail: str = None) -> None:
    db = CentralSessionLocal()
    try:
        db.add(
            SaasLoginEventORM(
                email=email,
                tenant_id=tenant_id,
                success=success,
                ip_address=ip_address,
                detail=(detail or None) and str(detail)[:200],
            )
        )
        db.commit()
    finally:
        db.close()
