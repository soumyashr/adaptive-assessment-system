#!/usr/bin/env python3
"""
Complete test for item bank deletion with proper cleanup verification
"""

import os
import time
import requests
import sqlite3
from pathlib import Path


def test_delete_with_proper_cleanup():
    """Test creating and deleting an item bank with cleanup verification"""

    API_BASE = 'http://localhost:8000/api'
    DATA_DIR = Path('/Users/soms/adaptive-assessment-system/backend/data')
    TEST_BANK_NAME = 'test_delete_bank'

    print("=" * 60)
    print("Item Bank Delete Cleanup Test")
    print("=" * 60)

    # Step 1: Clean up any previous test remnants
    print("\n1. Cleaning up any previous test files...")
    for suffix in ['', '.db', '.db-wal', '.db-shm', '.db-journal']:
        file_path = DATA_DIR / f"{TEST_BANK_NAME}{suffix}"
        if file_path.exists():
            try:
                os.remove(file_path)
                print(f"   Removed old file: {file_path.name}")
            except Exception as e:
                print(f"   Warning: Could not remove {file_path.name}: {e}")

    # Also clean from registry if exists
    try:
        conn = sqlite3.connect(DATA_DIR / 'registry.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM item_banks_registry WHERE name = ?", (TEST_BANK_NAME,))
        if cursor.rowcount > 0:
            print(f"   Removed old registry entry for {TEST_BANK_NAME}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"   Registry cleanup: {e}")

    # Step 2: Create a test item bank
    print(f"\n2. Creating test item bank '{TEST_BANK_NAME}'...")
    response = requests.post(
        f"{API_BASE}/item-banks/create",
        params={
            "name": TEST_BANK_NAME,
            "display_name": "Test Delete Bank",
            "subject": "Test"
        }
    )

    if response.status_code == 200:
        print(f"   ✓ Created successfully")
    else:
        print(f"   ✗ Creation failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

    # Step 3: Verify files were created
    print("\n3. Verifying files created...")
    db_file = DATA_DIR / f"{TEST_BANK_NAME}.db"

    if db_file.exists():
        print(f"   ✓ Database file exists: {db_file.name}")

        # Check file size
        size = db_file.stat().st_size
        print(f"   Size: {size} bytes")
    else:
        print(f"   ✗ Database file not found!")

    # Check for WAL files
    wal_file = DATA_DIR / f"{TEST_BANK_NAME}.db-wal"
    shm_file = DATA_DIR / f"{TEST_BANK_NAME}.db-shm"

    if wal_file.exists():
        print(f"   ⚠ WAL file exists: {wal_file.name} ({wal_file.stat().st_size} bytes)")
    if shm_file.exists():
        print(f"   ⚠ SHM file exists: {shm_file.name} ({shm_file.stat().st_size} bytes)")

    # Step 4: Check registry
    print("\n4. Checking registry...")
    conn = sqlite3.connect(DATA_DIR / 'registry.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM item_banks_registry WHERE name = ?", (TEST_BANK_NAME,))
    row = cursor.fetchone()

    if row:
        print(f"   ✓ Registry entry exists")
        print(f"     ID: {row[0]}, Name: {row[1]}, Status: {row[5] if len(row) > 5 else 'N/A'}")
    else:
        print(f"   ✗ No registry entry found")
    conn.close()

    # Step 5: Delete the item bank
    print(f"\n5. Deleting item bank '{TEST_BANK_NAME}'...")
    response = requests.delete(f"{API_BASE}/item-banks/{TEST_BANK_NAME}")

    print(f"   Response status: {response.status_code}")

    if response.status_code == 200:
        print(f"   ✓ Delete request successful")
        result = response.json()
        if 'deleted' in result:
            print(f"   Deleted: {result['deleted']}")
    else:
        print(f"   ✗ Delete failed!")
        print(f"   Response: {response.text}")

        # Try to understand why it failed
        if response.status_code == 404:
            print("   Issue: Item bank not found in registry")
        elif response.status_code == 400:
            print("   Issue: Bad request - possibly active sessions or validation error")

    # Step 6: Wait for cleanup
    print("\n6. Waiting for cleanup...")
    time.sleep(1)  # Give time for file system operations

    # Step 7: Verify cleanup
    print("\n7. Verifying cleanup...")

    all_clean = True

    # Check for any remaining files
    for suffix in ['', '-wal', '-shm', '-journal']:
        file_name = f"{TEST_BANK_NAME}.db{suffix}"
        file_path = DATA_DIR / file_name

        if file_path.exists():
            print(f"   ✗ STILL EXISTS: {file_name} ({file_path.stat().st_size} bytes)")
            all_clean = False

            # Try to understand why it's still there
            try:
                # Check if file is locked
                with open(file_path, 'rb') as f:
                    f.read(1)
                print(f"      File is readable (not locked)")
            except:
                print(f"      File might be locked!")

    if all_clean:
        print(f"   ✓ All files cleaned up successfully!")

    # Check registry cleanup
    conn = sqlite3.connect(DATA_DIR / 'registry.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM item_banks_registry WHERE name = ?", (TEST_BANK_NAME,))
    row = cursor.fetchone()

    if row:
        print(f"   ✗ Registry entry STILL EXISTS")
        all_clean = False
    else:
        print(f"   ✓ Registry entry removed")
    conn.close()

    # Step 8: Summary
    print("\n" + "=" * 60)
    if all_clean:
        print("✅ TEST PASSED: Complete cleanup successful!")
    else:
        print("❌ TEST FAILED: Cleanup incomplete")

        # Diagnostic info
        print("\nPossible issues:")
        print("1. Database connections not properly closed in delete_item_bank()")
        print("2. SQLAlchemy engine not disposed")
        print("3. WAL mode preventing immediate file deletion")
        print("4. Missing cleanup() method in ItemBankDBManager")

        print("\nTo fix manually:")
        print(f"rm {DATA_DIR}/{TEST_BANK_NAME}.db*")
        print(f"sqlite3 {DATA_DIR}/registry.db \"DELETE FROM item_banks_registry WHERE name='{TEST_BANK_NAME}'\"")

    print("=" * 60)

    return all_clean


def check_open_connections():
    """Check for open SQLite connections using lsof"""
    print("\nChecking for open database connections...")

    import subprocess
    try:
        result = subprocess.run(
            ['lsof', '|', 'grep', '.db'],
            shell=True,
            capture_output=True,
            text=True
        )

        if result.stdout:
            print("Open connections found:")
            for line in result.stdout.split('\n')[:10]:  # First 10 lines
                if line.strip():
                    print(f"  {line}")
        else:
            print("  No open connections detected")
    except:
        print("  Could not run lsof (may not be available)")


if __name__ == "__main__":
    # Run the test
    success = test_delete_with_proper_cleanup()

    # Check for open connections
    check_open_connections()

    # Exit with appropriate code
    exit(0 if success else 1)