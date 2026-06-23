"""
notes.py — notes per topic. Stored in Firestore. Content is Markdown.
GET is accessible to any authenticated user; POST/PUT/DELETE require admin.
current_user is a plain dict from Firestore.
"""
from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from firebase_admin_setup import get_firestore
from dependencies import require_admin, require_authenticated
from models.schemas import NoteCreate, NoteUpdate, NoteOut
from typing import List
import uuid

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("", response_model=List[NoteOut])
def list_notes(
    topicId: str,
    user: dict = Depends(require_authenticated),
):
    """List all notes for a given topic."""
    db = get_firestore()
    # Single where only — avoids composite index requirement.
    docs = db.collection("notes").where("topicId", "==", topicId).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    # Sort by createdAt in Python
    results.sort(key=lambda x: x.get("createdAt") or 0)
    return results


@router.post("", response_model=NoteOut, status_code=201)
def create_note(
    payload: NoteCreate,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    note_id = str(uuid.uuid4())
    data = {
        "topicId":   payload.topicId,
        "title":     payload.title,
        "content":   payload.content,
        "createdAt": SERVER_TIMESTAMP,
    }
    db.collection("notes").document(note_id).set(data)
    return {**data, "id": note_id, "createdAt": None}


@router.put("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: str,
    payload: NoteUpdate,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    ref = db.collection("notes").document(note_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Note not found.")
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    ref.update(updates)
    doc = ref.get().to_dict()
    doc["id"] = note_id
    return doc


@router.delete("/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    ref = db.collection("notes").document(note_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Note not found.")
    ref.delete()
