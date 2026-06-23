"""
attempts.py — test attempt start and submit flow.
startedAt is stored server-side to prevent client clock manipulation.
Scoring, leaderboard update, and result with explanations returned on submit.
current_user is a plain dict from Firestore: {uid, name, username, email, role, ...}
"""
from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin_setup import get_firestore
from dependencies import require_authenticated
from models.schemas import (
    AttemptStartRequest, AttemptStartResponse,
    AttemptSubmitRequest, AttemptResult, AttemptHistoryItem,
)
from services.timer import validate_elapsed, elapsed_seconds
from services.scoring import score_attempt, update_leaderboard
from typing import List
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/attempts", tags=["Attempts"])


@router.post("/start", response_model=AttemptStartResponse, status_code=201)
def start_attempt(
    payload: AttemptStartRequest,
    user: dict = Depends(require_authenticated),
):
    """
    Begin a test attempt.
    Stores startedAt server-side (UTC) — this is the authoritative start time.
    Returns attemptId + startedAt + test duration so the client can show a countdown.
    """
    db = get_firestore()

    # Fetch the test
    test_doc = db.collection("tests").document(payload.testId).get()
    if not test_doc.exists:
        raise HTTPException(status_code=404, detail="Test not found.")
    test = test_doc.to_dict()

    if not test.get("isActive"):
        raise HTTPException(status_code=403, detail="Test is not active.")

    attempt_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    db.collection("attempts").document(attempt_id).set({
        "userId":    user["uid"],
        "testId":    payload.testId,
        "startedAt": started_at,
        "status":    "in_progress",
    })

    return {
        "attemptId": attempt_id,
        "startedAt": started_at.isoformat(),
        "duration":  test.get("duration", 0),
        "timerMode": test.get("timerMode", "per_test"),
    }


@router.post("/{attempt_id}/submit", response_model=AttemptResult)
def submit_attempt(
    attempt_id: str,
    payload: AttemptSubmitRequest,
    user: dict = Depends(require_authenticated),
):
    """
    Submit answers for an attempt.
    Validates server-side elapsed time. Scores answers. Updates leaderboard.
    Returns full results including explanations for wrong answers.
    """
    db = get_firestore()

    # Fetch the attempt
    attempt_ref = db.collection("attempts").document(attempt_id)
    attempt_doc = attempt_ref.get()
    if not attempt_doc.exists:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    attempt = attempt_doc.to_dict()

    if attempt.get("userId") != user["uid"]:
        raise HTTPException(status_code=403, detail="Not your attempt.")

    if attempt.get("status") == "submitted":
        raise HTTPException(status_code=409, detail="Attempt already submitted.")

    # Validate timer
    test_doc = db.collection("tests").document(attempt["testId"]).get()
    if not test_doc.exists:
        raise HTTPException(status_code=404, detail="Test not found.")
    test = test_doc.to_dict()

    started_at = attempt.get("startedAt")

    if not validate_elapsed(started_at, test.get("duration", 0)):
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Submission rejected: time limit exceeded.",
        )

    time_taken = elapsed_seconds(started_at)

    # Fetch full question data (with correctAnswer) from Firestore
    question_ids = test.get("questionIds", [])
    questions = []
    for qid in question_ids:
        qdoc = db.collection("questions").document(qid).get()
        if qdoc.exists:
            qdata = qdoc.to_dict()
            qdata["id"] = qdoc.id
            questions.append(qdata)
        else:
            qdoc_test = db.collection("question_for_test").document(qid).get()
            if qdoc_test.exists:
                qdata = qdoc_test.to_dict()
                qdata["id"] = qdoc_test.id
                questions.append(qdata)

    # Score
    answers_raw = [a.dict() for a in payload.answers]
    result = score_attempt(answers_raw, questions)

    raw_score  = result["rawScore"]
    total      = result["totalQuestions"]
    normalized = result["normalizedScore"]
    passed     = normalized >= test.get("passThreshold", 60)
    submitted_at = datetime.now(timezone.utc)

    # Update Firestore attempt doc
    attempt_ref.update({
        "submittedAt":    submitted_at,
        "status":         "submitted",
        "answers": [
            {
                "questionId":      a["questionId"],
                "selectedAnswer":  a["selectedAnswer"],
                "isCorrect":       a["isCorrect"],
                "timeTakenSeconds":a.get("timeTakenSeconds"),
            }
            for a in result["scored_answers"]
        ],
        "rawScore":        raw_score,
        "totalQuestions":  total,
        "normalizedScore": normalized,
        "passed":          passed,
    })

    # Update leaderboard (name + username from Firestore user dict)
    update_leaderboard(
        uid=user["uid"],
        name=user.get("name", ""),
        username=user.get("username", ""),
        normalized_score=normalized,
    )

    return {
        "attemptId":        attempt_id,
        "testId":           attempt["testId"],
        "rawScore":         raw_score,
        "totalQuestions":   total,
        "normalizedScore":  normalized,
        "passed":           passed,
        "timeTakenSeconds": round(time_taken, 1),
        "answers":          result["scored_answers"],
    }


@router.get("/me", response_model=List[AttemptHistoryItem])
def my_attempts(user: dict = Depends(require_authenticated)):
    """Return the current user's full attempt history."""
    db = get_firestore()
    # Single where to avoid composite index requirement.
    # Filter status and sort submittedAt in Python.
    docs = (
        db.collection("attempts")
        .where("userId", "==", user["uid"])
        .stream()
    )

    results = []
    for doc in docs:
        data = doc.to_dict()
        # Filter: only submitted attempts
        if data.get("status") != "submitted":
            continue
        test_doc = db.collection("tests").document(data.get("testId", "")).get()
        test_title = test_doc.to_dict().get("title", "Unknown") if test_doc.exists else "Unknown"
        results.append({
            "attemptId":      doc.id,
            "testId":         data.get("testId"),
            "testTitle":      test_title,
            "submittedAt":    data.get("submittedAt"),
            "rawScore":       data.get("rawScore", 0),
            "totalQuestions": data.get("totalQuestions", 0),
            "normalizedScore":data.get("normalizedScore", 0),
            "passed":         data.get("passed", False),
        })

    # Sort newest first in Python (avoids order_by composite index)
    results.sort(
        key=lambda x: x["submittedAt"] if x["submittedAt"] else 0,
        reverse=True,
    )
    return results


@router.get("/{attempt_id}")
def get_attempt_result(
    attempt_id: str,
    user: dict = Depends(require_authenticated),
):
    """Get full result for a submitted attempt (for results page)."""
    db = get_firestore()
    doc = db.collection("attempts").document(attempt_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    data = doc.to_dict()

    if data.get("userId") != user["uid"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    # Enrich answers with question text + explanation
    enriched = []
    for ans in data.get("answers", []):
        qdoc = db.collection("questions").document(ans["questionId"]).get()
        if qdoc.exists:
            q = qdoc.to_dict()
            enriched.append({
                **ans,
                "questionText":  q.get("questionText", ""),
                "correctAnswer": q.get("correctAnswer", ""),
                "explanation":   q.get("explanation", ""),
            })
        else:
            qdoc_test = db.collection("question_for_test").document(ans["questionId"]).get()
            if qdoc_test.exists:
                q = qdoc_test.to_dict()
                enriched.append({
                    **ans,
                    "questionText":  q.get("questionText", ""),
                    "correctAnswer": q.get("correctAnswer", ""),
                    "explanation":   q.get("explanation", ""),
                })
            else:
                enriched.append(ans)

    test_doc = db.collection("tests").document(data.get("testId", "")).get()
    test_title = test_doc.to_dict().get("title", "Unknown") if test_doc.exists else "Unknown"

    return {**data, "attemptId": attempt_id, "testTitle": test_title, "answers": enriched}
