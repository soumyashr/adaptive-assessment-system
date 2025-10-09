from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from scripts.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    initial_competence_level = Column(String, default="beginner")  # Changed: more descriptive
    created_at = Column(DateTime, server_default=func.now())



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
    answer = Column(String)
    topic = Column(String, index=True)
    content_area = Column(String, nullable=True)
    tier = Column(String, index=True)
    discrimination_a = Column(Float)
    difficulty_b = Column(Float)
    guessing_c = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    # RELATIONSHIP_UPDATE: Enable querying responses from question
    responses = relationship("Response", back_populates="question")


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    session_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    theta = Column(Float)
    sem = Column(Float)
    tier = Column(String)
    questions_asked = Column(Integer, default=0)
    topic_performance = Column(Text, nullable=True)  # TOPIC_TRACKING_UPDATE: Store JSON topic performance data
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)

    # Relationships
    responses = relationship("Response", back_populates="session")

class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("assessment_sessions.session_id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    selected_option = Column(String)
    is_correct = Column(Boolean)
    response_time = Column(Float, nullable=True)
    theta_before = Column(Float)
    theta_after = Column(Float, nullable=True)
    sem_after = Column(Float, nullable=True)
    topic = Column(String, nullable=True)  # TOPIC_TRACKING_UPDATE: Link response to topic for analysis
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



class ItemBank(Base):
    """Registry of all item banks"""
    __tablename__ = "item_banks_registry"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    display_name = Column(String)
    subject = Column(String)
    model_type = Column(String, default="3PL")  # CONSISTENCY_FIX: Changed from irt_model to match services.py
    status = Column(String, default="pending")
    total_items = Column(Integer, default=0)
    calibrated_items = Column(Integer, default=0)
    test_takers = Column(Integer, default=0)
    accuracy = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    last_calibrated = Column(DateTime, nullable=True)