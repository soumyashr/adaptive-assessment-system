# backend/scripts/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get path to backend/data/registry.db
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
REGISTRY_DB_PATH = os.path.join(backend_dir, "data", "registry.db")

# Ensure data directory exists
os.makedirs(os.path.dirname(REGISTRY_DB_PATH), exist_ok=True)

# Create engine for registry
engine = create_engine(
    f"sqlite:///{REGISTRY_DB_PATH}",
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Get registry database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()