"""
schemas.py — Pydantic request/response models for all API endpoints.
User profile is stored in Firestore (no SQL types needed here).
"""
from __future__ import annotations
from typing import List, Optional, Any
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


# ─── Auth ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=6)


class AdminCreate(UserCreate):
    admin_key: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    uid: str
    name: str
    username: str
    email: str
    role: str
    theme_pref: str = "dark"
    created_at: Optional[Any] = None


class ThemeUpdate(BaseModel):
    theme_pref: str = Field(..., pattern=r"^(dark|light)$")


# ─── Topics ───────────────────────────────────────────────────────────────────

class TopicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


class TopicOut(BaseModel):
    id: str
    name: str
    description: str
    createdBy: str
    createdAt: Any


# ─── Notes ────────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    topicId: str
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(default="")


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class NoteOut(BaseModel):
    id: str
    topicId: str
    title: str
    content: str
    createdAt: Any


# ─── Questions ────────────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    topicId: str
    type: str = Field(..., pattern=r"^(mcq|fill_blank)$")
    questionText: str = Field(..., min_length=1)
    options: Optional[List[str]] = None
    correctAnswer: str
    explanation: str = Field(default="")
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard)$")


class QuestionUpdate(BaseModel):
    questionText: Optional[str] = None
    options: Optional[List[str]] = None
    correctAnswer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern=r"^(easy|medium|hard)$")


class QuestionOut(BaseModel):
    id: str
    topicId: str
    type: str
    questionText: str
    options: Optional[List[str]]
    correctAnswer: str
    explanation: str
    difficulty: str
    createdAt: Any
    updatedAt: Any


class BulkQuestionItem(BaseModel):
    """A single question inside a bulk import — topicId is supplied by the parent."""
    type: str = Field(..., pattern=r"^(mcq|fill_blank)$")
    questionText: str = Field(..., min_length=1)
    options: Optional[List[str]] = None
    correctAnswer: str
    explanation: str = Field(default="")
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard)$")


class BulkQuestionCreate(BaseModel):
    topicId: str
    questions: List[BulkQuestionItem]


class BulkImportResult(BaseModel):
    imported: int
    failed: int
    errors: List[str]


# ─── Test Questions ───────────────────────────────────────────────────────────

class TestQuestionCreate(QuestionCreate):
    pass


class TestQuestionUpdate(QuestionUpdate):
    pass


class TestQuestionOut(QuestionOut):
    pass


class BulkTestQuestionCreate(BulkQuestionCreate):
    pass



# ─── Tests ────────────────────────────────────────────────────────────────────

class TestCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    type: str = Field(..., pattern=r"^(topic|overall)$")
    topicId: Optional[str] = None
    questionIds: List[str]
    timerMode: str = Field(..., pattern=r"^(per_test|per_question)$")
    duration: int = Field(..., gt=0)
    passThreshold: float = Field(..., ge=0, le=100)
    isActive: bool = False


class TestUpdate(BaseModel):
    title: Optional[str] = None
    questionIds: Optional[List[str]] = None
    timerMode: Optional[str] = Field(None, pattern=r"^(per_test|per_question)$")
    duration: Optional[int] = Field(None, gt=0)
    passThreshold: Optional[float] = Field(None, ge=0, le=100)
    isActive: Optional[bool] = None


class TestOut(BaseModel):
    id: str
    title: str
    type: str
    topicId: Optional[str]
    questionIds: List[str]
    timerMode: str
    duration: int
    passThreshold: float
    isActive: bool
    createdBy: str
    createdAt: Any


# ─── Attempts ─────────────────────────────────────────────────────────────────

class AttemptStartRequest(BaseModel):
    testId: str


class AttemptStartResponse(BaseModel):
    attemptId: str
    startedAt: str
    duration: int
    timerMode: str


class AnswerItem(BaseModel):
    questionId: str
    selectedAnswer: str
    timeTakenSeconds: Optional[float] = None


class AttemptSubmitRequest(BaseModel):
    answers: List[AnswerItem]


class AnswerResult(BaseModel):
    questionId: str
    questionText: str
    selectedAnswer: str
    correctAnswer: str
    isCorrect: bool
    explanation: str
    timeTakenSeconds: Optional[float]


class AttemptResult(BaseModel):
    attemptId: str
    testId: str
    rawScore: int
    totalQuestions: int
    normalizedScore: float
    passed: bool
    timeTakenSeconds: float
    answers: List[AnswerResult]


class AttemptHistoryItem(BaseModel):
    attemptId: str
    testId: str
    testTitle: str
    submittedAt: Any
    rawScore: int
    totalQuestions: int
    normalizedScore: float
    passed: bool


# ─── Leaderboard ──────────────────────────────────────────────────────────────

class LeaderboardEntry(BaseModel):
    rank: int
    userId: str
    name: str
    username: str
    totalNormalizedScore: float
    totalAttempts: int


# ─── Admin Stats ──────────────────────────────────────────────────────────────

class TestStat(BaseModel):
    testId: str
    testTitle: str
    avgScore: float
    totalAttempts: int


class AdminStats(BaseModel):
    totalUsers: int
    totalAttempts: int
    testStats: List[TestStat]
    mostAttemptedTest: Optional[TestStat]
