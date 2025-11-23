#!/usr/bin/env python3
"""
Update existing questions with proper tier-based IRT parameters

This script fixes questions that were uploaded with incorrect parameters
due to the case sensitivity bug.

Usage:
    python update_existing_parameters.py --item-bank physics_oscillations_expanded
"""

import argparse
import sys
import os

# Add backend to path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.db_manager import ItemBankDBManager
from config import Config


def update_parameters(item_bank_name: str, dry_run: bool = False):
    """Update IRT parameters for all questions in item bank"""

    # Tier-based parameters
    tier_discrimination = Config.TIER_DISCRIMINATION_DEFAULTS
    tier_difficulty = Config.TIER_DIFFICULTY_DEFAULTS

    # Connect to item bank database
    db_manager = ItemBankDBManager()
    db_path = db_manager.get_db_path(item_bank_name)

    if not os.path.exists(db_path):
        print(f"❌ Error: Item bank '{item_bank_name}' not found at {db_path}")
        return

    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all questions
    cursor.execute("""
        SELECT id, question_id, tier, discrimination_a, difficulty_b, guessing_c
        FROM questions
    """)

    questions = cursor.fetchall()

    if not questions:
        print(f"❌ No questions found in item bank '{item_bank_name}'")
        conn.close()
        return

    print(f"\n{'=' * 80}")
    print(f"UPDATE IRT PARAMETERS - {item_bank_name}")
    print(f"{'=' * 80}\n")
    print(f"Found {len(questions)} questions")

    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")

    # Track changes
    updated_count = 0
    tier_stats = {'C1': 0, 'C2': 0, 'C3': 0, 'C4': 0, 'invalid': 0}

    for q_id, question_id, tier, old_a, old_b, old_c in questions:
        # Normalize tier
        tier_upper = str(tier).upper() if tier else None

        if tier_upper in ['C1', 'C2', 'C3', 'C4']:
            new_a = tier_discrimination[tier_upper]
            new_b = tier_difficulty[tier_upper]
            new_c = 0.25  # Keep standard guessing parameter

            tier_stats[tier_upper] += 1

            # Check if update needed
            if abs(old_a - new_a) > 0.01 or abs(old_b - new_b) > 0.01:
                updated_count += 1

                if not dry_run:
                    cursor.execute("""
                        UPDATE questions
                        SET discrimination_a = ?,
                            difficulty_b = ?,
                            guessing_c = ?
                        WHERE id = ?
                    """, (new_a, new_b, new_c, q_id))

                print(f"✓ {question_id} ({tier_upper}): a={old_a:.2f}→{new_a:.2f}, b={old_b:.2f}→{new_b:.2f}")
        else:
            tier_stats['invalid'] += 1
            print(f"⚠️  {question_id}: Invalid tier '{tier}' - skipped")

    if not dry_run:
        conn.commit()

    conn.close()

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}\n")
    print(f"Total questions: {len(questions)}")
    print(f"Updated: {updated_count}")
    print(f"\nTier distribution:")
    for tier in ['C1', 'C2', 'C3', 'C4']:
        count = tier_stats[tier]
        if count > 0:
            pct = 100 * count / len(questions)
            print(
                f"  {tier}: {count:3d} ({pct:5.1f}%) - a={tier_discrimination[tier]:.1f}, b={tier_difficulty[tier]:+.1f}")

    if tier_stats['invalid'] > 0:
        print(f"  Invalid: {tier_stats['invalid']} (kept original parameters)")

    if dry_run:
        print(f"\n💡 Run without --dry-run to apply changes")
    else:
        print(f"\n✅ Parameters updated successfully!")
        print(f"📊 Ready for calibration with proper tier distribution")


def main():
    parser = argparse.ArgumentParser(description="Update IRT parameters for existing questions")
    parser.add_argument("--item-bank", required=True, help="Item bank name")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")

    args = parser.parse_args()

    update_parameters(args.item_bank, args.dry_run)


if __name__ == "__main__":
    main()