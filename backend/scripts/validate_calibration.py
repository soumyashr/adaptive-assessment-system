#!/usr/bin/env python3
"""
Validate Calibration Results

Checks calibration quality and detects issues.

Usage:
    python validate_calibration.py --item-bank physics_oscillations_expanded
"""

import argparse
import sys
import os
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.db_manager import ItemBankDBManager


def validate(item_bank_name: str):
    """Validate calibration results"""

    db_manager = ItemBankDBManager()
    db_path = db_manager.get_db_path(item_bank_name)

    if not os.path.exists(db_path):
        print(f"❌ Item bank not found: {item_bank_name}")
        return

    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all questions
    cursor.execute("""
        SELECT question_id, tier, discrimination_a, difficulty_b, guessing_c
        FROM questions
    """)

    questions = cursor.fetchall()

    print(f"\n{'=' * 80}")
    print(f"CALIBRATION VALIDATION - {item_bank_name}")
    print(f"{'=' * 80}\n")
    print(f"Total questions: {len(questions)}")

    # Tier distribution
    tier_data = {'C1': [], 'C2': [], 'C3': [], 'C4': []}

    for q_id, tier, a, b, c in questions:
        if tier in tier_data:
            tier_data[tier].append((a, b, c))

    print("\n📊 Difficulty Distribution by Tier:")
    print(f"{'Tier':<6} {'Count':<7} {'Difficulty (b)':<20} {'Status'}")
    print("-" * 60)

    expected_ranges = {
        'C1': (-1.5, -0.5),
        'C2': (-0.5, 0.5),
        'C3': (0.5, 1.0),
        'C4': (1.0, 2.0)
    }

    issues = []

    for tier in ['C1', 'C2', 'C3', 'C4']:
        if not tier_data[tier]:
            print(f"{tier:<6} {0:<7} {'N/A':<20} ❌ NO QUESTIONS")
            issues.append(f"Missing {tier} questions")
            continue

        difficulties = [b for a, b, c in tier_data[tier]]
        mean_b = np.mean(difficulties)
        std_b = np.std(difficulties)
        min_b = np.min(difficulties)
        max_b = np.max(difficulties)

        expected_min, expected_max = expected_ranges[tier]

        # Check if mean is in expected range
        if expected_min <= mean_b <= expected_max:
            status = "✓ Good"
        elif mean_b < expected_min - 0.5 or mean_b > expected_max + 0.5:
            status = "❌ BAD"
            issues.append(f"{tier} difficulty out of range: {mean_b:.2f}")
        else:
            status = "⚠️  Check"
            issues.append(f"{tier} difficulty borderline: {mean_b:.2f}")

        count = len(difficulties)
        range_str = f"[{min_b:+.2f}, {max_b:+.2f}]"
        print(f"{tier:<6} {count:<7} {range_str:<20} {status}")

    # Check discrimination
    print(f"\n📊 Discrimination Distribution:")
    all_discriminations = [a for tier_items in tier_data.values() for a, b, c in tier_items]

    if all_discriminations:
        print(f"  Mean: {np.mean(all_discriminations):.2f}")
        print(f"  Range: [{np.min(all_discriminations):.2f}, {np.max(all_discriminations):.2f}]")

        low_disc = sum(1 for a in all_discriminations if a < 0.8)
        if low_disc > 0:
            print(f"  ⚠️  {low_disc} questions with low discrimination (<0.8)")
            issues.append(f"{low_disc} questions with low discrimination")

    # Overall assessment
    print(f"\n{'=' * 80}")
    if not issues:
        print("✅ VALIDATION PASSED - Calibration looks good!")
        print("\nAll tiers have appropriate difficulty distributions.")
        print("Ready for student assessments.")
    else:
        print("⚠️  ISSUES DETECTED:")
        for issue in issues:
            print(f"  - {issue}")

        print("\n💡 Recommendations:")
        if any("Missing" in issue for issue in issues):
            print("  - Add more questions to missing tiers")
        if any("out of range" in issue for issue in issues):
            print("  - Re-run calibration with more responses")
            print("  - Check if simulated student abilities are appropriate")

    print(f"{'=' * 80}\n")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Validate calibration results")
    parser.add_argument("--item-bank", required=True, help="Item bank name")

    args = parser.parse_args()
    validate(args.item_bank)


if __name__ == "__main__":
    main()