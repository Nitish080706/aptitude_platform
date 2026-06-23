"""
question_for_test.py — Test-specific question management. All routes require admin.
Stored in Firestore under the collection 'question_for_test'.
"""
from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from firebase_admin_setup import get_firestore
from dependencies import require_admin
from models.schemas import (
    TestQuestionCreate,
    TestQuestionUpdate,
    TestQuestionOut,
    BulkTestQuestionCreate,
    BulkImportResult
)
from typing import List
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/question-for-test", tags=["Test Questions"])


@router.get("", response_model=List[TestQuestionOut])
def list_test_questions(
    topicId: str,
    admin: dict = Depends(require_admin),
):
    """List all test-specific questions for a topic (admin only)."""
    db = get_firestore()
    docs = db.collection("question_for_test").where("topicId", "==", topicId).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    # Sort by createdAt in Python
    results.sort(key=lambda x: x.get("createdAt") or 0)
    return results


@router.post("", response_model=TestQuestionOut, status_code=201)
def create_test_question(
    payload: TestQuestionCreate,
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
    db.collection("question_for_test").document(qid).set(data)
    return {**data, "id": qid, "createdAt": now, "updatedAt": now}


@router.post("/bulk", response_model=BulkImportResult, status_code=201)
def bulk_create_test_questions(
    payload: BulkTestQuestionCreate,
    admin: dict = Depends(require_admin),
):
    """
    Bulk-import multiple test questions for a topic in one request.
    Returns a summary of how many were imported vs failed.
    """
    db = get_firestore()
    imported = 0
    failed = 0
    errors: List[str] = []

    for idx, q in enumerate(payload.questions, start=1):
        try:
            qid = str(uuid.uuid4())
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
            db.collection("question_for_test").document(qid).set(data)
            imported += 1
        except Exception as e:
            failed += 1
            errors.append(f"Question {idx}: {str(e)}")

    return {"imported": imported, "failed": failed, "errors": errors}


@router.put("/{question_id}", response_model=TestQuestionOut)
def update_test_question(
    question_id: str,
    payload: TestQuestionUpdate,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    ref = db.collection("question_for_test").document(question_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Test question not found.")
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    updates["updatedAt"] = SERVER_TIMESTAMP
    ref.update(updates)
    doc = ref.get().to_dict()
    doc["id"] = question_id
    return doc


@router.delete("/{question_id}", status_code=204)
def delete_test_question(
    question_id: str,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    ref = db.collection("question_for_test").document(question_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Test question not found.")
    ref.delete()
