#!/usr/bin/env python3
"""
Adaptive Assessment System - Complete File Generator
Run this script to create all necessary files for the system
"""

import os
from pathlib import Path


def create_file(path, content):
    """Create a file with given content"""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created: {path}")


def main():
    print("🚀 Creating Adaptive Assessment System files...")
    print("=" * 60)

    # Backend - main.py
    main_py = '''from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io
import logging

from database import get_db, engine
import models
import schemas
from irt_engine import IRTEngine
from services import UserService, QuestionService, AssessmentService
from config import get_config

# Get configuration
config = get_config()
config.validate_config()

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOGGING_CONFIG["level"]),
    format=config.LOGGING_CONFIG["format"],
    handlers=[
        logging.FileHandler(config.LOGGING_CONFIG["log_file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=config.API_CONFIG["title"], 
    version=config.API_CONFIG["version"]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.API_CONFIG["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
user_service = UserService()
question_service = QuestionService()
assessment_service = AssessmentService()
irt_engine = IRTEngine()

@app.post("/api/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user or get existing user"""
    return user_service.get_or_create_user(db, user.username, user.competence_level)

@app.get("/api/users/{username}", response_model=schemas.User)
def get_user(username: str, db: Session = Depends(get_db)):
    """Get user by username"""
    user = user_service.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/questions/upload")
def upload_questions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload questions from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Read CSV content
    content = file.file.read()
    df = pd.read_csv(io.StringIO(content.decode('utf-8')))

    # Validate required columns
    required_columns = ['subject', 'question_id', 'question', 'option_a', 'option_b', 
                       'option_c', 'option_d', 'answer', 'topic', 'tier', 
                       'discrimination_a', 'difficulty_b', 'guessing_c']

    if not all(col in df.columns for col in required_columns):
        raise HTTPException(status_code=400, detail="CSV missing required columns")

    # Import questions
    imported_count = question_service.import_questions_from_df(db, df)
    return {"message": f"Successfully imported {imported_count} questions"}

@app.post("/api/assessments/start", response_model=schemas.AssessmentSession)
def start_assessment(
    assessment_start: schemas.AssessmentStart, 
    db: Session = Depends(get_db)
):
    """Start a new assessment session"""
    user = user_service.get_user_by_username(db, assessment_start.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session = assessment_service.start_assessment(
        db, user.id, assessment_start.subject
    )

    # Get first question
    first_question = assessment_service.get_next_question(
        db, session.id, irt_engine
    )

    return {
        "session_id": session.id,
        "current_question": first_question,
        "theta": session.current_theta,
        "sem": session.current_sem,
        "questions_asked": session.questions_asked
    }

@app.post("/api/assessments/{session_id}/answer", response_model=schemas.AssessmentSession)
def submit_answer(
    session_id: int,
    answer: schemas.AnswerSubmission,
    db: Session = Depends(get_db)
):
    """Submit an answer and get next question"""

    # Record response
    assessment_service.record_response(
        db, session_id, answer.question_id, answer.selected_option, irt_engine
    )

    # Get updated session
    session = assessment_service.get_session(db, session_id)

    # Check if assessment should continue
    if session.is_completed:
        return {
            "session_id": session.id,
            "current_question": None,
            "theta": session.current_theta,
            "sem": session.current_sem,
            "questions_asked": session.questions_asked,
            "completed": True
        }

    # Get next question
    next_question = assessment_service.get_next_question(
        db, session_id, irt_engine
    )

    return {
        "session_id": session.id,
        "current_question": next_question,
        "theta": session.current_theta,
        "sem": session.current_sem,
        "questions_asked": session.questions_asked
    }

@app.get("/api/assessments/{session_id}/results", response_model=schemas.AssessmentResults)
def get_assessment_results(session_id: int, db: Session = Depends(get_db)):
    """Get assessment results"""
    return assessment_service.get_assessment_results(db, session_id)

@app.get("/api/users/{username}/proficiency", response_model=schemas.UserProficiency)
def get_user_proficiency(username: str, db: Session = Depends(get_db)):
    """Get user's proficiency across subjects"""
    user = user_service.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user_service.get_user_proficiency(db, user.id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=config.API_CONFIG["host"], 
        port=config.API_CONFIG["port"]
    )
'''
    create_file("main.py", main_py)

    # Backend - database.py
    database_py = '''from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./adaptive_assessment.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''
    create_file("database.py", database_py)

    # Backend - models.py
    models_py = '''from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.relationship import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    competence_level = Column(String, default="C1")  # C1, C2, C3, C4
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    assessment_sessions = relationship("AssessmentSession", back_populates="user")
    proficiencies = relationship("UserProficiency", back_populates="user")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, index=True)
    question_id = Column(String, unique=True, index=True)
    question = Column(Text)
    option_a = Column(Text)
    option_b = Column(Text)
    option_c = Column(Text)
    option_d = Column(Text)
    answer = Column(String)  # A, B, C, or D
    topic = Column(String, index=True)
    tier = Column(String, index=True)  # C1, C2, C3, C4
    discrimination_a = Column(Float)
    difficulty_b = Column(Float)
    guessing_c = Column(Float)
    selected_option_text = Column(Text, nullable=True)

    # Relationships
    responses = relationship("Response", back_populates="question")

class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    initial_theta = Column(Float)
    current_theta = Column(Float)
    current_sem = Column(Float, default=1.0)
    questions_asked = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="assessment_sessions")
    responses = relationship("Response", back_populates="session")

class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("assessment_sessions.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    selected_option = Column(String)  # A, B, C, or D
    is_correct = Column(Boolean)
    theta_before = Column(Float)
    theta_after = Column(Float)
    sem_after = Column(Float)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    session = relationship("AssessmentSession", back_populates="responses")
    question = relationship("Question", back_populates="responses")

class UserProficiency(Base):
    __tablename__ = "user_proficiencies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    theta = Column(Float)
    sem = Column(Float)
    tier = Column(String)  # C1, C2, C3, C4
    assessments_taken = Column(Integer, default=0)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="proficiencies")
'''
    create_file("models.py", models_py)

    # Backend - schemas.py
    schemas_py = '''from pydantic import BaseModel
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

class QuestionResponse(BaseModel):
    id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    topic: str
    tier: str

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
'''
    create_file("schemas.py", schemas_py)

    # Backend - config.py
    config_py = '''import os
from typing import Dict, Tuple

class Config:
    """Configuration class for Adaptive Assessment System"""

    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./adaptive_assessment.db")

    # IRT Engine Configuration
    IRT_CONFIG = {
        "target_sem": float(os.getenv("TARGET_SEM", "0.23")),
        "max_questions": int(os.getenv("MAX_QUESTIONS", "40")),
        "min_questions": int(os.getenv("MIN_QUESTIONS", "5")),
        "history_window": int(os.getenv("HISTORY_WINDOW", "8")),
        "max_theta_change": float(os.getenv("MAX_THETA_CHANGE", "0.5")),
        "theta_bounds": (-2.0, 2.0),
        "newton_raphson_iterations": int(os.getenv("NR_ITERATIONS", "10")),
        "convergence_threshold": float(os.getenv("CONVERGENCE_THRESHOLD", "0.01")),
        "exponential_smoothing_alpha": float(os.getenv("EXP_SMOOTH_ALPHA", "0.7"))
    }

    # Tier Configuration
    TIER_THETA_RANGES: Dict[str, Tuple[float, float]] = {
        "C1": (-2.0, -1.0),
        "C2": (-1.0, 0.0),
        "C3": (0.0, 1.0),
        "C4": (1.0, 2.0)
    }

    TIER_DISCRIMINATION_RANGES: Dict[str, Tuple[float, float]] = {
        "C1": (0.8, 1.0),
        "C2": (1.0, 1.4),
        "C3": (1.0, 1.4),
        "C4": (1.4, 1.6)
    }

    TIER_DIFFICULTY_RANGES: Dict[str, Tuple[float, float]] = {
        "C1": (-1.5, -0.5),
        "C2": (-0.5, 0.5),
        "C3": (0.5, 1.0),
        "C4": (1.0, 2.0)
    }

    # Initial theta values for competence levels
    INITIAL_THETA_MAP: Dict[str, float] = {
        "C1": -1.5,
        "C2": -0.5,
        "C3": 0.5,
        "C4": 1.5
    }

    # API Configuration
    API_CONFIG = {
        "host": os.getenv("API_HOST", "0.0.0.0"),
        "port": int(os.getenv("API_PORT", "8000")),
        "cors_origins": os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        "title": "Adaptive Assessment API",
        "version": "1.0.0"
    }

    # Logging Configuration
    LOGGING_CONFIG = {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "log_file": os.getenv("LOG_FILE", "adaptive_assessment.log"),
    }

    @classmethod
    def get_irt_config(cls):
        """Get IRT configuration"""
        return cls.IRT_CONFIG

    @classmethod
    def get_tier_config(cls):
        """Get tier configuration"""
        return {
            "theta_ranges": cls.TIER_THETA_RANGES,
            "discrimination_ranges": cls.TIER_DISCRIMINATION_RANGES,
            "difficulty_ranges": cls.TIER_DIFFICULTY_RANGES,
            "initial_theta_map": cls.INITIAL_THETA_MAP
        }

    @classmethod
    def validate_config(cls):
        """Validate configuration values"""
        errors = []

        # Validate IRT config
        if cls.IRT_CONFIG["target_sem"] <= 0:
            errors.append("TARGET_SEM must be positive")

        if cls.IRT_CONFIG["min_questions"] >= cls.IRT_CONFIG["max_questions"]:
            errors.append("MIN_QUESTIONS must be less than MAX_QUESTIONS")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        return True

def get_config():
    """Get configuration based on environment"""
    return Config()
'''
    create_file("config.py", config_py)

    # Backend - irt_engine.py
    irt_engine_py = '''import math
import numpy as np
from typing import List, Tuple, Dict, Optional
from collections import deque
from config import get_config

class IRTEngine:
    def __init__(self, config=None):
        self.config = config or get_config()
        irt_config = self.config.get_irt_config()
        tier_config = self.config.get_tier_config()

        # Load configuration values
        self.target_sem = irt_config["target_sem"]
        self.max_questions = irt_config["max_questions"]
        self.min_questions = irt_config["min_questions"]
        self.history_window = irt_config["history_window"]
        self.max_theta_change = irt_config["max_theta_change"]
        self.theta_bounds = irt_config["theta_bounds"]
        self.newton_raphson_iterations = irt_config["newton_raphson_iterations"]
        self.convergence_threshold = irt_config["convergence_threshold"]
        self.exponential_smoothing_alpha = irt_config["exponential_smoothing_alpha"]

        # Tier mappings from config
        self.tier_theta_ranges = tier_config["theta_ranges"]
        self.tier_discrimination_ranges = tier_config["discrimination_ranges"]
        self.tier_difficulty_ranges = tier_config["difficulty_ranges"]
        self.initial_theta_map = tier_config["initial_theta_map"]

    def get_initial_theta(self, competence_level: str) -> float:
        """Get initial theta based on competence level"""
        return self.initial_theta_map.get(competence_level, -1.0)

    def theta_to_tier(self, theta: float) -> str:
        """Convert theta to tier"""
        if theta < -1.0:
            return "C1"
        elif theta < 0.0:
            return "C2"
        elif theta < 1.0:
            return "C3"
        else:
            return "C4"

    def probability_correct(self, theta: float, difficulty: float, 
                          discrimination: float, guessing: float = 0.25) -> float:
        """Calculate probability of correct response using 3PL model"""
        try:
            exponent = discrimination * (theta - difficulty)
            if exponent > 700:  # Prevent overflow
                return 1.0
            elif exponent < -700:
                return guessing
            else:
                return guessing + (1 - guessing) / (1 + math.exp(-exponent))
        except (OverflowError, ZeroDivisionError):
            return 0.5

    def information(self, theta: float, difficulty: float, 
                   discrimination: float, guessing: float = 0.25) -> float:
        """Calculate Fisher Information for an item"""
        p = self.probability_correct(theta, difficulty, discrimination, guessing)

        if p <= guessing or p >= 1.0:
            return 0.0

        try:
            # Fisher Information for 3PL model
            q = 1 - p
            p_star = (p - guessing) / (1 - guessing)

            numerator = (discrimination ** 2) * (p_star * (1 - p_star))
            denominator = (1 - guessing) ** 2

            information_value = numerator / denominator
            return max(0.0, information_value)
        except (ZeroDivisionError, ValueError):
            return 0.0

    def calculate_sem(self, theta: float, questions_info: List[Tuple[float, float, float]]) -> float:
        """Calculate Standard Error of Measurement"""
        total_info = 0.0
        for difficulty, discrimination, guessing in questions_info:
            total_info += self.information(theta, difficulty, discrimination, guessing)

        if total_info <= 0:
            return 1.0

        return 1.0 / math.sqrt(total_info)

    def select_next_question(self, theta: float, available_questions: List[Dict], 
                           response_history: List[bool]) -> Optional[Dict]:
        """Select next question using Fisher Information and fairness constraints"""
        if not available_questions:
            return None

        # Calculate current tier
        current_tier = self.theta_to_tier(theta)

        # Apply streak detection and tier adjustment
        adjusted_tier = self._apply_fairness_constraints(current_tier, response_history)

        # Filter questions by adjusted tier and discrimination range
        suitable_questions = self._filter_questions_by_tier(available_questions, adjusted_tier)

        if not suitable_questions:
            # Fallback to any available question
            suitable_questions = available_questions

        # Select question with maximum Fisher Information
        best_question = None
        max_information = -1

        for question in suitable_questions:
            info = self.information(
                theta, 
                question['difficulty_b'], 
                question['discrimination_a'], 
                question['guessing_c']
            )

            if info > max_information:
                max_information = info
                best_question = question

        return best_question

    def _apply_fairness_constraints(self, current_tier: str, 
                                  response_history: List[bool]) -> str:
        """Apply fairness constraints for tier adjustment"""
        if len(response_history) < 4:
            return current_tier

        recent_responses = response_history[-4:]

        # Detect streaks
        if all(recent_responses):  # All correct
            return self._adjust_tier_up(current_tier)
        elif not any(recent_responses):  # All incorrect
            return self._adjust_tier_down(current_tier)

        return current_tier

    def _adjust_tier_up(self, tier: str) -> str:
        """Adjust tier up for too many correct answers"""
        tier_order = ["C1", "C2", "C3", "C4"]
        current_index = tier_order.index(tier)
        return tier_order[min(current_index + 1, len(tier_order) - 1)]

    def _adjust_tier_down(self, tier: str) -> str:
        """Adjust tier down for too many incorrect answers"""
        tier_order = ["C1", "C2", "C3", "C4"]
        current_index = tier_order.index(tier)
        return tier_order[max(current_index - 1, 0)]

    def _filter_questions_by_tier(self, questions: List[Dict], tier: str) -> List[Dict]:
        """Filter questions by tier-appropriate difficulty and discrimination"""
        difficulty_range = self.tier_difficulty_ranges[tier]
        discrimination_range = self.tier_discrimination_ranges[tier]

        filtered = []
        for q in questions:
            if (difficulty_range[0] <= q['difficulty_b'] <= difficulty_range[1] and
                discrimination_range[0] <= q['discrimination_a'] <= discrimination_range[1]):
                filtered.append(q)

        return filtered

    def update_theta(self, current_theta: float, responses: List[Tuple[bool, float, float, float]]) -> float:
        """Update theta using Newton-Raphson method with MLE"""
        if not responses:
            return current_theta

        theta = current_theta

        # Newton-Raphson iterations
        for iteration in range(self.newton_raphson_iterations):
            likelihood_derivative = 0.0
            second_derivative = 0.0

            for is_correct, difficulty, discrimination, guessing in responses:
                p = self.probability_correct(theta, difficulty, discrimination, guessing)

                if p <= 0.001:
                    p = 0.001
                elif p >= 0.999:
                    p = 0.999

                q = 1 - p

                # First derivative of log-likelihood
                if is_correct:
                    likelihood_derivative += (discrimination * q) / p
                else:
                    likelihood_derivative -= (discrimination * p) / q

                # Second derivative of log-likelihood
                second_derivative -= (discrimination ** 2) * p * q / (p * q)

            if abs(second_derivative) < 1e-8:
                break

            # Newton-Raphson update
            delta_theta = likelihood_derivative / second_derivative

            # Apply delta clamping
            delta_theta = max(-self.max_theta_change, 
                            min(self.max_theta_change, delta_theta))

            new_theta = theta + delta_theta

            # Apply theta bounds
            new_theta = max(self.theta_bounds[0], 
                          min(self.theta_bounds[1], new_theta))

            # Check convergence
            if abs(delta_theta) < self.convergence_threshold:
                break

            theta = new_theta

        # Apply exponential smoothing to prevent oscillations
        smoothed_theta = self.exponential_smoothing_alpha * theta + (1 - self.exponential_smoothing_alpha) * current_theta

        return max(self.theta_bounds[0], 
                  min(self.theta_bounds[1], smoothed_theta))

    def should_stop_assessment(self, sem: float, questions_asked: int, 
                             response_history: List[bool]) -> bool:
        """Determine if assessment should stop"""
        # Minimum questions check
        if questions_asked < self.min_questions:
            return False

        # Maximum questions check
        if questions_asked >= self.max_questions:
            return True

        # SEM threshold check
        if sem <= self.target_sem:
            return True

        # Check for consistent performance (additional stopping criterion)
        if len(response_history) >= 8:
            recent_responses = response_history[-8:]
            accuracy = sum(recent_responses) / len(recent_responses)
            if accuracy == 1.0 or accuracy == 0.0:
                return True  # Perfect or no correct answers

        return False
'''
    create_file("irt_engine.py", irt_engine_py)

    # Backend - services.py (Part 1 due to length)
    services_py_part1 = '''from sqlalchemy.orm import Session
from sqlalchemy import and_, not_
from typing import List, Optional, Dict
import pandas as pd
from datetime import datetime

import models
import schemas
from irt_engine import IRTEngine

class UserService:
    def get_or_create_user(self, db: Session, username: str, competence_level: str = "C1") -> models.User:
        """Get existing user or create new one"""
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            user = models.User(username=username, competence_level=competence_level)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def get_user_by_username(self, db: Session, username: str) -> Optional[models.User]:
        """Get user by username"""
        return db.query(models.User).filter(models.User.username == username).first()

    def get_user_proficiency(self, db: Session, user_id: int) -> schemas.UserProficiency:
        """Get user's proficiency across all subjects"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        proficiencies = db.query(models.UserProficiency).filter(
            models.UserProficiency.user_id == user_id
        ).all()

        proficiency_list = []
        for prof in proficiencies:
            proficiency_list.append(schemas.UserProficiencySubject(
                subject=prof.subject,
                theta=prof.theta,
                sem=prof.sem,
                tier=prof.tier,
                assessments_taken=prof.assessments_taken,
                last_updated=prof.last_updated
            ))

        return schemas.UserProficiency(
            username=user.username,
            proficiencies=proficiency_list
        )

    def update_user_proficiency(self, db: Session, user_id: int, subject: str, 
                               theta: float, sem: float, tier: str):
        """Update or create user proficiency for a subject"""
        proficiency = db.query(models.UserProficiency).filter(
            and_(
                models.UserProficiency.user_id == user_id,
                models.UserProficiency.subject == subject
            )
        ).first()

        if proficiency:
            proficiency.theta = theta
            proficiency.sem = sem
            proficiency.tier = tier
            proficiency.assessments_taken += 1
        else:
            proficiency = models.UserProficiency(
                user_id=user_id,
                subject=subject,
                theta=theta,
                sem=sem,
                tier=tier,
                assessments_taken=1
            )
            db.add(proficiency)

        db.commit()

class QuestionService:
    def import_questions_from_df(self, db: Session, df: pd.DataFrame) -> int:
        """Import questions from pandas DataFrame"""
        imported_count = 0

        for _, row in df.iterrows():
            # Check if question already exists
            existing = db.query(models.Question).filter(
                models.Question.question_id == row['question_id']
            ).first()

            if not existing:
                question = models.Question(
                    subject=row['subject'],
                    question_id=row['question_id'],
                    question=row['question'],
                    option_a=row['option_a'],
                    option_b=row['option_b'],
                    option_c=row['option_c'],
                    option_d=row['option_d'],
                    answer=row['answer'],
                    topic=row['topic'],
                    tier=row['tier'],
                    discrimination_a=float(row['discrimination_a']),
                    difficulty_b=float(row['difficulty_b']),
                    guessing_c=float(row['guessing_c']),
                    selected_option_text=row.get('selected_option_text', '')
                )
                db.add(question)
                imported_count += 1

        db.commit()
        return imported_count

    def get_available_questions(self, db: Session, session_id: int, subject: str) -> List[Dict]:
        """Get available questions for a session (not yet asked)"""
        asked_question_ids = db.query(models.Response.question_id).filter(
            models.Response.session_id == session_id
        ).subquery()

        questions = db.query(models.Question).filter(
            and_(
                models.Question.subject == subject,
                not_(models.Question.id.in_(asked_question_ids))
            )
        ).all()

        return [
            {
                'id': q.id,
                'question_id': q.question_id,
                'question': q.question,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'answer': q.answer,
                'topic': q.topic,
                'tier': q.tier,
                'discrimination_a': q.discrimination_a,
                'difficulty_b': q.difficulty_b,
                'guessing_c': q.guessing_c
            }
            for q in questions
        ]

    def get_question_by_id(self, db: Session, question_id: int) -> Optional[models.Question]:
        """Get question by ID"""
        return db.query(models.Question).filter(models.Question.id == question_id).first()
'''

    # Create services.py with the continuation
    services_py_part2 = '''
class AssessmentService:
    def __init__(self):
        self.user_service = UserService()
        self.question_service = QuestionService()

    def start_assessment(self, db: Session, user_id: int, subject: str) -> models.AssessmentSession:
        """Start a new assessment session"""
        # Get user's previous proficiency for this subject
        user_proficiency = db.query(models.UserProficiency).filter(
            and_(
                models.UserProficiency.user_id == user_id,
                models.UserProficiency.subject == subject
            )
        ).first()

        # Set initial theta based on proficiency or competence level
        if user_proficiency:
            initial_theta = user_proficiency.theta
        else:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            irt_engine = IRTEngine()
            initial_theta = irt_engine.get_initial_theta(user.competence_level)

        session = models.AssessmentSession(
            user_id=user_id,
            subject=subject,
            initial_theta=initial_theta,
            current_theta=initial_theta,
            current_sem=1.0
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        return session

    def get_session(self, db: Session, session_id: int) -> Optional[models.AssessmentSession]:
        """Get assessment session by ID"""
        return db.query(models.AssessmentSession).filter(
            models.AssessmentSession.id == session_id
        ).first()

    def get_next_question(self, db: Session, session_id: int, 
                         irt_engine: IRTEngine) -> Optional[schemas.QuestionResponse]:
        """Get next question for assessment"""
        session = self.get_session(db, session_id)
        if not session or session.is_completed:
            return None

        # Get response history
        responses = db.query(models.Response).filter(
            models.Response.session_id == session_id
        ).order_by(models.Response.created_at).all()

        response_history = [r.is_correct for r in responses]

        # Get available questions
        available_questions = self.question_service.get_available_questions(
            db, session_id, session.subject
        )

        if not available_questions:
            # No more questions available, complete assessment
            session.is_completed = True
            session.completed_at = datetime.utcnow()
            db.commit()
            return None

        # Select next question using IRT engine
        next_question_data = irt_engine.select_next_question(
            session.current_theta, available_questions, response_history
        )

        if not next_question_data:
            return None

        return schemas.QuestionResponse(
            id=next_question_data['id'],
            question=next_question_data['question'],
            option_a=next_question_data['option_a'],
            option_b=next_question_data['option_b'],
            option_c=next_question_data['option_c'],
            option_d=next_question_data['option_d'],
            topic=next_question_data['topic'],
            tier=next_question_data['tier']
        )

    def record_response(self, db: Session, session_id: int, question_id: int, 
                       selected_option: str, irt_engine: IRTEngine):
        """Record a response and update theta"""
        session = self.get_session(db, session_id)
        question = self.question_service.get_question_by_id(db, question_id)

        if not session or not question:
            return

        # Check if answer is correct
        is_correct = selected_option.upper() == question.answer.upper()

        # Get all previous responses for theta calculation
        previous_responses = db.query(models.Response).filter(
            models.Response.session_id == session_id
        ).all()

        # Prepare response data for theta update
        response_data = [
            (r.is_correct, 
             self.question_service.get_question_by_id(db, r.question_id).difficulty_b,
             self.question_service.get_question_by_id(db, r.question_id).discrimination_a,
             self.question_service.get_question_by_id(db, r.question_id).guessing_c)
            for r in previous_responses
        ]

        # Add current response
        response_data.append((
            is_correct,
            question.difficulty_b,
            question.discrimination_a,
            question.guessing_c
        ))

        # Update theta
        theta_before = session.current_theta
        new_theta = irt_engine.update_theta(theta_before, response_data)

        # Calculate SEM
        questions_info = []
        for resp in previous_responses:
            q = self.question_service.get_question_by_id(db, resp.question_id)
            questions_info.append((q.difficulty_b, q.discrimination_a, q.guessing_c))

        # Add current question
        questions_info.append((question.difficulty_b, question.discrimination_a, question.guessing_c))

        new_sem = irt_engine.calculate_sem(new_theta, questions_info)

        # Record response
        response = models.Response(
            session_id=session_id,
            question_id=question_id,
            selected_option=selected_option,
            is_correct=is_correct,
            theta_before=theta_before,
            theta_after=new_theta,
            sem_after=new_sem
        )

        db.add(response)

        # Update session
        session.current_theta = new_theta
        session.current_sem = new_sem
        session.questions_asked += 1

        # Check if assessment should stop
        response_history = [r.is_correct for r in previous_responses] + [is_correct]

        if irt_engine.should_stop_assessment(new_sem, session.questions_asked, response_history):
            session.is_completed = True
            session.completed_at = datetime.utcnow()

            # Update user proficiency
            new_tier = irt_engine.theta_to_tier(new_theta)
            self.user_service.update_user_proficiency(
                db, session.user_id, session.subject, new_theta, new_sem, new_tier
            )

        db.commit()

    def get_assessment_results(self, db: Session, session_id: int) -> schemas.AssessmentResults:
        """Get assessment results"""
        session = self.get_session(db, session_id)
        responses = db.query(models.Response).filter(
            models.Response.session_id == session_id
        ).order_by(models.Response.created_at).all()

        # Calculate metrics
        correct_count = sum(1 for r in responses if r.is_correct)
        accuracy = correct_count / len(responses) if responses else 0.0

        # Prepare response details
        response_details = []
        for resp in responses:
            question = self.question_service.get_question_by_id(db, resp.question_id)
            response_details.append(schemas.ResponseDetails(
                question_id=resp.question_id,
                question=question.question,
                selected_option=resp.selected_option,
                correct_answer=question.answer,
                is_correct=resp.is_correct,
                theta_before=resp.theta_before,
                theta_after=resp.theta_after
            ))

        irt_engine = IRTEngine()
        final_tier = irt_engine.theta_to_tier(session.current_theta)

        return schemas.AssessmentResults(
            session_id=session.id,
            user_id=session.user_id,
            subject=session.subject,
            final_theta=session.current_theta,
            final_sem=session.current_sem,
            tier=final_tier,
            questions_asked=session.questions_asked,
            correct_answers=correct_count,
            accuracy=accuracy,
            responses=response_details,
            completed_at=session.completed_at
        )
'''

    create_file("services.py", services_py_part1 + services_py_part2)

    # Sample CSV data
    sample_csv = '''subject,question_id,question,option_a,option_b,option_c,option_d,answer,topic,tier,discrimination_a,difficulty_b,guessing_c,selected_option_text
Vocabulary,Q001,What is the meaning of VITUPERATIVE?,Praising,Harshly critical,Kind,Gentle,B,Advanced Vocabulary,C1,1.2,-0.8,0.25,Harshly critical
Vocabulary,Q002,What does EPHEMERAL mean?,Permanent,Lasting,Brief,Eternal,C,Time Concepts,C2,1.1,-0.3,0.25,Brief
Vocabulary,Q003,UBIQUITOUS means:,Rare,Everywhere,Hidden,Occasional,B,Descriptive Words,C2,1.0,0.1,0.25,Everywhere
Vocabulary,Q004,What is PERSPICACIOUS?,Confused,Clear-sighted,Blind,Uncertain,B,Mental Qualities,C3,1.3,0.7,0.25,Clear-sighted
Vocabulary,Q005,TRUCULENT means:,Peaceful,Aggressive,Calm,Gentle,B,Behavioral Traits,C3,1.2,0.9,0.25,Aggressive
Vocabulary,Q006,What does RECONDITE mean?,Simple,Obscure,Clear,Popular,B,Complexity,C4,1.4,1.2,0.25,Obscure
Vocabulary,Q007,PUSILLANIMOUS describes someone who is:,Brave,Cowardly,Strong,Bold,B,Character Traits,C1,0.9,-1.2,0.25,Cowardly
Vocabulary,Q008,What is DILATORY behavior?,Prompt,Delayed,Quick,Efficient,B,Time-related,C2,1.1,-0.1,0.25,Delayed
Vocabulary,Q009,SANGUINE means:,Pessimistic,Optimistic,Angry,Sad,B,Emotional States,C2,1.0,0.2,0.25,Optimistic
Vocabulary,Q010,What does PELLUCID mean?,Murky,Clear,Dark,Cloudy,B,Clarity,C3,1.2,0.6,0.25,Clear
Vocabulary,Q011,OSTENTATIOUS behavior is:,Modest,Showy,Quiet,Simple,B,Behavior,C2,1.0,0.3,0.25,Showy
Vocabulary,Q012,What is INDEFATIGABLE?,Tired,Tireless,Lazy,Weak,B,Energy Levels,C3,1.3,0.8,0.25,Tireless
Vocabulary,Q013,PENURIOUS means:,Generous,Stingy,Rich,Wasteful,B,Financial Traits,C4,1.5,1.4,0.25,Stingy
Vocabulary,Q014,What does SUPERCILIOUS mean?,Humble,Arrogant,Kind,Friendly,B,Attitude,C3,1.2,0.9,0.25,Arrogant
Vocabulary,Q015,LUGUBRIOUS describes something:,Cheerful,Mournful,Exciting,Happy,B,Mood,C4,1.4,1.3,0.25,Mournful
Vocabulary,Q016,What is MAGNANIMOUS behavior?,Petty,Generous,Selfish,Mean,B,Character,C2,1.1,0.0,0.25,Generous
Vocabulary,Q017,QUIXOTIC means:,Practical,Idealistic,Realistic,Sensible,B,Thinking Style,C4,1.5,1.5,0.25,Idealistic
Vocabulary,Q018,What does TERSE mean?,Wordy,Concise,Long,Detailed,B,Communication,C2,1.0,-0.2,0.25,Concise
Vocabulary,Q019,VINDICTIVE describes someone who is:,Forgiving,Vengeful,Kind,Merciful,B,Personality,C3,1.2,0.7,0.25,Vengeful
Vocabulary,Q020,What is VICARIOUS experience?,Direct,Indirect,Personal,Immediate,B,Experience Type,C3,1.3,0.8,0.25,Indirect
'''
    create_file("data/sample_questions/Vocabulary_C1.csv", sample_csv)

    # Import script
    import_script = '''#!/usr/bin/env python3
"""
Import questions from CSV file
"""
import sys
import os
import pandas as pd
from database import SessionLocal
from services import QuestionService

def import_questions(csv_file_path):
    """Import questions from CSV file"""
    if not os.path.exists(csv_file_path):
        print(f"Error: File {csv_file_path} not found")
        return

    print(f"Importing questions from {csv_file_path}...")

    df = pd.read_csv(csv_file_path)
    db = SessionLocal()

    try:
        question_service = QuestionService()
        imported_count = question_service.import_questions_from_df(db, df)
        print(f"Successfully imported {imported_count} questions")
    except Exception as e:
        print(f"Error importing questions: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_questions.py <csv_file_path>")
        sys.exit(1)

    csv_file_path = sys.argv[1]
    import_questions(csv_file_path)
'''
    create_file("scripts/import_questions.py", import_script)

    # Frontend files would be created separately
    print()
    print("=" * 60)
    print("🎉 ALL BACKEND FILES CREATED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print("📁 Files created:")
    print("   ✅ main.py - FastAPI application")
    print("   ✅ database.py - Database configuration")
    print("   ✅ models.py - SQLAlchemy models")
    print("   ✅ schemas.py - Pydantic schemas")
    print("   ✅ config.py - Configuration management")
    print("   ✅ irt_engine.py - IRT algorithm engine")
    print("   ✅ services.py - Business logic services")
    print("   ✅ data/sample_questions/Vocabulary_C1.csv - 20 sample questions")
    print("   ✅ scripts/import_questions.py - Question import utility")
    print()


if __name__ == "__main__":
    main()