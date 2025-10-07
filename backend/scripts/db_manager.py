# backend/scripts/db_manager.py

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from pathlib import Path
import logging
import os
import sys
import stat
import sqlite3
from typing import Optional, List, Dict
from contextlib import contextmanager

Base = declarative_base()
logger = logging.getLogger(__name__)


class ItemBankDBManager:
    """
    Manage multiple item bank databases in backend/data/

    Features:
    - Automatic permission fixing for SQLite databases
    - Connection pooling and proper cleanup
    - Thread-safe operations
    - Better error handling and logging
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

        # Add backend to path if needed
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        logger.info(f"ItemBankDBManager initialized with base_dir: {self.base_dir}")

    def cleanup(self, item_bank_name: Optional[str] = None) -> None:
        """
        Clean up connections and resources

        Args:
            item_bank_name: Specific item bank to clean up, or None for all
        """
        if item_bank_name:
            # Clean up specific item bank
            if item_bank_name in self.engines:
                try:
                    # Dispose of the engine (closes all connections)
                    self.engines[item_bank_name].dispose()
                    del self.engines[item_bank_name]
                    logger.info(f"Cleaned up engine for {item_bank_name}")
                except Exception as e:
                    logger.error(f"Error cleaning up engine: {e}")

            if item_bank_name in self.session_makers:
                try:
                    # Remove the scoped session
                    if hasattr(self.session_makers[item_bank_name], 'remove'):
                        self.session_makers[item_bank_name].remove()
                    del self.session_makers[item_bank_name]
                    logger.info(f"Cleaned up session maker for {item_bank_name}")
                except Exception as e:
                    logger.error(f"Error cleaning up session maker: {e}")
        else:
            # Clean up all
            for name in list(self.engines.keys()):
                self.cleanup(name)

            logger.info("Cleaned up all database connections")

    def _ensure_directory_exists(self) -> None:
        """Create data directory with proper permissions"""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)

            # Set directory permissions (775 - rwxrwxr-x)
            # This allows SQLite to create journal files
            os.chmod(self.base_dir, 0o775)
            logger.info(f"Data directory created/verified: {self.base_dir}")

        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")
            raise

    def _fix_db_permissions(self, db_path: Path) -> None:
        """Fix permissions for a database file"""
        try:
            if db_path.exists():
                # Set file permissions (664 - rw-rw-r--)
                os.chmod(db_path, 0o664)

                # Verify writability
                with sqlite3.connect(str(db_path), timeout=5.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")  # Use Write-Ahead Logging for better concurrency
                    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety and speed
                    conn.commit()

                logger.debug(f"Permissions fixed for: {db_path}")

        except Exception as e:
            logger.warning(f"Could not fix permissions for {db_path}: {e}")
            # Don't raise - let it fail later with a more specific error

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
        if item_bank_name not in self.engines:
            db_path = self.get_db_path(item_bank_name)

            # Fix permissions before creating engine
            self._fix_db_permissions(db_path)

            # Create engine with optimized settings
            engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={
                    "check_same_thread": False,  # Allow multiple threads
                    "timeout": 15,  # Increase timeout to handle locks
                    "isolation_level": None  # Use autocommit mode to reduce locks
                },
                poolclass=StaticPool,  # Better for SQLite
                echo=False  # Set to True for SQL debugging
            )

            # Set up event listeners for connection configuration
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                """Configure SQLite for better performance and concurrency"""
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
                cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
                cursor.execute("PRAGMA foreign_keys=ON")  # Enforce foreign keys
                cursor.execute("PRAGMA busy_timeout=5000")  # 5 second timeout
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
        if item_bank_name not in self.session_makers:
            engine = self.get_engine(item_bank_name)

            # Use scoped_session for thread safety
            session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
                expire_on_commit=False  # Prevent lazy loading issues
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
            # Session automatically closed
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
                if db_file.stem != 'registry' and not db_file.name.endswith('-journal'):
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
            'error': None
        }

        db_path = self.get_db_path(item_bank_name)

        try:
            # Check existence
            result['exists'] = db_path.exists()
            if not result['exists']:
                result['error'] = 'Database file does not exist'
                return result

            # Check readability
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

    def cleanup(self, item_bank_name: Optional[str] = None) -> None:
        """
        Clean up connections and resources

        Args:
            item_bank_name: Specific item bank to clean up, or None for all
        """
        if item_bank_name:
            # Clean up specific item bank
            if item_bank_name in self.engines:
                self.engines[item_bank_name].dispose()
                del self.engines[item_bank_name]
                logger.info(f"Cleaned up engine for {item_bank_name}")

            if item_bank_name in self.session_makers:
                self.session_makers[item_bank_name].remove()
                del self.session_makers[item_bank_name]

        else:
            # Clean up all
            for engine in self.engines.values():
                engine.dispose()
            self.engines.clear()

            for session_maker in self.session_makers.values():
                session_maker.remove()
            self.session_makers.clear()

            logger.info("Cleaned up all database connections")

    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during cleanup


# Global item bank database manager
item_bank_db = ItemBankDBManager()