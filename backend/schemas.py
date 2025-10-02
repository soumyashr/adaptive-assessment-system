from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    initial_competence_level: str = "beginner"  # Changed

class User(BaseModel):
    id: int
    username: str
    initial_competence_level: str  # Changed
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


class AssessmentSession(BaseModel):
    session_id: int  # Changed from id
    current_question: Optional[QuestionResponse] = None
    theta: float  # Changed from current_theta
    sem: float    # Changed from current_sem
    questions_asked: int
    completed: bool = False  # Changed from is_completed
    last_response_correct: Optional[bool] = None


class ResponseDetails(BaseModel):
    question_id: int
    question: str
    selected_option: str
    correct_answer: str
    is_correct: bool
    theta_before: float
    theta_after: float


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


class UserProficiencySubject(BaseModel):
    item_bank: str  # Item bank name
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