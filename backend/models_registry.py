# backend/models_registry.py
"""Models for registry database (backend/data/registry.db)"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
import sys
import os

# Add scripts to path
scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

from database import Base


class User(Base):
    """Central user registry - single source of truth"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    initial_competence_level = Column(String, default="beginner")
    created_at = Column(DateTime, server_default=func.now())


class ItemBank(Base):
    """Registry of all item banks"""
    __tablename__ = "item_banks_registry"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    display_name = Column(String)
    subject = Column(String)
    irt_model = Column(String, default="3PL")
    status = Column(String, default="pending")
    total_items = Column(Integer, default=0)
    calibrated_items = Column(Integer, default=0)
    test_takers = Column(Integer, default=0)
    accuracy = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    last_calibrated = Column(DateTime, nullable=True)


class UserProficiencySummary(Base):
    """Cached proficiency summary for quick lookups"""
    __tablename__ = "user_proficiency_summary"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    item_bank_name = Column(String, index=True)
    subject = Column(String)
    theta = Column(Float)
    sem = Column(Float)
    tier = Column(String)
    assessments_taken = Column(Integer, default=0)
    topic_performance = Column(Text, nullable=True)  # REGISTRY_UPDATE: Cached topic performance JSON
    last_updated = Column(DateTime, server_default=func.now())