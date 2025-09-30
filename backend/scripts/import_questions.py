#!/usr/bin/env python3
"""
Import questions from CSV file with proper import paths
"""
import sys
import os
import pandas as pd

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the backend directory (parent of scripts)
backend_dir = os.path.dirname(script_dir)
# Add backend directory to the beginning of Python path
sys.path.insert(0, backend_dir)

# Now import our local modules
from database import SessionLocal
from services import QuestionService


def import_questions(csv_file_path):
    """Import questions from CSV file"""
    if not os.path.exists(csv_file_path):
        print(f"Error: File {csv_file_path} not found")
        return

    print(f"Importing questions from {csv_file_path}...")
    print(f"Backend directory: {backend_dir}")

    # Try multiple encodings for the CSV file
    encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    df = None
    for encoding in encodings_to_try:
        try:
            print(f"Trying encoding: {encoding}")
            df = pd.read_csv(csv_file_path, encoding=encoding)
            print(f"Successfully read CSV with encoding: {encoding}")
            break
        except UnicodeDecodeError as e:
            print(f"Failed with {encoding}: {e}")
            continue
        except Exception as e:
            print(f"Error with {encoding}: {e}")
            break

    if df is None:
        print("Error: Could not read CSV with any encoding")
        return

    print(f"CSV has {len(df)} rows and {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")

    # Check required columns
    required_columns = ['subject', 'question_id', 'question', 'option_a', 'option_b',
                        'option_c', 'option_d', 'answer', 'topic', 'tier',
                        'discrimination_a', 'difficulty_b', 'guessing_c']

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Missing required columns: {missing_columns}")
        print(f"Available columns: {list(df.columns)}")
        return

    db = SessionLocal()

    try:
        question_service = QuestionService()
        imported_count = question_service.import_questions_from_df(db, df)
        print(f"Successfully imported {imported_count} questions")
    except Exception as e:
        print(f"Error importing questions: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_questions.py <csv_file_path>")
        print("Example: python import_questions.py ../data/sample_questions/Vocabulary_C1.csv")
        sys.exit(1)

    csv_file_path = sys.argv[1]
    import_questions(csv_file_path)