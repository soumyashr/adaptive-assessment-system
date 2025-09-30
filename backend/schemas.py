from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    competence_level: str = "C1"

class User(BaseModel):
    id: int
    username: str
    competence_level: str
    created_at: datetime

    class Config:
        from_attributes = True

class QuestionBase(BaseModel):
    subject: str
    question_id: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    answer: str
    topic: str
    tier: str
    discrimination_a: float
    difficulty_b: float
    guessing_c: float

class Question(QuestionBase):
    id: int

    class Config:
        from_attributes = True

# In schemas.py - Update QuestionResponse
class QuestionResponse(BaseModel):
    id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    topic: str
    tier: str
    difficulty_b: float        # ADD THIS
    discrimination_a: float    # ADD THIS
    guessing_c: float          # ADD THIS

class AssessmentStart(BaseModel):
    username: str
    subject: str

class AnswerSubmission(BaseModel):
    question_id: int
    selected_option: str
    response_time_ms: Optional[int] = None

class AssessmentSession(BaseModel):
    session_id: int
    current_question: Optional[QuestionResponse] = None
    theta: float
    sem: float
    questions_asked: int
    completed: bool = False
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
    subject: str
    theta: float
    sem: float
    tier: str
    assessments_taken: int
    last_updated: datetime

class UserProficiency(BaseModel):
    username: str
    proficiencies: List[UserProficiencySubject]
