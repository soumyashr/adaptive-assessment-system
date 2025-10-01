# verify_schema.py
import sqlite3

conn = sqlite3.connect('../adaptive_assessment.db')
cursor = conn.cursor()

print("=== assessment_sessions ===")
cursor.execute("PRAGMA table_info(assessment_sessions)")
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\n=== Expected columns ===")
print("  session_id: INTEGER (PK)")
print("  user_id: INTEGER")
print("  subject: VARCHAR")
print("  theta: REAL")
print("  sem: REAL")
print("  tier: VARCHAR")
print("  questions_asked: INTEGER")
print("  started_at: TEXT")
print("  completed_at: TEXT")
print("  completed: INTEGER")

conn.close()