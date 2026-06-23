"""
main.py — FastAPI application entry point.
Initializes Firebase (Auth + Firestore). No SQL.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from firebase_admin_setup import init_firebase

# Import routers
from routers import (
    auth,
    topics,
    notes,
    questions,
    question_for_test,
    tests,
    attempts,
    leaderboard,
    admin_dashboard,
)

# ─── App Init ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Sophía Study Platform API",
    description="Secure gateway over Firebase Auth and Firestore. All data (users + content) in Firestore.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():
    init_firebase()
    print("✅ Firebase initialized. All data in Firestore.")

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(notes.router)
app.include_router(questions.router)
app.include_router(question_for_test.router)
app.include_router(tests.router)
app.include_router(attempts.router)
app.include_router(leaderboard.router)
app.include_router(admin_dashboard.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "Sophía Study Platform"}
