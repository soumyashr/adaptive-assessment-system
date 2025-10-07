#!/usr/bin/env python3
"""
Debug script to check item bank registry and fix mismatches
Works from any directory within the project
"""

import sqlite3
import os
from pathlib import Path
import sys


def find_project_root():
    """Find the project root directory (contains backend folder)"""
    current = Path.cwd()

    # Try common locations
    possible_roots = [
        current,  # Current directory
        current.parent,  # Parent directory
        current.parent.parent,  # Grandparent
    ]

    # Look for backend/data directory structure
    for root in possible_roots:
        if (root / 'backend' / 'data').exists():
            return root
        elif (root / 'data').exists() and 'backend' in str(current):
            # We might be inside backend already
            return root.parent

    # If we're in scripts directory
    if current.name == 'scripts' and current.parent.name == 'backend':
        return current.parent.parent
    elif current.name == 'backend':
        return current.parent

    # Last resort - look for registry.db
    for root in possible_roots:
        if (root / 'backend' / 'data' / 'registry.db').exists():
            return root
        if (root / 'data' / 'registry.db').exists():
            return root.parent

    return current


def check_registry():
    """Check what's in the registry database"""

    # Find the correct paths
    project_root = find_project_root()
    backend_dir = project_root / 'backend'
    data_dir = backend_dir / 'data'
    registry_db = data_dir / 'registry.db'

    print("Item Bank Registry Diagnostic")
    print("=" * 50)
    print(f"Project root: {project_root}")
    print(f"Backend dir: {backend_dir}")
    print(f"Data dir: {data_dir}")
    print()

    # Check if data directory exists
    if not data_dir.exists():
        print(f"✗ Data directory not found: {data_dir}")
        print("\nTrying to locate data directory...")

        # Look for any .db files
        for path in project_root.rglob('*.db'):
            print(f"  Found database: {path}")
            if path.name == 'registry.db':
                registry_db = path
                data_dir = path.parent
                print(f"  → Using data directory: {data_dir}")
                break

    # Check registry database
    if registry_db.exists():
        print(f"\n✓ Registry database found: {registry_db}")

        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
                       SELECT name
                       FROM sqlite_master
                       WHERE type = 'table'
                         AND name = 'item_banks_registry'
                       """)

        if not cursor.fetchone():
            print("✗ Table 'item_banks_registry' not found in registry.db")
            print("  The database might not be initialized properly.")
        else:
            # Check registered item banks
            cursor.execute("""
                           SELECT id, name, display_name, subject, status, total_items
                           FROM item_banks_registry
                           ORDER BY name
                           """)

            registered_banks = cursor.fetchall()
            print(f"\nRegistered Item Banks ({len(registered_banks)} found):")
            print("-" * 50)

            if registered_banks:
                for bank in registered_banks:
                    print(f"ID: {bank[0]}")
                    print(f"  Name: {bank[1]}")
                    print(f"  Display: {bank[2]}")
                    print(f"  Subject: {bank[3]}")
                    print(f"  Status: {bank[4]}")
                    print(f"  Items: {bank[5]}")
                    print()
            else:
                print("  (No item banks registered)")

        conn.close()
    else:
        print(f"\n✗ Registry database not found at: {registry_db}")
        print("\nPossible issues:")
        print("1. The database hasn't been created yet")
        print("2. It's in a different location")
        print("\nTo fix: Start the FastAPI server once to create the database")

    # Check actual database files
    print("\nDatabase Files in data directory:")
    print("-" * 50)

    if data_dir.exists():
        db_files = list(data_dir.glob('*.db'))

        if db_files:
            for db_file in sorted(db_files):
                print(f"  {db_file.name}")

                if db_file.name != 'registry.db':
                    # Check if it has questions
                    try:
                        conn = sqlite3.connect(db_file)
                        cursor = conn.cursor()

                        # Check if questions table exists
                        cursor.execute("""
                                       SELECT name
                                       FROM sqlite_master
                                       WHERE type = 'table'
                                         AND name = 'questions'
                                       """)

                        if cursor.fetchone():
                            cursor.execute("SELECT COUNT(*) FROM questions")
                            count = cursor.fetchone()[0]
                            print(f"    → {count} questions")
                        else:
                            print(f"    → No questions table")

                        conn.close()
                    except Exception as e:
                        print(f"    → Error reading: {e}")
        else:
            print("  (No database files found)")
    else:
        print(f"  Data directory doesn't exist: {data_dir}")
        print("\nTo fix: Create the directory and start the FastAPI server")

    # Mismatch Analysis
    if registry_db.exists() and data_dir.exists():
        print("\nMismatch Analysis:")
        print("-" * 50)

        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()

        # Check if table exists before querying
        cursor.execute("""
                       SELECT name
                       FROM sqlite_master
                       WHERE type = 'table'
                         AND name = 'item_banks_registry'
                       """)

        if cursor.fetchone():
            cursor.execute("SELECT name FROM item_banks_registry")
            registered_names = {row[0] for row in cursor.fetchall()}
        else:
            registered_names = set()

        conn.close()

        db_files = {f.stem for f in data_dir.glob('*.db') if f.name != 'registry.db'}

        orphaned = db_files - registered_names
        missing = registered_names - db_files

        if orphaned:
            print("⚠️  Database files without registry entries:")
            for name in orphaned:
                print(f"    - {name}.db")
                print(f"      Fix: Register with create endpoint or delete the file")

        if missing:
            print("⚠️  Registry entries without database files:")
            for name in missing:
                print(f"    - {name}")
                print(f"      Fix: Remove from registry or recreate database")

        if not orphaned and not missing:
            if registered_names or db_files:
                print("✓ All databases are properly registered")
            else:
                print("  No item banks found")


def check_specific_itembank(name):
    """Check for a specific item bank"""
    project_root = find_project_root()
    backend_dir = project_root / 'backend'
    data_dir = backend_dir / 'data'

    print(f"\nChecking for '{name}'...")
    print("-" * 50)

    # Look for the database file
    db_path = data_dir / f'{name}.db'

    if db_path.exists():
        print(f"✓ Found database file: {db_path}")

        # Check if registered
        registry_db = data_dir / 'registry.db'
        if registry_db.exists():
            conn = sqlite3.connect(registry_db)
            cursor = conn.cursor()

            cursor.execute("""
                           SELECT name
                           FROM sqlite_master
                           WHERE type = 'table'
                             AND name = 'item_banks_registry'
                           """)

            if cursor.fetchone():
                cursor.execute(
                    "SELECT * FROM item_banks_registry WHERE name = ?",
                    (name,)
                )

                if cursor.fetchone():
                    print("✓ Registered in registry")
                else:
                    print("✗ NOT registered in registry")
                    print("\nTo fix, run this Python code:")
                    print(f"""
import requests
response = requests.post(
    "http://localhost:8000/api/item-banks/create",
    params={{
        "name": "{name}",
        "display_name": "{name.replace('_', ' ').title()}",
        "subject": "Mathematics"
    }}
)
print(response.json())
""")
            conn.close()
    else:
        print(f"✗ Database file not found: {name}.db")

        # Look for similar names
        if data_dir.exists():
            similar = [f.stem for f in data_dir.glob('*complex*.db')]
            if similar:
                print(f"\nDid you mean one of these?")
                for s in similar:
                    print(f"  - {s}")


if __name__ == "__main__":
    check_registry()

    print("\n" + "=" * 50)
    check_specific_itembank('maths_complex_nos')

    print("\n" + "=" * 50)
    print("Next Steps:")
    print("1. If no databases exist, start the FastAPI server first")
    print("2. Use the web UI to create and upload item banks")
    print("3. Or use the API endpoints directly as shown above")