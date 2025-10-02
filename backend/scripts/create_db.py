# backend/scripts/create_db.py

import sys
import os

# Get absolute paths
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)

# Add backend to path
sys.path.insert(0, backend_dir)

# Import from same directory
from database import Base, engine

# Import registry models only
import models_registry

print("Dropping all tables in registry database...")
Base.metadata.drop_all(bind=engine)

print("Creating tables in registry database...")
Base.metadata.create_all(bind=engine)

print("✓ Registry database recreated successfully")
print(f"   Location: {os.path.join(backend_dir, 'data', 'registry.db')}")
print("\nTables created:")
print("  - users")
print("  - item_banks_registry")
print("  - user_proficiency_summary")