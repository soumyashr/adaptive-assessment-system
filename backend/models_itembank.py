# backend/models_itembank.py
"""Models for item bank databases (backend/data/*.db)"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
import sys
import os

# Add scripts to path
scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

from db_manager import Base


class Question(Base):
    """Questions in this item bank"""
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


class AssessmentSession(Base):
    """Assessment sessions in this item bank"""
    __tablename__ = "assessment_sessions"

    session_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)  # References registry.db users.id
    subject = Column(String)
    theta = Column(Float)
    sem = Column(Float)
    tier = Column(String)
    questions_asked = Column(Integer, default=0)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)


class Response(Base):
    """Individual responses in this item bank"""
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
    created_at = Column(DateTime, server_default=func.now())


class UserProficiency(Base):
    """User proficiency in this item bank"""
    __tablename__ = "user_proficiencies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)  # References registry.db users.id
    subject = Column(String)
    theta = Column(Float)
    sem = Column(Float)
    tier = Column(String)
    assessments_taken = Column(Integer, default=0)
    topic_performance = Column(Text, nullable=True)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())