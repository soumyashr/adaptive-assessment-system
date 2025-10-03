#!/usr/bin/env python3
"""
SAFE ADDITIVE MIGRATION - No Breaking Changes
Only adds new columns/tables, doesn't modify existing structure
Run this ONCE before deploying new code
"""

import sqlite3
import os
from pathlib import Path


def safe_add_column(cursor, table, column, column_type, default=None):
    """Safely add column only if it doesn't exist"""
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]

        if column not in columns:
            default_clause = f"DEFAULT {default}" if default else ""
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type} {default_clause}")
            print(f"  ✓ Added {column} to {table}")
            return True
        else:
            print(f"  → Column {column} already exists in {table}")
            return False
    except Exception as e:
        print(f"  ✗ Error adding {column} to {table}: {e}")
        return False


def safe_create_table(cursor, table_name, create_sql):
    """Safely create table only if it doesn't exist"""
    try:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            cursor.execute(create_sql)
            print(f"  ✓ Created table {table_name}")
            return True
        else:
            print(f"  → Table {table_name} already exists")
            return False
    except Exception as e:
        print(f"  ✗ Error creating {table_name}: {e}")
        return False


def safe_create_index(cursor, index_name, create_sql):
    """Safely create index only if it doesn't exist"""
    try:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'")
        if not cursor.fetchone():
            cursor.execute(create_sql)
            print(f"  ✓ Created index {index_name}")
            return True
        else:
            print(f"  → Index {index_name} already exists")
            return False
    except Exception as e:
        print(f"  ✗ Error creating {index_name}: {e}")
        return False


def migrate_database(db_path):
    """SAFE migration - only adds, never modifies existing structure"""
    print(f"\nMigrating: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Add new columns (will be NULL for existing rows - safe)
        safe_add_column(cursor, 'assessment_sessions', 'topic_performance', 'TEXT')
        safe_add_column(cursor, 'responses', 'topic', 'TEXT')
        safe_add_column(cursor, 'user_proficiencies', 'topic_performance', 'TEXT')

        # 2. Create new table (doesn't affect existing tables)
        safe_create_table(cursor, 'topic_performance', """
                                                       CREATE TABLE topic_performance
                                                       (
                                                           id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                                                           session_id         INTEGER,
                                                           user_id            INTEGER,
                                                           topic              TEXT,
                                                           theta              REAL,
                                                           sem                REAL,
                                                           questions_answered INTEGER   DEFAULT 0,
                                                           correct_count      INTEGER   DEFAULT 0,
                                                           accuracy           REAL,
                                                           tier               TEXT,
                                                           created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                           FOREIGN KEY (session_id) REFERENCES assessment_sessions (session_id)
                                                       )
                                                       """)

        # 3. Create indexes (improves performance, doesn't break anything)
        safe_create_index(cursor, 'idx_topic_performance_session',
                          "CREATE INDEX idx_topic_performance_session ON topic_performance(session_id)")
        safe_create_index(cursor, 'idx_topic_performance_user',
                          "CREATE INDEX idx_topic_performance_user ON topic_performance(user_id)")
        safe_create_index(cursor, 'idx_topic_performance_topic',
                          "CREATE INDEX idx_topic_performance_topic ON topic_performance(topic)")
        safe_create_index(cursor, 'idx_responses_topic',
                          "CREATE INDEX idx_responses_topic ON responses(topic)")

        # 4. Backfill topic data ONLY if topic column is empty (safe)
        cursor.execute("SELECT COUNT(*) FROM responses WHERE topic IS NOT NULL")
        if cursor.fetchone()[0] == 0:
            print("  → Backfilling topic data from questions...")
            cursor.execute("""
                           UPDATE responses
                           SET topic = (SELECT questions.topic
                                        FROM questions
                                        WHERE questions.id = responses.question_id)
                           WHERE topic IS NULL
                           """)
            cursor.execute("SELECT changes()")
            updated = cursor.fetchone()[0]
            print(f"  ✓ Topic data backfilled ({updated} rows updated)")
        else:
            print("  → Topic data already exists, skipping backfill")

        conn.commit()
        print(f"  ✓ Migration completed successfully\n")

    except Exception as e:
        print(f"  ✗ Error during migration: {e}\n")
        conn.rollback()
    finally:
        conn.close()


def migrate_all_databases():
    """Migrate all databases safely"""
    script_dir = Path(__file__).parent
    data_dir = script_dir / 'data'

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        print("Creating data directory...")
        data_dir.mkdir(parents=True, exist_ok=True)
        print("No databases to migrate yet.")
        return

    db_files = list(data_dir.glob('*.db'))

    if not db_files:
        print("No database files found in data directory")
        return

    print("=" * 60)
    print("SAFE ADDITIVE MIGRATION - No Breaking Changes")
    print("=" * 60)
    print(f"\nFound {len(db_files)} database(s) to migrate")

    for db_file in db_files:
        migrate_database(str(db_file))

    print("=" * 60)
    print("Migration completed! All existing functionality preserved.")
    print("=" * 60)


if __name__ == "__main__":
    migrate_all_databases()