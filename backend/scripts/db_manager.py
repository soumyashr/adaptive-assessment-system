# backend/scripts/db_manager.py

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool  # Changed from StaticPool
from pathlib import Path
import logging
import os
import sys
import stat
import sqlite3
import time
from typing import Optional, List, Dict
from contextlib import contextmanager
from datetime import datetime, timedelta

Base = declarative_base()
logger = logging.getLogger(__name__)


class ItemBankDBManager:
    """
    Manage multiple item bank databases in backend/data/

    Features:
    - Automatic permission fixing for SQLite databases
    - Connection pooling with automatic cleanup
    - Thread-safe operations
    - Better error handling and logging
    - Automatic idle connection cleanup
    """

    def __init__(self):
        # Use Path for better cross-platform compatibility
        script_dir = Path(__file__).parent.absolute()
        backend_dir = script_dir.parent
        self.base_dir = backend_dir / "data"

        # Create directory with proper permissions
        self._ensure_directory_exists()

        # Storage for engines and session makers
        self.engines: Dict[str, any] = {}
        self.session_makers: Dict[str, any] = {}

        # Track last access time for each item bank
        self.last_accessed: Dict[str, float] = {}

        # Configuration
        self.max_idle_time = 300  # 5 minutes in seconds
        self.use_wal_mode = True  # Can be configured

        # Add backend to path if needed
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        logger.info(f"ItemBankDBManager initialized with base_dir: {self.base_dir}")

    def _ensure_directory_exists(self) -> None:
        """Create data directory with proper permissions"""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)

            # Set directory permissions (775 - rwxrwxr-x)
            # This allows SQLite to create journal files
            os.chmod(self.base_dir, 0o775)
            logger.debug(f"Data directory created/verified: {self.base_dir}")

        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")
            raise

    def _fix_db_permissions(self, db_path: Path) -> None:
        """Fix permissions for a database file"""
        try:
            if db_path.exists():
                # Set file permissions (664 - rw-rw-r--)
                os.chmod(db_path, 0o664)

                # Verify writability and set journal mode
                with sqlite3.connect(str(db_path), timeout=5.0) as conn:
                    cursor = conn.cursor()
                    if self.use_wal_mode:
                        cursor.execute("PRAGMA journal_mode=WAL")
                    else:
                        cursor.execute("PRAGMA journal_mode=DELETE")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    conn.commit()
                    cursor.close()

                logger.debug(f"Permissions fixed for: {db_path}")

        except Exception as e:
            logger.warning(f"Could not fix permissions for {db_path}: {e}")

    def get_db_path(self, item_bank_name: str) -> Path:
        """
        Get database path for an item bank

        Args:
            item_bank_name: Name of the item bank

        Returns:
            Path object for the database file
        """
        # Sanitize the name for filesystem
        safe_name = "".join(c for c in item_bank_name if c.isalnum() or c in ('-', '_'))

        if safe_name != item_bank_name:
            logger.warning(f"Item bank name sanitized: '{item_bank_name}' -> '{safe_name}'")

        return self.base_dir / f"{safe_name}.db"

    def get_engine(self, item_bank_name: str):
        """
        Get or create engine for an item bank with proper configuration

        Args:
            item_bank_name: Name of the item bank

        Returns:
            SQLAlchemy engine instance
        """
        # Update last accessed time
        self.last_accessed[item_bank_name] = time.time()

        # Clean up idle connections periodically
        self.cleanup_idle()

        if item_bank_name not in self.engines:
            db_path = self.get_db_path(item_bank_name)

            # Fix permissions before creating engine
            self._fix_db_permissions(db_path)

            # Create engine with NullPool to avoid connection persistence
            engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={
                    "check_same_thread": False,
                    "timeout": 15,
                },
                poolclass=NullPool,  # No connection pooling - create/close each time
                echo=False
            )

            # Set up event listeners for connection configuration
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                """Configure SQLite for better performance and concurrency"""
                cursor = dbapi_conn.cursor()
                if self.use_wal_mode:
                    cursor.execute("PRAGMA journal_mode=WAL")
                else:
                    cursor.execute("PRAGMA journal_mode=DELETE")  # Cleaner - no WAL files
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.close()

            # Import and create tables
            try:
                import models_itembank
                models_itembank.Base.metadata.create_all(bind=engine)

                # Fix permissions after table creation
                self._fix_db_permissions(db_path)

                self.engines[item_bank_name] = engine
                logger.info(f"Created engine for item bank: {item_bank_name}")

            except Exception as e:
                logger.error(f"Failed to create engine for {item_bank_name}: {e}")
                raise

        return self.engines[item_bank_name]

    def get_session(self, item_bank_name: str):
        """
        Get database session for an item bank

        Args:
            item_bank_name: Name of the item bank

        Returns:
            SQLAlchemy session instance
        """
        # Update last accessed time
        self.last_accessed[item_bank_name] = time.time()

        if item_bank_name not in self.session_makers:
            engine = self.get_engine(item_bank_name)

            # Create session factory
            session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
                expire_on_commit=False
            )

            self.session_makers[item_bank_name] = scoped_session(session_factory)

        return self.session_makers[item_bank_name]()

    @contextmanager
    def get_session_context(self, item_bank_name: str):
        """
        Context manager for database sessions with automatic cleanup

        Usage:
            with item_bank_db.get_session_context('maths') as session:
                # Use session
                pass
            # Session automatically closed and cleaned up
        """
        session = self.get_session(item_bank_name)
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error for {item_bank_name}: {e}")
            raise
        finally:
            session.close()
            # Remove the scoped session to ensure cleanup
            if item_bank_name in self.session_makers:
                self.session_makers[item_bank_name].remove()

    def cleanup_idle(self, max_idle_time: Optional[int] = None) -> int:
        """
        Clean up connections that have been idle for too long

        Args:
            max_idle_time: Maximum idle time in seconds (uses self.max_idle_time if not provided)

        Returns:
            Number of connections cleaned up
        """
        if max_idle_time is None:
            max_idle_time = self.max_idle_time

        current_time = time.time()
        cleaned_count = 0

        # Find idle connections
        idle_banks = []
        for item_bank_name, last_access in list(self.last_accessed.items()):
            if current_time - last_access > max_idle_time:
                idle_banks.append(item_bank_name)

        # Clean up idle connections
        for item_bank_name in idle_banks:
            logger.debug(f"Cleaning up idle connection for {item_bank_name}")
            self.cleanup(item_bank_name)
            cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} idle database connections")

        return cleaned_count

    def checkpoint_wal(self, item_bank_name: str) -> bool:
        """
        Checkpoint WAL file to merge changes back to main database

        Args:
            item_bank_name: Name of the item bank

        Returns:
            True if successful, False otherwise
        """
        if not self.use_wal_mode:
            return True  # Nothing to do if not using WAL

        db_path = self.get_db_path(item_bank_name)

        try:
            # Close any existing connections first
            if item_bank_name in self.session_makers:
                self.session_makers[item_bank_name].remove()
            if item_bank_name in self.engines:
                self.engines[item_bank_name].dispose()

            # Checkpoint the WAL
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()

            logger.debug(f"Checkpointed WAL for {item_bank_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to checkpoint WAL for {item_bank_name}: {e}")
            return False

    def cleanup(self, item_bank_name: Optional[str] = None) -> None:
        """
        Clean up connections and resources

        Args:
            item_bank_name: Specific item bank to clean up, or None for all
        """
        if item_bank_name:
            # Clean up specific item bank
            try:
                # Remove from tracking
                if item_bank_name in self.last_accessed:
                    del self.last_accessed[item_bank_name]

                # Close session maker
                if item_bank_name in self.session_makers:
                    try:
                        self.session_makers[item_bank_name].remove()
                        del self.session_makers[item_bank_name]
                        logger.debug(f"Removed session maker for {item_bank_name}")
                    except Exception as e:
                        logger.error(f"Error removing session maker: {e}")

                # Dispose engine
                if item_bank_name in self.engines:
                    try:
                        self.engines[item_bank_name].dispose()
                        del self.engines[item_bank_name]
                        logger.debug(f"Disposed engine for {item_bank_name}")
                    except Exception as e:
                        logger.error(f"Error disposing engine: {e}")

                # Try to checkpoint WAL if in use
                if self.use_wal_mode:
                    self.checkpoint_wal(item_bank_name)

            except Exception as e:
                logger.error(f"Error during cleanup of {item_bank_name}: {e}")
        else:
            # Clean up all
            for name in list(self.engines.keys()):
                self.cleanup(name)

            self.last_accessed.clear()
            logger.info("Cleaned up all database connections")

    def list_item_banks(self) -> List[str]:
        """
        List all item banks in backend/data/

        Returns:
            List of item bank names
        """
        if not self.base_dir.exists():
            return []

        banks = []
        try:
            for db_file in self.base_dir.glob('*.db'):
                # Exclude registry.db and journal files
                if (db_file.stem != 'registry' and
                        not db_file.name.endswith('-journal') and
                        not db_file.name.endswith('-wal') and
                        not db_file.name.endswith('-shm')):
                    banks.append(db_file.stem)

            logger.debug(f"Found {len(banks)} item banks")
            return sorted(banks)

        except Exception as e:
            logger.error(f"Error listing item banks: {e}")
            return []

    def verify_item_bank(self, item_bank_name: str) -> Dict[str, any]:
        """
        Verify an item bank database is accessible and working

        Args:
            item_bank_name: Name of the item bank

        Returns:
            Dictionary with verification results
        """
        result = {
            'exists': False,
            'readable': False,
            'writable': False,
            'tables': [],
            'question_count': 0,
            'error': None
        }

        db_path = self.get_db_path(item_bank_name)

        try:
            # Check existence
            result['exists'] = db_path.exists()
            if not result['exists']:
                result['error'] = 'Database file does not exist'
                return result

            # Check readability and content
            with sqlite3.connect(str(db_path), timeout=5.0) as conn:
                cursor = conn.cursor()

                # Check tables
                cursor.execute("""
                               SELECT name
                               FROM sqlite_master
                               WHERE type = 'table'
                               ORDER BY name
                               """)
                result['tables'] = [row[0] for row in cursor.fetchall()]
                result['readable'] = True

                # Count questions if table exists
                if 'questions' in result['tables']:
                    cursor.execute("SELECT COUNT(*) FROM questions")
                    result['question_count'] = cursor.fetchone()[0]

                # Check writability
                cursor.execute("CREATE TABLE IF NOT EXISTS _test (id INTEGER)")
                cursor.execute("INSERT INTO _test VALUES (1)")
                cursor.execute("DELETE FROM _test")
                cursor.execute("DROP TABLE IF EXISTS _test")
                conn.commit()
                result['writable'] = True

        except sqlite3.OperationalError as e:
            if 'readonly' in str(e):
                result['error'] = 'Database is read-only'
            else:
                result['error'] = str(e)
        except Exception as e:
            result['error'] = str(e)

        return result

    def set_wal_mode(self, use_wal: bool) -> None:
        """
        Enable or disable WAL mode for new connections

        Args:
            use_wal: True for WAL mode, False for DELETE mode
        """
        self.use_wal_mode = use_wal
        logger.info(f"WAL mode set to: {use_wal}")

        # Clean up existing connections to apply new setting
        self.cleanup()

    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during cleanup


# Global item bank database manager
item_bank_db = ItemBankDBManager()

# Optional: Set to DELETE mode if the preference is  WAL files
# But this will affect performance
# item_bank_db.set_wal_mode(False)