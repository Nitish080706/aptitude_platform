"""
questions.py — Question bank management. All routes require admin.
Stored in Firestore. Edits don't retroactively re-score past attempts.
current_user is a plain dict from Firestore.
"""
from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from firebase_admin_setup import get_firestore
from dependencies import require_admin, require_authenticated
from models.schemas import QuestionCreate, QuestionUpdate, QuestionOut, BulkQuestionCreate, BulkImportResult
from typing import List, Dict, Any
from datetime import datetime, timezone
import uuid
import random

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get("", response_model=List[QuestionOut])
def list_questions(
    topicId: str,
    admin: dict = Depends(require_admin),
):
    """List all questions for a topic (admin only — includes correct answers)."""
    db = get_firestore()
    # Single where only — avoids composite index requirement.
    docs = db.collection("questions").where("topicId", "==", topicId).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    # Sort by createdAt in Python
    results.sort(key=lambda x: x.get("createdAt") or 0)
    return results


@router.get("/train", response_model=List[Dict[str, Any]])
def get_train_questions(
    topicId: str,
    shuffle: bool = True,
    user: dict = Depends(require_authenticated),
):
    """
    Return questions for a topic **without** the correctAnswer field.
    Pulls from BOTH 'questions' (general bank) AND 'question_for_test' collections
    so the train session includes every question tied to this topic.
    Intended for the Train mode — no attempt data is recorded.
    Accessible by any authenticated user (not admin-only).
    """
    db = get_firestore()
    results = []
    seen_ids: set = set()

    def extract_question(doc) -> Dict[str, Any]:
        data = doc.to_dict()
        return {
            "id":             doc.id,
            "questionText":   data.get("questionText", ""),
            "type":           data.get("type", "mcq"),
            "options":        data.get("options", []),
            "explanation":    data.get("explanation", ""),
            "difficulty":     data.get("difficulty", "medium"),
            "_correctAnswer": data.get("correctAnswer", ""),  # revealed client-side after submit
        }

    # ── Collection 1: general question bank ──────────────────────────
    for doc in db.collection("questions").where("topicId", "==", topicId).stream():
        if doc.id not in seen_ids:
            seen_ids.add(doc.id)
            results.append(extract_question(doc))

    # ── Collection 2: test-specific questions ─────────────────────────
    for doc in db.collection("question_for_test").where("topicId", "==", topicId).stream():
        if doc.id not in seen_ids:
            seen_ids.add(doc.id)
            results.append(extract_question(doc))

    if shuffle:
        random.shuffle(results)
    return results


@router.post("", response_model=QuestionOut, status_code=201)
def create_question(
    payload: QuestionCreate,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    qid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "topicId":       payload.topicId,
        "type":          payload.type,
        "questionText":  payload.questionText,
        "options":       payload.options or [],
        "correctAnswer": payload.correctAnswer,
        "explanation":   payload.explanation,
        "difficulty":    payload.difficulty,
        "createdAt":     SERVER_TIMESTAMP,
        "updatedAt":     SERVER_TIMESTAMP,
    }
    db.collection("questions").document(qid).set(data)
    return {**data, "id": qid, "createdAt": now, "updatedAt": now}


@router.post("/bulk", response_model=BulkImportResult, status_code=201)
def bulk_create_questions(
    payload: BulkQuestionCreate,
    admin: dict = Depends(require_admin),
):
    """
    Bulk-import multiple questions for a topic in one request.
    Returns a summary of how many were imported vs failed.
    """
    db = get_firestore()
    imported = 0
    failed = 0
    errors: List[str] = []

    for idx, q in enumerate(payload.questions, start=1):
        try:
            qid = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            data = {
                "topicId":       payload.topicId,
                "type":          q.type,
                "questionText":  q.questionText,
                "options":       q.options or [],
                "correctAnswer": q.correctAnswer,
                "explanation":   q.explanation,
                "difficulty":    q.difficulty,
                "createdAt":     SERVER_TIMESTAMP,
                "updatedAt":     SERVER_TIMESTAMP,
            }
            db.collection("questions").document(qid).set(data)
            imported += 1
        except Exception as e:
            failed += 1
            errors.append(f"Question {idx}: {str(e)}")

    return {"imported": imported, "failed": failed, "errors": errors}


@router.put("/{question_id}", response_model=QuestionOut)
def update_question(
    question_id: str,
    payload: QuestionUpdate,
    admin: dict = Depends(require_admin),
):
    """
    Edit a question's text, options, correct answer, or explanation.
    Past attempt scores are NOT retroactively changed.
    """
    db = get_firestore()
    ref = db.collection("questions").document(question_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Question not found.")
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    updates["updatedAt"] = SERVER_TIMESTAMP
    ref.update(updates)
    doc = ref.get().to_dict()
    doc["id"] = question_id
    return doc


@router.delete("/{question_id}", status_code=204)
def delete_question(
    question_id: str,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    ref = db.collection("questions").document(question_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Question not found.")
    ref.delete()
