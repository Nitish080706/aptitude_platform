"""
leaderboard.py — global leaderboard endpoint.
Ranked entries stored in Firestore leaderboard/{uid}.
All user data (name, username) is denormalized into the leaderboard doc
by services/scoring.py when an attempt is submitted.
current_user is a plain dict from Firestore.
"""
from fastapi import APIRouter, Depends, Query
from firebase_admin_setup import get_firestore
from dependencies import require_authenticated
from models.schemas import LeaderboardEntry
from typing import List

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("", response_model=List[LeaderboardEntry])
def get_leaderboard(
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(require_authenticated),
):
    """
    Return the global leaderboard sorted by rank.
    Each entry includes userId, name, username, totalNormalizedScore, totalAttempts, rank.
    """
    db = get_firestore()
    docs = (
        db.collection("leaderboard")
        .order_by("rank")
        .limit(limit)
        .stream()
    )

    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append({
            "rank":                data.get("rank", 0),
            "userId":              data.get("userId", doc.id),
            "name":                data.get("name", ""),
            "username":            data.get("username", ""),
            "totalNormalizedScore":data.get("totalNormalizedScore", 0),
            "totalAttempts":       data.get("totalAttempts", 0),
        })

    return results
