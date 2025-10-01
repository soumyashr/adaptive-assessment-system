from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    initial_competence_level = Column(String, default="beginner")  # Changed: more descriptive
    created_at = Column(DateTime, server_default=func.now())

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
    content_area = Column(String, nullable=True)  # Added: for IRT engine
    tier = Column(String, index=True)  # C1, C2, C3, C4
    discrimination_a = Column(Float)
    difficulty_b = Column(Float)
    guessing_c = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    responses = relationship("Response", back_populates="question")


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    session_id = Column(Integer, primary_key=True, index=True)  # Changed from 'id'
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    theta = Column(Float)  # Changed: single column instead of initial_theta/current_theta
    sem = Column(Float)    # Changed from current_sem
    tier = Column(String)  # Added: current tier
    questions_asked = Column(Integer, default=0)
    started_at = Column(DateTime, server_default=func.now())  # Changed from created_at
    completed_at = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)  # Changed from is_completed

    # Relationships
    user = relationship("User", back_populates="assessment_sessions")
    responses = relationship("Response", back_populates="session")


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("assessment_sessions.session_id"))  # Updated FK
    question_id = Column(Integer, ForeignKey("questions.id"))
    selected_option = Column(String)  # A, B, C, or D
    is_correct = Column(Boolean)
    response_time = Column(Float, nullable=True)  # Changed from response_time_ms
    theta_before = Column(Float)
    theta_after = Column(Float, nullable=True)  # Made nullable
    sem_after = Column(Float, nullable=True)    # Added
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
    topic_performance = Column(Text, nullable=True)  # Added: JSON storage
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="proficiencies")