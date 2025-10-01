#!/usr/bin/env python3
"""
Debug script to check question data
"""
from backend.scripts.database import SessionLocal
import models


def debug_questions():
    db = SessionLocal()

    try:
        questions = db.query(models.Question).limit(5).all()

        for q in questions:
            print(f"Question ID: {q.question_id}")
            print(f"Question: {q.question}")
            print(f"Option A: {q.option_a}")
            print(f"Option B: {q.option_b}")
            print(f"Option C: {q.option_c}")
            print(f"Option D: {q.option_d}")
            print(f"Correct Answer: '{q.answer}' (type: {type(q.answer)})")
            print(f"Answer text: {q.selected_option_text}")

    finally:
        db.close()


if __name__ == "__main__":
    debug_questions()