# backend/scripts/db_manager.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys

Base = declarative_base()


class ItemBankDBManager:
    """Manage multiple item bank databases in backend/data/"""

    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)
        self.base_dir = os.path.join(backend_dir, "data")

        os.makedirs(self.base_dir, exist_ok=True)
        self.engines = {}
        self.session_makers = {}

    def get_db_path(self, item_bank_name: str) -> str:
        """Get database path for an item bank"""
        safe_name = "".join(c for c in item_bank_name if c.isalnum() or c in ('-', '_'))
        return os.path.join(self.base_dir, f"{safe_name}.db")

    def get_engine(self, item_bank_name: str):
        """Get or create engine for an item bank"""
        if item_bank_name not in self.engines:
            db_path = self.get_db_path(item_bank_name)
            self.engines[item_bank_name] = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False}
            )

            # Import item bank models ONLY (not User)
            backend_dir = os.path.dirname(self.base_dir)
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)

            import models_itembank
            # Create tables using item bank models
            models_itembank.Base.metadata.create_all(bind=self.engines[item_bank_name])

        return self.engines[item_bank_name]

    def get_session(self, item_bank_name: str):
        """Get database session for an item bank"""
        if item_bank_name not in self.session_makers:
            engine = self.get_engine(item_bank_name)
            self.session_makers[item_bank_name] = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            )
        return self.session_makers[item_bank_name]()

    def list_item_banks(self):
        """List all item banks in backend/data/"""
        if not os.path.exists(self.base_dir):
            return []

        banks = []
        for filename in os.listdir(self.base_dir):
            if filename.endswith('.db') and filename != 'registry.db':
                bank_name = filename[:-3]
                banks.append(bank_name)
        return banks


# Global item bank database manager
item_bank_db = ItemBankDBManager()