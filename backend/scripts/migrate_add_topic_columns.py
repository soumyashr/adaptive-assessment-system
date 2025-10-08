# backend/scripts/migrate_add_topic_columns.py
"""
TOPIC_TRACKING_UPDATE: Migration script to add topic-related columns to existing databases
This allows existing databases to support the new topic performance tracking features

Location: backend/scripts/migrate_add_topic_columns.py
Database Location: backend/data/*.db
Run from: backend/ directory using: python scripts/migrate_add_topic_columns.py
"""

import sqlite3
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_registry_db(db_name: str) -> bool:
    """Check if this is the registry database"""
    return db_name.lower() == 'registry.db'


def has_tables(db_path: str) -> bool:
    """SAFETY_CHECK: Check if database has any tables"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        return len(tables) > 0
    except Exception as e:
        logger.error(f"Error checking tables: {e}")
        return False


def table_exists(cursor, table_name: str) -> bool:
    """SAFETY_CHECK: Check if a specific table exists"""
    cursor.execute(f"""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='{table_name}'
    """)
    return cursor.fetchone() is not None


def migrate_registry_database(db_path: str, db_name: str) -> bool:
    """
    REGISTRY_MIGRATION: Migrate registry.db
    - Add topic_performance to user_proficiency_summary
    - Drop topic_performance table (wrong location)
    """

    if not os.path.exists(db_path):
        logger.warning(f"{db_name}: Database not found")
        return False

    # SAFETY_CHECK: Skip empty databases
    if not has_tables(db_path):
        logger.warning(f"{db_name}: Database is empty - skipping")
        return True

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        logger.info(f"{db_name}: This is the REGISTRY database - special migration")

        # SAFETY_CHECK: Only migrate if user_proficiency_summary exists
        if not table_exists(cursor, 'user_proficiency_summary'):
            logger.warning(f"{db_name}: user_proficiency_summary table not found - skipping")
            conn.close()
            return True

        # REGISTRY_MIGRATION: Check and add topic_performance to user_proficiency_summary
        cursor.execute("PRAGMA table_info(user_proficiency_summary)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'topic_performance' not in columns:
            logger.info(f"{db_name}: Adding topic_performance to user_proficiency_summary")
            cursor.execute("""
                           ALTER TABLE user_proficiency_summary
                               ADD COLUMN topic_performance TEXT
                           """)
            conn.commit()
            logger.info(f"{db_name}: ✓ topic_performance added to user_proficiency_summary")
        else:
            logger.info(f"{db_name}: topic_performance already exists in user_proficiency_summary")

        # REGISTRY_MIGRATION: Drop topic_performance table if it exists (wrong architecture)
        if table_exists(cursor, 'topic_performance'):
            logger.info(f"{db_name}: Dropping topic_performance table (belongs in item banks, not registry)")
            cursor.execute("DROP TABLE IF EXISTS topic_performance")
            conn.commit()
            logger.info(f"{db_name}: ✓ topic_performance table dropped")
        else:
            logger.info(f"{db_name}: No topic_performance table to drop")

        logger.info(f"{db_name}: ✅ Registry migration completed successfully\n")
        return True

    except Exception as e:
        logger.error(f"{db_name}: ❌ Migration failed - {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def migrate_item_bank_database(db_path: str, db_name: str) -> bool:
    """
    ITEM_BANK_MIGRATION: Migrate individual item bank database
    - Add topic_performance to assessment_sessions
    - Add topic to responses
    - Add topic_performance to user_proficiencies
    - Create topic_performance table
    """

    if not os.path.exists(db_path):
        logger.warning(f"{db_name}: Database not found")
        return False

    # SAFETY_CHECK: Skip empty databases
    if not has_tables(db_path):
        logger.info(f"{db_name}: Database is empty (no tables) - skipping migration")
        logger.info(f"{db_name}: Tables will be created automatically on first use\n")
        return True

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # SAFETY_CHECK: Check if this database has assessment tables
        has_assessment_tables = table_exists(cursor, 'assessment_sessions')

        if not has_assessment_tables:
            logger.info(f"{db_name}: No assessment_sessions table - database not yet used for assessments")
            logger.info(f"{db_name}: Migration not needed - tables will be created on first use\n")
            conn.close()
            return True

        # ITEM_BANK_MIGRATION: Check and add topic_performance to assessment_sessions
        cursor.execute("PRAGMA table_info(assessment_sessions)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'topic_performance' not in columns:
            logger.info(f"{db_name}: Adding topic_performance to assessment_sessions")
            cursor.execute("""
                           ALTER TABLE assessment_sessions
                               ADD COLUMN topic_performance TEXT
                           """)
            conn.commit()
            logger.info(f"{db_name}: ✓ topic_performance added to assessment_sessions")
        else:
            logger.info(f"{db_name}: topic_performance already exists in assessment_sessions")

        # ITEM_BANK_MIGRATION: Check and add topic to responses (if table exists)
        if table_exists(cursor, 'responses'):
            cursor.execute("PRAGMA table_info(responses)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'topic' not in columns:
                logger.info(f"{db_name}: Adding topic to responses")
                cursor.execute("""
                               ALTER TABLE responses
                                   ADD COLUMN topic VARCHAR
                               """)
                conn.commit()
                logger.info(f"{db_name}: ✓ topic added to responses")
            else:
                logger.info(f"{db_name}: topic already exists in responses")

        # ITEM_BANK_MIGRATION: Check and add topic_performance to user_proficiencies (if table exists)
        if table_exists(cursor, 'user_proficiencies'):
            cursor.execute("PRAGMA table_info(user_proficiencies)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'topic_performance' not in columns:
                logger.info(f"{db_name}: Adding topic_performance to user_proficiencies")
                cursor.execute("""
                               ALTER TABLE user_proficiencies
                                   ADD COLUMN topic_performance TEXT
                               """)
                conn.commit()
                logger.info(f"{db_name}: ✓ topic_performance added to user_proficiencies")
            else:
                logger.info(f"{db_name}: topic_performance already exists in user_proficiencies")

        # ITEM_BANK_MIGRATION: Create topic_performance table if it doesn't exist
        if not table_exists(cursor, 'topic_performance'):
            logger.info(f"{db_name}: Creating topic_performance table")
            cursor.execute("""
                           CREATE TABLE topic_performance
                           (
                               id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                               session_id         INTEGER,
                               user_id            INTEGER,
                               topic              VARCHAR,
                               theta              FLOAT,
                               sem                FLOAT,
                               questions_answered INTEGER  DEFAULT 0,
                               correct_count      INTEGER  DEFAULT 0,
                               accuracy           FLOAT,
                               tier               VARCHAR,
                               created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
                               FOREIGN KEY (session_id) REFERENCES assessment_sessions (session_id)
                           )
                           """)
            conn.commit()
            logger.info(f"{db_name}: ✓ topic_performance table created")

            # ITEM_BANK_MIGRATION: Create indexes for performance
            logger.info(f"{db_name}: Creating indexes...")
            cursor.execute("""
                           CREATE INDEX IF NOT EXISTS idx_topic_perf_session
                               ON topic_performance(session_id)
                           """)
            cursor.execute("""
                           CREATE INDEX IF NOT EXISTS idx_topic_perf_user
                               ON topic_performance(user_id)
                           """)
            cursor.execute("""
                           CREATE INDEX IF NOT EXISTS idx_topic_perf_topic
                               ON topic_performance(topic)
                           """)
            conn.commit()
            logger.info(f"{db_name}: ✓ Indexes created")
        else:
            logger.info(f"{db_name}: topic_performance table already exists")

        logger.info(f"{db_name}: ✅ Item bank migration completed successfully\n")
        return True

    except Exception as e:
        logger.error(f"{db_name}: ❌ Migration failed - {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def migrate_all_databases():
    """
    Migrate all databases in the backend/data directory

    PATH_FIX: Script must be run from backend/ directory
    PATH_FIX: Command: python scripts/migrate_add_topic_columns.py
    PATH_FIX: Database location: backend/data/*.db
    """

    # PATH_FIX: Get correct paths
    script_path = Path(__file__).resolve()
    scripts_dir = script_path.parent
    backend_dir = scripts_dir.parent
    data_dir = backend_dir / 'data'

    logger.info("\n" + "=" * 70)
    logger.info("PATH INFORMATION")
    logger.info("=" * 70)
    logger.info(f"Script location: {script_path}")
    logger.info(f"Backend directory: {backend_dir}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Data directory exists: {data_dir.exists()}")
    logger.info("=" * 70 + "\n")

    # PATH_FIX: Verify structure
    if not backend_dir.name == 'backend':
        logger.error("❌ ERROR: This script must be in backend/scripts/ directory")
        logger.error(f"Current backend directory: {backend_dir}")
        return

    # PATH_FIX: Check if data directory exists
    if not data_dir.exists():
        logger.error(f"❌ Data directory not found: {data_dir}")
        logger.error("Expected to run from: backend/")
        logger.error("Command: python scripts/migrate_add_topic_columns.py")
        return

    logger.info("=" * 70)
    logger.info("TOPIC TRACKING DATABASE MIGRATION")
    logger.info("=" * 70)
    logger.info("Registry DB: Cache topic performance in user_proficiency_summary")
    logger.info("Item Banks: Add topic tracking to sessions, responses, proficiencies")
    logger.info("Empty DBs: Will be skipped (tables created on first use)")
    logger.info("=" * 70 + "\n")

    # Get all .db files
    all_db_files = sorted(data_dir.glob('*.db'))

    if not all_db_files:
        logger.warning(f"⚠️  No .db files found in: {data_dir}")
        return

    logger.info(f"Found {len(all_db_files)} database file(s):")
    for db_file in all_db_files:
        file_size = db_file.stat().st_size
        size_str = f"{file_size:,} bytes" if file_size > 0 else "EMPTY"
        db_type = "REGISTRY" if is_registry_db(db_file.name) else "ITEM BANK"
        logger.info(f"  • {db_file.name} ({db_type}) - {size_str}")
    logger.info("")

    # Migrate each database with appropriate strategy
    migrated_count = 0
    skipped_count = 0
    failed_count = 0

    for db_file in all_db_files:
        logger.info("=" * 70)
        logger.info(f"🗃️  Processing: {db_file.name}")
        logger.info("=" * 70)
        logger.info(f"Location: {db_file}")
        logger.info(f"Size: {db_file.stat().st_size:,} bytes")

        # MIGRATION_STRATEGY: Use different migration logic based on database type
        if is_registry_db(db_file.name):
            success = migrate_registry_database(str(db_file), db_file.name)
        else:
            success = migrate_item_bank_database(str(db_file), db_file.name)

        if success:
            # Check if it was actually migrated or just skipped
            if db_file.stat().st_size == 0 or not has_tables(str(db_file)):
                skipped_count += 1
            else:
                migrated_count += 1
        else:
            failed_count += 1

    # Summary
    logger.info("=" * 70)
    logger.info("✅ MIGRATION COMPLETE!")
    logger.info("=" * 70)
    logger.info(f"Migrated: {migrated_count} database(s)")
    logger.info(f"Skipped (empty/new): {skipped_count} database(s)")
    if failed_count > 0:
        logger.info(f"Failed: {failed_count} database(s)")
    logger.info("")
    logger.info("Registry: topic_performance cached in user_proficiency_summary")
    logger.info("Item Banks: Full topic tracking enabled")
    logger.info("Empty DBs: Will auto-create tables on first assessment")
    logger.info("")
    logger.info("You can now restart your application")
    logger.info("=" * 70)


if __name__ == "__main__":
    migrate_all_databases()