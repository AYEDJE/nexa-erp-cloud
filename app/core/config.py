"""Configuration centralisée de l'application NexaERP Cloud"""
import os

SECRET_KEY = os.getenv("SECRET_KEY", "nexa_erp_secret_key_change_me_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 heures