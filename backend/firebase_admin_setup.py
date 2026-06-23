"""
firebase_admin_setup.py — initializes Firebase Admin SDK once at startup.
ALL data (users + content) lives in Firestore. No SQL.

Collections:
  users/{uid}          — user profiles (name, username, email, role, theme_pref)
  topics/{id}          — topics
  notes/{id}           — notes per topic
  questions/{id}       — question bank
  tests/{id}           — tests
  attempts/{id}        — test attempts
  leaderboard/{uid}    — leaderboard entries
"""
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json
import base64
from config import FIREBASE_CREDENTIALS_PATH, FIREBASE_CREDENTIALS_JSON

_app = None
firestore_db = None
firebase_auth = None


def init_firebase():
    global _app, firestore_db, firebase_auth
    if not firebase_admin._apps:
        if FIREBASE_CREDENTIALS_JSON:
            try:
                # Try raw JSON first
                cred_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
            except json.JSONDecodeError:
                # Try base64 decoding
                try:
                    decoded = base64.b64decode(FIREBASE_CREDENTIALS_JSON).decode('utf-8')
                    cred_dict = json.loads(decoded)
                except Exception as e:
                    raise RuntimeError(f"FIREBASE_CREDENTIALS_JSON is set but failed to parse as JSON or Base64: {e}")
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        _app = firebase_admin.initialize_app(cred)
    else:
        _app = firebase_admin.get_app()

    firestore_db = firestore.client()
    firebase_auth = auth
    return firestore_db, firebase_auth


def get_firestore():
    if firestore_db is None:
        init_firebase()
    return firestore_db


def get_firebase_auth():
    if firebase_auth is None:
        init_firebase()
    return firebase_auth
