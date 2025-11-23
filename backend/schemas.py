# backend/schemas.py
# UPDATED: Added tier tracking and precision quality fields

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# EXISTING - NO CHANGES
class UserCreate(BaseModel):
    username: str
    initial_competence_level: str = "beginner"

class User(BaseModel):
    id: int
    username: str
    initial_competence_level: str
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    topic: str
    tier: str
    difficulty_b: float
    discrimination_a: float
    guessing_c: float


class AssessmentStart(BaseModel):
    username: str
    subject: str


class AnswerSubmission(BaseModel):
    question_id: int
    selected_option: str
    response_time_ms: Optional[int] = None


# UPDATED: Added tier tracking and precision fields
class AssessmentSession(BaseModel):
    session_id: int
    current_question: Optional[QuestionResponse] = None
    theta: float
    sem: float
    questions_asked: int
    completed: bool = False
    last_response_correct: Optional[bool] = None
    topic_performance: Optional[Dict[str, Any]] = None
    # ✅ NEW: Tier tracking fields
    estimated_tier: Optional[str] = None
    active_tier: Optional[str] = None
    tier_alignment: Optional[bool] = None
    tier_note: Optional[str] = None
    # ✅ NEW: Precision tracking fields
    precision_quality: Optional[Dict[str, Any]] = None
    progress_to_target: Optional[float] = None
    target_sem: Optional[float] = None
    early_termination: Optional[bool] = False
    termination_reason: Optional[str] = None
    reliability_note: Optional[str] = None


class ResponseDetails(BaseModel):
    question_id: int
    question: str
    selected_option: str
    correct_answer: str
    is_correct: bool
    theta_before: float
    theta_after: float
    difficulty: float


# UPDATED: Added tier tracking and precision fields
class AssessmentResults(BaseModel):
    session_id: int
    user_id: int
    subject: str
    final_theta: float
    final_sem: float
    tier: str
    questions_asked: int
    correct_answers: int
    accuracy: float
    responses: List[ResponseDetails]
    completed_at: Optional[datetime]
    topic_performance: Optional[Dict[str, Any]] = None
    learning_roadmap: Optional[Dict[str, Any]] = None
    # ✅ NEW: Tier tracking fields
    estimated_tier: Optional[str] = None
    active_tier: Optional[str] = None
    tier_alignment: Optional[bool] = None
    tier_note: Optional[str] = None
    # ✅ NEW: Precision tracking fields
    precision_quality: Optional[Dict[str, Any]] = None
    progress_to_target: Optional[float] = None
    target_sem: Optional[float] = None


# EXISTING - NO CHANGES
class UserProficiencySubject(BaseModel):
    item_bank: str
    subject: str
    theta: float
    sem: float
    tier: str
    assessments_taken: int
    last_updated: datetime


class UserProficiency(BaseModel):
    username: str
    proficiencies: List[UserProficiencySubject]

class ItemBankCreate(BaseModel):
    name: str
    display_name: str
    subject: str

class ItemBank(BaseModel):
    id: int
    name: str
    display_name: str
    subject: str
    irt_model: str
    status: str
    total_items: int
    calibrated_items: int
    test_takers: int
    accuracy: Optional[float]
    created_at: datetime
    last_calibrated: Optional[datetime]

    class Config:
        from_attributes = True