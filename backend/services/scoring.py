"""
scoring.py — attempt scoring and leaderboard update logic.
"""
from typing import List, Dict, Any
from firebase_admin_setup import get_firestore


def score_attempt(answers: List[Dict], questions: List[Dict]) -> Dict:
    """
    Score a submitted attempt.

    answers: list of {questionId, selectedAnswer, timeTakenSeconds}
    questions: list of full question docs from Firestore

    Returns:
        {rawScore, totalQuestions, normalizedScore, scored_answers}
    """
    question_map = {q["id"]: q for q in questions}
    scored_answers = []
    raw_score = 0

    for ans in answers:
        qid = ans.get("questionId")
        selected = ans.get("selectedAnswer", "").strip()
        q = question_map.get(qid)

        if not q:
            continue  # skip unknown question ids

        correct = q.get("correctAnswer", "").strip()

        # Case-insensitive exact match for both MCQ and fill-in-blank
        is_correct = selected.lower() == correct.lower()
        if is_correct:
            raw_score += 1

        scored_answers.append({
            "questionId": qid,
            "questionText": q.get("questionText", ""),
            "selectedAnswer": selected,
            "correctAnswer": correct,
            "isCorrect": is_correct,
            "explanation": q.get("explanation", ""),
            "timeTakenSeconds": ans.get("timeTakenSeconds"),
        })

    total = len(questions)
    normalized = round((raw_score / total) * 100, 2) if total > 0 else 0.0

    return {
        "rawScore": raw_score,
        "totalQuestions": total,
        "normalizedScore": normalized,
        "scored_answers": scored_answers,
    }


def update_leaderboard(uid: str, name: str, username: str, normalized_score: float):
    """
    Upsert the leaderboard document for this user and re-rank all entries.
    Leaderboard totalNormalizedScore is the SUM of all attempt scores.
    """
    db = get_firestore()
    lb_ref = db.collection("leaderboard").document(uid)
    lb_doc = lb_ref.get()

    if lb_doc.exists:
        data = lb_doc.to_dict()
        new_total = round(data.get("totalNormalizedScore", 0) + normalized_score, 2)
        new_attempts = data.get("totalAttempts", 0) + 1
        lb_ref.update({
            "totalNormalizedScore": new_total,
            "totalAttempts": new_attempts,
            "name": name,
            "username": username,
        })
    else:
        lb_ref.set({
            "userId": uid,
            "name": name,
            "username": username,
            "totalNormalizedScore": round(normalized_score, 2),
            "totalAttempts": 1,
            "rank": 0,  # will be recalculated below
        })

    # Re-rank all leaderboard entries
    _rerank_leaderboard()


def _rerank_leaderboard():
    """Sort all leaderboard docs by totalNormalizedScore desc and write rank fields."""
    db = get_firestore()
    docs = list(db.collection("leaderboard").stream())
    sorted_docs = sorted(
        docs,
        key=lambda d: d.to_dict().get("totalNormalizedScore", 0),
        reverse=True,
    )

    batch = db.batch()
    for idx, doc in enumerate(sorted_docs, start=1):
        batch.update(doc.reference, {"rank": idx})
    batch.commit()
