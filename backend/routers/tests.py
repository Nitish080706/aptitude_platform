"""
tests.py — Test management. Stored in Firestore.
Users see only active tests. correctAnswer is stripped from question data for users.
current_user is a plain dict from Firestore.
"""
from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from firebase_admin_setup import get_firestore
from dependencies import require_admin, require_authenticated
from models.schemas import TestCreate, TestUpdate, TestOut
from typing import List
import uuid

router = APIRouter(prefix="/tests", tags=["Tests"])


def _strip_answers(questions: List[dict]) -> List[dict]:
    """Remove correctAnswer and explanation from question dicts before sending to users."""
    safe_keys = {"id", "topicId", "type", "questionText", "options", "difficulty"}
    return [{k: v for k, v in q.items() if k in safe_keys} for q in questions]


def _enrich_test(doc_id: str, data: dict, role: str, db) -> dict:
    """Attach full (or stripped) question details to a test dict."""
    question_ids = data.get("questionIds", [])
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

    if role != "admin":
        questions = _strip_answers(questions)

    data["id"] = doc_id
    data["questions"] = questions
    return data


@router.get("", response_model=List[TestOut])
def list_tests(user: dict = Depends(require_authenticated)):
    """
    List tests.
    Users see only isActive=true tests.
    Admins see all tests.
    """
    db = get_firestore()
    col = db.collection("tests")
    if user.get("role") != "admin":
        col = col.where("isActive", "==", True)

    docs = col.stream()          # no .order_by() — avoids composite index requirement
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    # Sort by createdAt in Python (same pattern as list_questions)
    results.sort(key=lambda x: x.get("createdAt") or 0)
    return results


@router.get("/{test_id}")
def get_test(test_id: str, user: dict = Depends(require_authenticated)):
    """
    Get a single test with embedded question data.
    correctAnswer and explanation are stripped for non-admin users.
    """
    db = get_firestore()
    ref = db.collection("tests").document(test_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Test not found.")

    data = doc.to_dict()
    if user.get("role") != "admin" and not data.get("isActive"):
        raise HTTPException(status_code=404, detail="Test not found.")

    return _enrich_test(test_id, data, user.get("role", "user"), db)


@router.post("", response_model=TestOut, status_code=201)
def create_test(
    payload: TestCreate,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    tid = str(uuid.uuid4())
    data = {
        "title":         payload.title,
        "type":          payload.type,
        "topicId":       payload.topicId,
        "questionIds":   payload.questionIds,
        "timerMode":     payload.timerMode,
        "duration":      payload.duration,
        "passThreshold": payload.passThreshold,
        "isActive":      payload.isActive,
        "createdBy":     admin["uid"],
        "createdAt":     SERVER_TIMESTAMP,
    }
    db.collection("tests").document(tid).set(data)
    return {**data, "id": tid, "createdAt": None}


@router.put("/{test_id}", response_model=TestOut)
def update_test(
    test_id: str,
    payload: TestUpdate,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    ref = db.collection("tests").document(test_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Test not found.")
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    ref.update(updates)
    doc = ref.get().to_dict()
    doc["id"] = test_id
    return doc


@router.patch("/{test_id}/activate", response_model=TestOut)
def toggle_activate(
    test_id: str,
    admin: dict = Depends(require_admin),
):
    """Toggle isActive status of a test."""
    db = get_firestore()
    ref = db.collection("tests").document(test_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Test not found.")
    current = doc.to_dict().get("isActive", False)
    ref.update({"isActive": not current})
    updated = ref.get().to_dict()
    updated["id"] = test_id
    return updated
