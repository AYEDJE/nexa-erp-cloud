"""Journal des accès et notifications de sécurité multicanales."""
import json
import os
import smtplib
import urllib.error
import urllib.request
from datetime import datetime
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.models.activity import AccessLogORM, SecurityNotificationORM, SecurityPolicyORM
from app.models.user import UserORM

CHANNELS = ("email", "sms", "whatsapp", "telegram")


def record_connection(db: Session, user: UserORM, *, success: bool, ip_address: str = None, user_agent: str = None, detail: str = None) -> None:
    now = datetime.utcnow()
    if success:
        user.last_login_at = now
        user.last_login_ip = (ip_address or "")[:64] or None
        user.last_activity_at = now
    db.add(AccessLogORM(
        tenant_id=user.tenant_id,
        user_id=user.id,
        email=user.email,
        event_type="login_success" if success else "login_failure",
        occurred_at=now,
        ip_address=(ip_address or "")[:64] or None,
        user_agent=(user_agent or "")[:240] or None,
        detail=(detail or "")[:240] or None,
    ))


def record_activity(db: Session, user: UserORM, *, method: str, resource: str, ip_address: str = None) -> None:
    now = datetime.utcnow()
    previous = user.last_activity_at
    if previous is None or (now - previous).total_seconds() >= 60:
        user.last_activity_at = now
    db.add(AccessLogORM(
        tenant_id=user.tenant_id,
        user_id=user.id,
        email=user.email,
        event_type="activity",
        occurred_at=now,
        ip_address=(ip_address or "")[:64] or None,
        method=(method or "")[:12] or None,
        resource=(resource or "")[:180] or None,
    ))


def touch_activity(db: Session, user: UserORM) -> None:
    now = datetime.utcnow()
    previous = user.last_activity_at
    if previous is None or (now - previous).total_seconds() >= 60:
        user.last_activity_at = now


def ensure_policy(db: Session, tenant_id: str) -> SecurityPolicyORM:
    policy = db.query(SecurityPolicyORM).filter_by(tenant_id=tenant_id).first()
    if policy:
        return policy
    policy = SecurityPolicyORM(tenant_id=tenant_id)
    db.add(policy)
    db.flush()
    return policy


def dispatch_login_notifications(tenant_id: str, user_id: int, ip_address: str = None) -> None:
    """Envoie l'alerte de nouvelle connexion et conserve le résultat de chaque canal."""
    from app.core.database import CentralSessionLocal
    from app.core.tenant_db import get_tenant_sessionmaker
    from app.models.tenant_registry import CompanyRegistryORM

    company_name = tenant_id
    central = CentralSessionLocal()
    try:
        company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id).first()
        if company and company.company_name:
            company_name = company.company_name
    finally:
        central.close()

    db = get_tenant_sessionmaker(tenant_id)()
    try:
        user = db.query(UserORM).filter(UserORM.id == user_id, UserORM.tenant_id == tenant_id).first()
        if not user:
            return
        policy = ensure_policy(db, tenant_id)
        when = user.last_login_at or datetime.utcnow()
        message = (
            f"Nouvelle connexion à votre compte NexaERP ({company_name or tenant_id}) "
            f"le {when.strftime('%d/%m/%Y')} à {when.strftime('%H:%M')} UTC"
            + (f", depuis l'adresse {ip_address}." if ip_address else ".")
            + " Si ce n'est pas vous, changez votre mot de passe et prévenez l'administrateur de votre entreprise."
        )
        for channel in CHANNELS:
            destination, status, detail = _deliver(channel, user, policy, message)
            db.add(SecurityNotificationORM(
                tenant_id=tenant_id,
                user_id=user.id,
                email=user.email,
                channel=channel,
                destination=destination,
                status=status,
                message=message,
                provider_detail=detail,
            ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _enabled(value) -> bool:
    return True if value is None else bool(value)


def _channel_enabled(policy: SecurityPolicyORM, user: UserORM, channel: str) -> bool:
    company_on = {
        "email": policy.email_enabled,
        "sms": policy.sms_enabled,
        "whatsapp": policy.whatsapp_enabled,
        "telegram": policy.telegram_enabled,
    }[channel]
    user_on = {
        "email": user.notify_email,
        "sms": user.notify_sms,
        "whatsapp": user.notify_whatsapp,
        "telegram": user.notify_telegram,
    }[channel]
    return _enabled(company_on) and _enabled(user_on)


def _deliver(channel: str, user: UserORM, policy: SecurityPolicyORM, message: str):
    if not _channel_enabled(policy, user, channel):
        return None, "desactive", "Canal désactivé pour cette entreprise ou ce compte."
    if channel == "email":
        destination = user.email
    elif channel == "telegram":
        destination = (user.telegram_chat_id or "").strip() or None
    else:
        destination = (user.phone or "").strip() or None
    if not destination:
        return None, "destinataire_absent", "Aucun numéro ou identifiant n'est renseigné pour ce canal."
    sender = {
        "email": _send_email,
        "sms": _send_sms,
        "whatsapp": _send_whatsapp,
        "telegram": _send_telegram,
    }[channel]
    try:
        status, detail = sender(destination, message)
    except Exception as exc:
        status, detail = "echec", str(exc)[:240]
    return destination, status, detail


def _send_email(destination: str, message: str):
    host = os.getenv("SECURITY_SMTP_HOST", "").strip()
    if not host:
        return "non_configure", "Serveur SMTP non configuré (SECURITY_SMTP_HOST)."
    port = int(os.getenv("SECURITY_SMTP_PORT", "587"))
    sender = os.getenv("SECURITY_SMTP_FROM", os.getenv("SECURITY_SMTP_USER", "noreply@nexa-erp.local"))
    mail = EmailMessage()
    mail["Subject"] = "NexaERP — nouvelle connexion à votre compte"
    mail["From"] = sender
    mail["To"] = destination
    mail.set_content(message)
    with smtplib.SMTP(host, port, timeout=8) as smtp:
        if os.getenv("SECURITY_SMTP_STARTTLS", "1") != "0":
            smtp.starttls()
        user = os.getenv("SECURITY_SMTP_USER", "").strip()
        password = os.getenv("SECURITY_SMTP_PASSWORD", "")
        if user:
            smtp.login(user, password)
        smtp.send_message(mail)
    return "envoye", "Email accepté par le serveur SMTP."


def _send_sms(destination: str, message: str):
    url = os.getenv("SECURITY_SMS_WEBHOOK_URL", "").strip()
    if not url:
        return "non_configure", "Passerelle SMS non configurée (SECURITY_SMS_WEBHOOK_URL)."
    _post_json(url, {"to": destination, "text": message}, headers={})
    return "envoye", "SMS remis à la passerelle."


def _send_whatsapp(destination: str, message: str):
    token = os.getenv("WHATSAPP_TOKEN", "").strip()
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "").strip()
    if not token or not phone_id:
        return "non_configure", "WhatsApp Cloud non configuré (WHATSAPP_TOKEN, WHATSAPP_PHONE_ID)."
    _post_json(
        f"https://graph.facebook.com/v20.0/{phone_id}/messages",
        {
            "messaging_product": "whatsapp",
            "to": destination.lstrip("+"),
            "type": "text",
            "text": {"body": message},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return "envoye", "Message WhatsApp accepté."


def _send_telegram(destination: str, message: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return "non_configure", "Bot Telegram non configuré (TELEGRAM_BOT_TOKEN)."
    _post_json(
        f"https://api.telegram.org/bot{token}/sendMessage",
        {"chat_id": destination, "text": message},
        headers={},
    )
    return "envoye", "Message Telegram accepté."


def _post_json(url: str, payload: dict, headers: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status >= 300:
                raise RuntimeError(f"Le service a répondu {response.status}.")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Le service a répondu {exc.code}.") from exc
