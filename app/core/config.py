import os

"""Configuration centralisée de l'application NexaERP Cloud."""

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
_secret_key = os.getenv("SECRET_KEY")

if not _secret_key:
    if APP_ENV in {"production", "prod"}:
        raise RuntimeError("SECRET_KEY doit être défini en production.")
    # Clé uniquement pour développement local; ne jamais réutiliser en déploiement.
    _secret_key = "dev-only-nexa-erp-secret-not-for-production"

if APP_ENV in {"production", "prod"} and len(_secret_key) < 32:
    raise RuntimeError("SECRET_KEY doit contenir au moins 32 caractères en production.")

SECRET_KEY = _secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
TEMP_TOKEN_EXPIRE_MINUTES = int(os.getenv("TEMP_TOKEN_EXPIRE_MINUTES", "10"))
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
