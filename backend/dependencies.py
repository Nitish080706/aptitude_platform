"""
dependencies.py — FastAPI dependency functions for auth and role enforcement.
User profile (including role) is fetched from Firestore users/{uid}.
No SQL involved.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin_setup import get_firebase_auth, get_firestore

bearer_scheme = HTTPBearer()

# Simple dict representing an authenticated user from Firestore
# { uid, name, username, email, role, theme_pref }
UserDict = dict


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """Verify Firebase ID token and return decoded claims."""
    token = credentials.credentials
    try:
        fa = get_firebase_auth()
        decoded = fa.verify_id_token(token, clock_skew_seconds=60)
        return decoded
    except Exception as e:
        import traceback
        print(f"Token verification failed: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )


def get_current_user(token_data: dict = Depends(verify_token)) -> UserDict:
    """
    Look up the authenticated user in Firestore users/{uid}.
    Returns a plain dict with uid, name, username, email, role, theme_pref.
    """
    uid = token_data.get("uid")
    db = get_firestore()
    doc = db.collection("users").document(uid).get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found. Please sign up.",
        )

    data = doc.to_dict()
    data["uid"] = uid
    return data


def require_admin(current_user: UserDict = Depends(get_current_user)) -> UserDict:
    """Raises 403 if the authenticated user is not an admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


def require_authenticated(current_user: UserDict = Depends(get_current_user)) -> UserDict:
    """Passes for both 'user' and 'admin' roles."""
    return current_user
