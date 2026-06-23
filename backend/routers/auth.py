"""
auth.py — signup, admin signup, login, profile, and theme preference routes.

ALL user profile data lives in Firestore users/{uid}.
Firebase Auth is used for identity (UID + password).
Firestore is the source of truth for role, name, username, theme_pref.

Firestore document structure:
  users/{uid}
    name: string
    username: string
    email: string
    role: "user" | "admin"
    theme_pref: "dark" | "light"
    created_at: timestamp
"""
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from firebase_admin import auth as fb_auth
from firebase_admin_setup import get_firebase_auth, get_firestore
from models.schemas import (
    UserCreate, AdminCreate, LoginRequest,
    UserProfile, ThemeUpdate,
)
from dependencies import get_current_user
from config import ADMIN_SIGNUP_KEY

router = APIRouter(prefix="/auth", tags=["Auth"])

USERS_COL = "users"


def _build_user_dict(payload: UserCreate, role: str) -> dict:
    return {
        "name":       payload.name,
        "username":   payload.username,
        "email":      payload.email,
        "role":       role,
        "theme_pref": "dark",
        "created_at": SERVER_TIMESTAMP,
    }


def _check_uniqueness(payload: UserCreate):
    """
    Check username and email uniqueness in Firestore before creating Auth user.
    Raises 409 if either already exists.
    """
    db = get_firestore()

    # Check username
    existing_username = (
        db.collection(USERS_COL)
        .where("username", "==", payload.username)
        .limit(1)
        .get()
    )
    if existing_username:
        raise HTTPException(status_code=409, detail="Username already taken.")

    # Check email
    existing_email = (
        db.collection(USERS_COL)
        .where("email", "==", payload.email)
        .limit(1)
        .get()
    )
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already registered.")


def _create_user(payload: UserCreate, role: str) -> dict:
    """
    Step 1: Check uniqueness in Firestore.
    Step 2: Create Firebase Auth user (gets UID).
    Step 3: Write profile to Firestore users/{uid}.
    Rolls back Firebase Auth user if Firestore write fails.
    """
    _check_uniqueness(payload)

    fa = get_firebase_auth()
    db = get_firestore()

    # Create Firebase Auth user
    try:
        fb_user = fa.create_user(
            email=payload.email,
            password=payload.password,
            display_name=payload.name,
        )
    except fb_auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Email already registered.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth creation failed: {str(e)}")

    # Write to Firestore
    try:
        user_data = _build_user_dict(payload, role)
        db.collection(USERS_COL).document(fb_user.uid).set(user_data)
        return {"uid": fb_user.uid, **user_data, "created_at": None}
    except Exception as e:
        # Rollback: delete Firebase Auth user
        try:
            fa.delete_user(fb_user.uid)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Profile creation failed: {str(e)}")


@router.post("/signup", response_model=UserProfile, status_code=201)
def signup(payload: UserCreate):
    """Register a new user account (role: user)."""
    user = _create_user(payload, role="user")
    return user


@router.post("/signup/admin", response_model=UserProfile, status_code=201)
def signup_admin(payload: AdminCreate):
    """
    Register a new admin account.
    Fails with 403 if admin_key is wrong — nothing is created.
    """
    if payload.admin_key != ADMIN_SIGNUP_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key.",
        )
    user = _create_user(payload, role="admin")
    return user


@router.post("/login")
def login(payload: LoginRequest):
    """
    Verify email exists in Firebase Auth + return Firestore profile.

    Note: The actual Firebase ID token is issued client-side by the Firebase JS SDK.
    This endpoint is called after client-side sign-in to fetch the user's role/profile
    from Firestore. The frontend sends the ID token via Authorization header.
    """
    fa = get_firebase_auth()
    try:
        fb_user = fa.get_user_by_email(payload.email)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    db = get_firestore()
    doc = db.collection(USERS_COL).document(fb_user.uid).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User profile not found.")

    data = doc.to_dict()
    data["uid"] = fb_user.uid
    return {"message": "Login successful", "profile": data}


@router.get("/me", response_model=UserProfile)
def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile from Firestore."""
    return UserProfile(**current_user)


@router.patch("/theme", response_model=UserProfile)
def update_theme(
    payload: ThemeUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update the authenticated user's theme preference in Firestore."""
    db = get_firestore()
    uid = current_user["uid"]
    db.collection(USERS_COL).document(uid).update({"theme_pref": payload.theme_pref})
    current_user["theme_pref"] = payload.theme_pref
    return UserProfile(**current_user)
