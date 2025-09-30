from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship  # ← Fixed this line
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
