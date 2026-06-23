"""
admin_dashboard.py — admin stats endpoint.
ALL data is now in Firestore (users + attempts + tests).
"""
from fastapi import APIRouter, Depends
from firebase_admin_setup import get_firestore
from dependencies import require_admin
from models.schemas import AdminStats, TestStat
from collections import defaultdict

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStats)
def get_stats(admin: dict = Depends(require_admin)):
    """
    Dashboard stats:
    - Total users: count of Firestore users collection
    - Total attempts: count of submitted attempts in Firestore
    - Avg score per test + most attempted: aggregated from Firestore attempts
    """
    db = get_firestore()

    # Total users — count Firestore users collection
    user_docs = list(db.collection("users").stream())
    total_users = len(user_docs)

    # All submitted attempts
    attempt_docs = (
        db.collection("attempts")
        .where("status", "==", "submitted")
        .stream()
    )

    total_attempts = 0
    test_scores: dict = defaultdict(list)
    test_attempt_counts: dict = defaultdict(int)

    for doc in attempt_docs:
        data = doc.to_dict()
        total_attempts += 1
        tid = data.get("testId")
        score = data.get("normalizedScore", 0)
        if tid:
            test_scores[tid].append(score)
            test_attempt_counts[tid] += 1

    # Per-test stats
    test_stats = []
    for tid, scores in test_scores.items():
        test_doc = db.collection("tests").document(tid).get()
        title = test_doc.to_dict().get("title", "Unknown") if test_doc.exists else "Unknown"
        avg = round(sum(scores) / len(scores), 2) if scores else 0
        test_stats.append(TestStat(
            testId=tid,
            testTitle=title,
            avgScore=avg,
            totalAttempts=test_attempt_counts[tid],
        ))

    test_stats.sort(key=lambda x: x.totalAttempts, reverse=True)
    most_attempted = test_stats[0] if test_stats else None

    return AdminStats(
        totalUsers=total_users,
        totalAttempts=total_attempts,
        testStats=test_stats,
        mostAttemptedTest=most_attempted,
    )
