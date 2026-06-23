"""
config.py — loads environment variables from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_SIGNUP_KEY: str = os.getenv("ADMIN_SIGNUP_KEY", "")
FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "./serviceAccountKey.json")
FIREBASE_CREDENTIALS_JSON: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "")

# Load CORS origins (support multiple comma-separated values)
cors_raw = os.getenv("CORS_ORIGINS", os.getenv("CORS_ORIGIN", ""))
if cors_raw:
    CORS_ORIGINS = [o.strip() for o in cors_raw.split(",") if o.strip()]
else:
    CORS_ORIGINS = ["http://localhost:5500", "http://127.0.0.1:5500"]

# Ensure local dev fallbacks are included for ease of development
if "http://localhost:5500" not in CORS_ORIGINS:
    CORS_ORIGINS.append("http://localhost:5500")
if "http://127.0.0.1:5500" not in CORS_ORIGINS:
    CORS_ORIGINS.append("http://127.0.0.1:5500")

if not ADMIN_SIGNUP_KEY:
    raise RuntimeError("ADMIN_SIGNUP_KEY is not set in environment variables.")
