"""
paragraph_recall.py — Paragraph Recall feature.

Admin:
  POST   /paragraph-recall          — create a challenge
  GET    /paragraph-recall          — list all challenges
  PUT    /paragraph-recall/{id}     — update a challenge
  DELETE /paragraph-recall/{id}     — delete a challenge
  PATCH  /paragraph-recall/{id}/activate — toggle active

User:
  GET    /paragraph-recall/active   — list active challenges (paragraph hidden)
  GET    /paragraph-recall/{id}     — get one challenge (paragraph hidden for users)
  POST   /paragraph-recall/{id}/attempt — submit user's recalled text, score via Groq
  GET    /paragraph-recall/attempts/me  — user's own attempt history
"""

from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from firebase_admin_setup import get_firestore
from dependencies import require_admin, require_authenticated
from models.schemas import (
    ParagraphRecallCreate,
    ParagraphRecallUpdate,
    ParagraphRecallOut,
    ParagraphRecallAttemptSubmit,
    ParagraphRecallAttemptResult,
    ParagraphRecallAttemptHistoryItem,
)
from typing import List
from datetime import datetime, timezone
import uuid
import httpx

router = APIRouter(prefix="/paragraph-recall", tags=["Paragraph Recall"])

GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
GROQ_CHAT_URL   = "https://api.groq.com/openai/v1/chat/completions"

DEFAULT_WRITE_DURATION = 540  # seconds


# ─── Helper ──────────────────────────────────────────────────────────────────

def _safe_doc(doc_id: str, data: dict, include_paragraph: bool = True) -> dict:
    """Build a safe response dict; strip paragraph if not authorized."""
    out = {
        "id":              doc_id,
        "title":           data.get("title", ""),
        "description":     data.get("description", ""),
        "readDuration":    data.get("readDuration", 60),
        "writeDuration":   data.get("writeDuration", DEFAULT_WRITE_DURATION),
        "isActive":        data.get("isActive", False),
        "createdBy":       data.get("createdBy", ""),
        "createdAt":       data.get("createdAt"),
    }
    if include_paragraph:
        out["paragraph"] = data.get("paragraph", "")
    return out


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@router.post("", response_model=ParagraphRecallOut, status_code=201)
def create_challenge(
    payload: ParagraphRecallCreate,
    admin: dict = Depends(require_admin),
):
    """Create a new Paragraph Recall challenge."""
    db  = get_firestore()
    cid = str(uuid.uuid4())
    data = {
        "title":         payload.title,
        "description":   payload.description,
        "paragraph":     payload.paragraph,
        "readDuration":  payload.readDuration,
        "writeDuration": payload.writeDuration,
        "isActive":      payload.isActive,
        "createdBy":     admin["uid"],
        "createdAt":     SERVER_TIMESTAMP,
    }
    db.collection("paragraph_recall").document(cid).set(data)
    return {**data, "id": cid, "createdAt": None}


@router.get("", response_model=List[ParagraphRecallOut])
def list_challenges(admin: dict = Depends(require_admin)):
    """List ALL challenges (admin only — includes paragraph text)."""
    db   = get_firestore()
    docs = db.collection("paragraph_recall").stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append(_safe_doc(doc.id, data, include_paragraph=True))
    results.sort(key=lambda x: x.get("createdAt") or 0)
    return results


@router.put("/{challenge_id}", response_model=ParagraphRecallOut)
def update_challenge(
    challenge_id: str,
    payload: ParagraphRecallUpdate,
    admin: dict = Depends(require_admin),
):
    """Update an existing challenge."""
    db  = get_firestore()
    ref = db.collection("paragraph_recall").document(challenge_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Challenge not found.")
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    ref.update(updates)
    data = ref.get().to_dict()
    return _safe_doc(challenge_id, data, include_paragraph=True)


@router.delete("/{challenge_id}", status_code=204)
def delete_challenge(
    challenge_id: str,
    admin: dict = Depends(require_admin),
):
    """Delete a challenge."""
    db  = get_firestore()
    ref = db.collection("paragraph_recall").document(challenge_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Challenge not found.")
    ref.delete()
    return None


@router.patch("/{challenge_id}/activate", response_model=ParagraphRecallOut)
def toggle_activate(
    challenge_id: str,
    admin: dict = Depends(require_admin),
):
    """Toggle isActive status."""
    db  = get_firestore()
    ref = db.collection("paragraph_recall").document(challenge_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Challenge not found.")
    current = doc.to_dict().get("isActive", False)
    ref.update({"isActive": not current})
    data = ref.get().to_dict()
    return _safe_doc(challenge_id, data, include_paragraph=True)


# ─── User endpoints ───────────────────────────────────────────────────────────

@router.get("/active", response_model=List[ParagraphRecallOut])
def list_active_challenges(user: dict = Depends(require_authenticated)):
    """List active challenges for users — paragraph text is NOT included."""
    db   = get_firestore()
    docs = (
        db.collection("paragraph_recall")
        .where("isActive", "==", True)
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append(_safe_doc(doc.id, data, include_paragraph=False))
    results.sort(key=lambda x: x.get("createdAt") or 0)
    return results


@router.get("/attempts/me", response_model=List[ParagraphRecallAttemptHistoryItem])
def my_recall_attempts(user: dict = Depends(require_authenticated)):
    """Return the current user's Paragraph Recall attempt history."""
    db   = get_firestore()
    docs = (
        db.collection("paragraph_recall_attempts")
        .where("userId", "==", user["uid"])
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        # Enrich with challenge title
        ch_doc = db.collection("paragraph_recall").document(data.get("challengeId", "")).get()
        ch_title = ch_doc.to_dict().get("title", "Unknown") if ch_doc.exists else "Unknown"
        results.append({
            "attemptId":    doc.id,
            "challengeId":  data.get("challengeId"),
            "challengeTitle": ch_title,
            "submittedAt":  data.get("submittedAt"),
            "score":        data.get("score", 0),
            "feedback":     data.get("feedback", ""),
            "model":        data.get("model", ""),
        })
    results.sort(
        key=lambda x: x["submittedAt"] if x["submittedAt"] else 0,
        reverse=True,
    )
    return results


@router.get("/{challenge_id}")
def get_challenge(
    challenge_id: str,
    user: dict = Depends(require_authenticated),
):
    """
    Get a single challenge.
    Admins get the full paragraph. Users get metadata only (no paragraph).
    The paragraph is sent separately via /start endpoint timing logic on frontend.
    """
    db  = get_firestore()
    ref = db.collection("paragraph_recall").document(challenge_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Challenge not found.")
    data = doc.to_dict()
    is_admin = user.get("role") == "admin"
    if not is_admin and not data.get("isActive"):
        raise HTTPException(status_code=404, detail="Challenge not found.")
    return _safe_doc(challenge_id, data, include_paragraph=is_admin)


@router.get("/{challenge_id}/paragraph")
def get_challenge_paragraph(
    challenge_id: str,
    user: dict = Depends(require_authenticated),
):
    """
    Returns the paragraph text for an active challenge.
    Called by the frontend at the exact moment the read timer starts.
    """
    db  = get_firestore()
    ref = db.collection("paragraph_recall").document(challenge_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Challenge not found.")
    data = doc.to_dict()
    if not data.get("isActive") and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Challenge not active.")
    return {"paragraph": data.get("paragraph", "")}


@router.post("/groq/models")
def get_groq_models(payload: dict, user: dict = Depends(require_authenticated)):
    """
    Proxy: fetch available Groq models using the user's API key.
    payload: { "apiKey": "..." }
    """
    api_key = payload.get("apiKey", "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="Groq API key is required.")
    try:
        resp = httpx.get(
            GROQ_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Invalid Groq API key or Groq error.")
        models_data = resp.json()
        # Return only chat-completions-capable models
        models = [
            m["id"] for m in models_data.get("data", [])
            if "whisper" not in m["id"].lower()
        ]
        models.sort()
        return {"models": models}
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Groq: {str(e)}")


@router.post("/{challenge_id}/attempt", response_model=ParagraphRecallAttemptResult, status_code=201)
def submit_recall_attempt(
    challenge_id: str,
    payload: ParagraphRecallAttemptSubmit,
    user: dict = Depends(require_authenticated),
):
    """
    Submit the user's recalled paragraph.
    Sends original + user text to Groq LLM and returns a score out of 100.
    Stores result + updates leaderboard.
    """
    db  = get_firestore()
    ref = db.collection("paragraph_recall").document(challenge_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Challenge not found.")
    data = doc.to_dict()
    if not data.get("isActive") and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Challenge not active.")

    original_paragraph = data.get("paragraph", "")
    user_text          = payload.userText.strip()
    api_key            = payload.groqApiKey.strip()
    model              = payload.model.strip()

    if not api_key:
        raise HTTPException(status_code=400, detail="Groq API key is required.")
    if not model:
        raise HTTPException(status_code=400, detail="Groq model is required.")
    if not user_text:
        raise HTTPException(status_code=400, detail="User recalled text is required.")

    # ── Call Groq LLM for scoring ──────────────────────────────────────────────
    prompt = f"""You are an expert evaluator for a "Paragraph Recall" exercise.

ORIGINAL PARAGRAPH:
\"\"\"{original_paragraph}\"\"\"

USER'S RECALLED VERSION:
\"\"\"{user_text}\"\"\"

Your task is to evaluate how accurately the user recalled the paragraph.
Consider:
1. Key facts and information retained (40 points)
2. Overall meaning and context preserved (30 points)
3. Sentence structure and wording similarity (20 points)
4. Completeness — how much of the content was captured (10 points)

Respond ONLY in this exact JSON format (no extra text, no markdown):
{{
  "score": <integer 0-100>,
  "feedback": "<2-3 sentence constructive feedback explaining the score>"
}}"""

    try:
        groq_resp = httpx.post(
            GROQ_CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       model,
                "messages":    [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens":  300,
            },
            timeout=30,
        )
        if groq_resp.status_code != 200:
            raise HTTPException(
                status_code=groq_resp.status_code,
                detail=f"Groq API error: {groq_resp.text}",
            )
        groq_data  = groq_resp.json()
        raw_output = groq_data["choices"][0]["message"]["content"].strip()

        # Parse JSON from LLM response
        import json, re
        # Extract JSON block even if LLM wraps it
        json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = json.loads(raw_output)

        score    = max(0, min(100, int(parsed.get("score", 0))))
        feedback = str(parsed.get("feedback", ""))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM scoring failed: {str(e)}")

    # ── Store attempt ──────────────────────────────────────────────────────────
    attempt_id   = str(uuid.uuid4())
    submitted_at = datetime.now(timezone.utc)

    db.collection("paragraph_recall_attempts").document(attempt_id).set({
        "userId":      user["uid"],
        "challengeId": challenge_id,
        "userText":    user_text,
        "score":       score,
        "feedback":    feedback,
        "model":       model,
        "submittedAt": submitted_at,
    })

    # ── Update leaderboard (recall score contributes separately) ──────────────
    _update_recall_leaderboard(
        uid=user["uid"],
        name=user.get("name", ""),
        username=user.get("username", ""),
        score=score,
    )

    return {
        "attemptId":      attempt_id,
        "challengeId":    challenge_id,
        "score":          score,
        "feedback":       feedback,
        "originalParagraph": original_paragraph,
        "userText":       user_text,
        "submittedAt":    submitted_at.isoformat(),
    }


def _update_recall_leaderboard(uid: str, name: str, username: str, score: float):
    """Add recall score to leaderboard (same collection as test leaderboard)."""
    db     = get_firestore()
    lb_ref = db.collection("leaderboard").document(uid)
    lb_doc = lb_ref.get()

    if lb_doc.exists:
        data      = lb_doc.to_dict()
        new_total = round(data.get("totalNormalizedScore", 0) + score, 2)
        new_att   = data.get("totalAttempts", 0) + 1
        lb_ref.update({
            "totalNormalizedScore": new_total,
            "totalAttempts":        new_att,
            "name":                 name,
            "username":             username,
        })
    else:
        lb_ref.set({
            "userId":               uid,
            "name":                 name,
            "username":             username,
            "totalNormalizedScore": round(score, 2),
            "totalAttempts":        1,
            "rank":                 0,
        })

    # Re-rank
    from services.scoring import _rerank_leaderboard
    _rerank_leaderboard()
