"""
topics.py — CRUD for topics. Stored in Firestore.
GET is public (no auth needed for listing); POST/PUT/DELETE require admin.
current_user / admin is a plain dict from Firestore.
"""
from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from firebase_admin_setup import get_firestore
from dependencies import require_admin
from models.schemas import TopicCreate, TopicUpdate, TopicOut
from typing import List
import uuid

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get("", response_model=List[TopicOut])
def list_topics():
    """List all topics (public — no auth required)."""
    db = get_firestore()
    docs = db.collection("topics").order_by("createdAt").stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


@router.post("", response_model=TopicOut, status_code=201)
def create_topic(
    payload: TopicCreate,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    topic_id = str(uuid.uuid4())
    data = {
        "name":        payload.name,
        "description": payload.description,
        "createdBy":   admin["uid"],
        "createdAt":   SERVER_TIMESTAMP,
    }
    db.collection("topics").document(topic_id).set(data)
    return {**data, "id": topic_id, "createdAt": None}


@router.put("/{topic_id}", response_model=TopicOut)
def update_topic(
    topic_id: str,
    payload: TopicUpdate,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    ref = db.collection("topics").document(topic_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Topic not found.")
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    ref.update(updates)
    doc = ref.get().to_dict()
    doc["id"] = topic_id
    return doc


@router.delete("/{topic_id}", status_code=204)
def delete_topic(
    topic_id: str,
    admin: dict = Depends(require_admin),
):
    db = get_firestore()
    ref = db.collection("topics").document(topic_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Topic not found.")
    ref.delete()
