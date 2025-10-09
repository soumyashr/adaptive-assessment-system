#!/usr/bin/env python3
"""
Initialize database tables
creates all the SQLite database tables
(users, questions, assessment_sessions, responses, user_proficiencies)
"""
from scripts.database import engine
import models

def setup_database():
    """Create all database tables"""
    print("Creating database tables...")
    models.Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    setup_database()