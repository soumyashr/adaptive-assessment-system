#!/usr/bin/env python3
"""
Debug why assessment start fails with 404 after session creation
"""

import sqlite3
from pathlib import Path


def debug_assessment_issue():
    """Debug the assessment start 404 issue"""

    ITEM_BANK_NAME = 'maths_complex_nos'
    DATA_DIR = Path('/Users/soms/adaptive-assessment-system/backend/data')

    print("=" * 60)
    print("Assessment Start Debug for maths_complex_nos")
    print("=" * 60)

    # 1. Check registry
    print("\n1. Checking Registry Entry:")
    print("-" * 40)

    registry_db = DATA_DIR / 'registry.db'
    conn = sqlite3.connect(registry_db)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT name, display_name, subject, status, total_items
                   FROM item_banks_registry
                   WHERE name = ?
                   """, (ITEM_BANK_NAME,))

    row = cursor.fetchone()
    if row:
        print(f"  Name: {row[0]}")
        print(f"  Display: {row[1]}")
        print(f"  Subject: {row[2]}")  # THIS IS IMPORTANT
        print(f"  Status: {row[3]}")
        print(f"  Items: {row[4]}")
        registry_subject = row[2]
    else:
        print("  NOT FOUND in registry!")
        registry_subject = None

    conn.close()

    # 2. Check the actual database
    print("\n2. Checking Item Bank Database:")
    print("-" * 40)

    db_path = DATA_DIR / f'{ITEM_BANK_NAME}.db'
    if not db_path.exists():
        print(f"  ✗ Database file not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check questions table
    cursor.execute("""
                   SELECT COUNT(*),
                          COUNT(DISTINCT subject),
                          MIN(subject),
                          MAX(subject)
                   FROM questions
                   """)

    row = cursor.fetchone()
    print(f"  Total questions: {row[0]}")
    print(f"  Unique subjects: {row[1]}")
    print(f"  Subject values: '{row[2]}' to '{row[3]}'")

    # Get sample of subject values
    cursor.execute("""
                   SELECT DISTINCT subject, COUNT(*) as cnt
                   FROM questions
                   GROUP BY subject
                   ORDER BY cnt DESC LIMIT 5
                   """)

    print("\n  Subject Distribution:")
    for row in cursor.fetchall():
        print(f"    '{row[0]}': {row[1]} questions")

    # Check for NULL or empty subjects
    cursor.execute("""
                   SELECT COUNT(*)
                   FROM questions
                   WHERE subject IS NULL
                      OR subject = ''
                   """)

    null_count = cursor.fetchone()[0]
    if null_count > 0:
        print(f"\n  ⚠️  WARNING: {null_count} questions have NULL/empty subject!")

    # Check sample questions
    print("\n3. Sample Questions:")
    print("-" * 40)

    cursor.execute("""
                   SELECT id, question_id, subject, tier, topic
                   FROM questions LIMIT 3
                   """)

    for row in cursor.fetchall():
        print(f"  ID {row[0]}:")
        print(f"    question_id: {row[1]}")
        print(f"    subject: '{row[2]}'")
        print(f"    tier: {row[3]}")
        print(f"    topic: {row[4]}")

    # Check assessment sessions
    print("\n4. Recent Assessment Sessions:")
    print("-" * 40)

    cursor.execute("""
                   SELECT session_id, user_id, subject, questions_asked, completed
                   FROM assessment_sessions
                   ORDER BY session_id DESC LIMIT 3
                   """)

    sessions = cursor.fetchall()
    if sessions:
        for row in sessions:
            print(f"  Session {row[0]}:")
            print(f"    User: {row[1]}, Subject: '{row[2]}'")
            print(f"    Questions: {row[3]}, Completed: {row[4]}")
    else:
        print("  No sessions found")

    conn.close()

    # 5. Diagnosis
    print("\n5. DIAGNOSIS:")
    print("=" * 60)

    if registry_subject:
        print(f"Registry says subject should be: '{registry_subject}'")
        print("\nThe 404 error likely means:")
        print("1. The 'subject' field in questions doesn't match the registry")
        print("2. Questions were uploaded with wrong/missing subject field")
        print("3. The assessment is looking for the wrong subject")

        print("\nTO FIX:")
        print("-" * 40)
        print("Option 1: Update questions to match registry subject")
        print(f"""
import sqlite3
conn = sqlite3.connect('{db_path}')
cursor = conn.cursor()
cursor.execute("UPDATE questions SET subject = ?", ('{registry_subject}',))
conn.commit()
print(f"Updated {{cursor.rowcount}} questions")
conn.close()
""")

        print("\nOption 2: If questions have different subject, update the CSV")
        print("and re-upload with the correct subject field matching the registry")


def fix_subject_mismatch(item_bank_name='maths_complex_nos'):
    """Fix subject mismatch between registry and questions"""

    DATA_DIR = Path('/Users/soms/adaptive-assessment-system/backend/data')

    # Get registry subject
    registry_db = DATA_DIR / 'registry.db'
    conn = sqlite3.connect(registry_db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT subject FROM item_banks_registry WHERE name = ?",
        (item_bank_name,)
    )
    registry_subject = cursor.fetchone()[0]
    conn.close()

    print(f"Registry subject: '{registry_subject}'")

    # Update questions
    db_path = DATA_DIR / f'{item_bank_name}.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check current subjects
    cursor.execute("SELECT DISTINCT subject FROM questions")
    current_subjects = [row[0] for row in cursor.fetchall()]
    print(f"Current subjects in questions: {current_subjects}")

    if registry_subject not in current_subjects:
        print(f"Updating all questions to subject='{registry_subject}'...")
        cursor.execute(
            "UPDATE questions SET subject = ?",
            (registry_subject,)
        )
        conn.commit()
        print(f"✓ Updated {cursor.rowcount} questions")
    else:
        print("✓ Subject already matches!")

    conn.close()


if __name__ == "__main__":
    debug_assessment_issue()

    print("\n" + "=" * 60)
    print("Fix Subject Mismatch?")
    print("=" * 60)

    response = input("Do you want to fix the subject mismatch? (y/n): ")
    if response.lower() == 'y':
        fix_subject_mismatch()
        print("\n✓ Fixed! Try starting the assessment again.")