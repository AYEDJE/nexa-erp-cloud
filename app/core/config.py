"""Configuration centralisée de l'application NexaERP Cloud"""
import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "nexa_erp_secret_key_change_me_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
TEMP_TOKEN_EXPIRE_MINUTES = int(os.getenv("TEMP_TOKEN_EXPIRE_MINUTES", "10"))
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
SESSION_IDLE_MINUTES = int(os.getenv("SESSION_IDLE_MINUTES", "30"))

AI_PROVIDER = os.getenv("AI_PROVIDER", "huggingface").strip().lower()   # ← passage à huggingface
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()                      # non utilisé par HF mais conservé
AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")  # conservé pour compatibilité
AI_MODEL = os.getenv("AI_MODEL", "deepseek-ai/DeepSeek-V4.1-Flash")   # ← modèle cible HF
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))


HF_MODEL = os.getenv("HF_MODEL", AI_MODEL)         
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()        
HF_DEVICE = os.getenv("HF_DEVICE", "cpu")           