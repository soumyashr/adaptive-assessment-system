#!/usr/bin/env python3
"""
MASTER FIX SCRIPT - Complete Item Bank Calibration Fix

This script performs the complete workflow to fix calibration issues:
1. Updates existing question parameters with tier-based values
2. Optionally clears old response data
3. Runs enhanced simulation with realistic assessments
4. Validates calibration results
5. Provides instructions for final UI recalibration

Usage:
    python fix_item_bank_calibration.py --item-bank physics_oscillations_expanded

Options:
    --item-bank NAME        Item bank to fix (required)
    --n-students N          Number of students to simulate (default: 600)
    --questions-per N       Max questions per assessment (default: 30)
    --clear-responses       Clear existing response data before simulation
    --skip-simulation       Skip simulation (only update parameters)
    --dry-run              Show what would happen without making changes
"""

import argparse
import sys
import os
import sqlite3
import random
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple


# Color codes for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")


def print_step(step_num, text):
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}[STEP {step_num}]{Colors.ENDC} {Colors.BOLD}{text}{Colors.ENDC}")


def print_success(text):
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {text}")


def print_warning(text):
    print(f"{Colors.WARNING}⚠{Colors.ENDC}  {text}")


def print_error(text):
    print(f"{Colors.FAIL}✗{Colors.ENDC} {text}")


def print_info(text):
    print(f"  {text}")


# Add backend to path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(script_dir, '..') if 'scripts' in script_dir else script_dir
backend_dir = os.path.abspath(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

random.seed(42)
np.random.seed(42)


class ItemBankFixer:
    """Complete item bank calibration fix workflow"""

    def __init__(self, item_bank_name: str, dry_run: bool = False):
        self.item_bank_name = item_bank_name
        self.dry_run = dry_run
        self.db_path = None
        self.questions = []

        # Tier-based parameters
        self.tier_discrimination = {
            'C1': 1.2,
            'C2': 1.5,
            'C3': 1.5,
            'C4': 1.8
        }

        self.tier_difficulty = {
            'C1': -1.5,
            'C2': -0.5,
            'C3': 0.5,
            'C4': 1.5
        }

    def initialize(self) -> bool:
        """Initialize and verify item bank exists"""
        print_step(0, "INITIALIZATION")

        # Find database
        possible_paths = [
            os.path.join(backend_dir, 'data', f'{self.item_bank_name}.db'),
            os.path.join(backend_dir, f'{self.item_bank_name}.db'),
            f'backend/data/{self.item_bank_name}.db',
            f'{self.item_bank_name}.db'
        ]

        for path in possible_paths:
            if os.path.exists(path):
                self.db_path = path
                break

        if not self.db_path:
            print_error(f"Could not find database for item bank: {self.item_bank_name}")
            print_info(f"Searched locations:")
            for path in possible_paths:
                print_info(f"  - {path}")
            return False

        print_success(f"Found item bank: {self.db_path}")

        # Load questions
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, question_id, tier, discrimination_a, difficulty_b, guessing_c, topic
            FROM questions
        """)

        for row in cursor.fetchall():
            self.questions.append({
                'id': row[0],
                'question_id': row[1],
                'tier': row[2],
                'discrimination_a': row[3],
                'difficulty_b': row[4],
                'guessing_c': row[5],
                'topic': row[6]
            })

        conn.close()

        if not self.questions:
            print_error("No questions found in item bank")
            return False

        print_success(f"Loaded {len(self.questions)} questions")

        # Show tier distribution
        tier_counts = {}
        for q in self.questions:
            tier = q['tier']
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        print_info("Current tier distribution:")
        for tier in sorted(tier_counts.keys()):
            print_info(f"  {tier}: {tier_counts[tier]} questions")

        if self.dry_run:
            print_warning("DRY RUN MODE - No changes will be made")

        return True

    def update_parameters(self) -> Tuple[int, Dict]:
        """Update question parameters with tier-based values"""
        print_step(1, "UPDATE QUESTION PARAMETERS")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        updated_count = 0
        tier_stats = {'C1': 0, 'C2': 0, 'C3': 0, 'C4': 0, 'invalid': 0}

        for q in self.questions:
            # Normalize tier
            tier_upper = str(q['tier']).upper() if q['tier'] else None

            if tier_upper in ['C1', 'C2', 'C3', 'C4']:
                new_a = self.tier_discrimination[tier_upper]
                new_b = self.tier_difficulty[tier_upper]
                new_c = 0.25

                tier_stats[tier_upper] += 1

                # Check if update needed
                if abs(q['discrimination_a'] - new_a) > 0.01 or abs(q['difficulty_b'] - new_b) > 0.01:
                    updated_count += 1

                    if not self.dry_run:
                        cursor.execute("""
                            UPDATE questions
                            SET discrimination_a = ?,
                                difficulty_b = ?,
                                guessing_c = ?
                            WHERE id = ?
                        """, (new_a, new_b, new_c, q['id']))

                    print_info(
                        f"  {q['question_id']} ({tier_upper}): a={q['discrimination_a']:.2f}→{new_a:.2f}, b={q['difficulty_b']:.2f}→{new_b:.2f}")
            else:
                tier_stats['invalid'] += 1
                print_warning(f"  {q['question_id']}: Invalid tier '{q['tier']}' - keeping original parameters")

        if not self.dry_run:
            conn.commit()

        conn.close()

        print_success(f"Updated {updated_count} questions")

        return updated_count, tier_stats

    def clear_responses(self) -> int:
        """Clear existing response data"""
        print_step(2, "CLEAR OLD RESPONSE DATA")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count existing data
        cursor.execute("SELECT COUNT(*) FROM responses")
        response_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM assessment_sessions")
        session_count = cursor.fetchone()[0]

        if response_count == 0 and session_count == 0:
            print_info("No existing response data to clear")
            conn.close()
            return 0

        print_info(f"Found {response_count} responses from {session_count} sessions")

        if not self.dry_run:
            cursor.execute("DELETE FROM responses")
            cursor.execute("DELETE FROM assessment_sessions")
            conn.commit()
            print_success("Cleared all response data")
        else:
            print_warning("Would clear all response data (dry run)")

        conn.close()
        return response_count

    def simulate_assessments(self, n_students: int, max_questions: int) -> Dict:
        """Run enhanced simulation"""
        print_step(3, f"SIMULATE {n_students} ASSESSMENTS")

        if self.dry_run:
            print_warning("Skipping simulation (dry run)")
            return {'simulated': False}

        # Generate students
        print_info("Generating virtual students...")
        students = self._generate_students(n_students)

        level_counts = {}
        for s in students:
            level_counts[s['level']] = level_counts.get(s['level'], 0) + 1

        print_info("Student distribution:")
        for level, count in sorted(level_counts.items()):
            pct = 100 * count / len(students)
            print_info(f"  {level:12s}: {count:4d} ({pct:5.1f}%)")

        # Run simulations
        print_info(f"Simulating assessments (max {max_questions} questions each)...")
        simulations = []

        for i, student in enumerate(students, 1):
            sim = self._simulate_assessment(student, max_questions)
            simulations.append(sim)

            if i % 100 == 0:
                print_info(f"  Progress: {i}/{n_students}")

        print_success(f"Completed {len(simulations)} assessments")

        # Save to database
        print_info("Saving to database...")
        self._save_simulations(simulations)
        print_success("Data saved")

        # Generate statistics
        stats = self._calculate_stats(simulations)

        return stats

    def _generate_students(self, n: int) -> List[Dict]:
        """Generate virtual students"""
        students = []

        distributions = [
            {'level': 'beginner', 'count': int(n * 0.20), 'theta_mean': -1.5, 'theta_std': 0.5},
            {'level': 'intermediate', 'count': int(n * 0.40), 'theta_mean': 0.0, 'theta_std': 0.6},
            {'level': 'advanced', 'count': int(n * 0.30), 'theta_mean': 1.0, 'theta_std': 0.5},
            {'level': 'expert', 'count': int(n * 0.10), 'theta_mean': 2.0, 'theta_std': 0.4}
        ]

        student_id = 1
        for dist in distributions:
            for _ in range(dist['count']):
                true_theta = np.clip(
                    np.random.normal(dist['theta_mean'], dist['theta_std']),
                    -3.0, 3.0
                )
                students.append({
                    'id': student_id,
                    'level': dist['level'],
                    'true_theta': true_theta
                })
                student_id += 1

        return students

    def _simulate_assessment(self, student: Dict, max_questions: int) -> Dict:
        """Simulate one assessment with simplified adaptive logic"""
        initial_theta_map = {
            'beginner': -1.5,
            'intermediate': 0.0,
            'advanced': 1.5,
            'expert': 2.0
        }

        current_theta = initial_theta_map[student['level']]
        current_theta += np.random.normal(0, 0.3)
        current_theta = np.clip(current_theta, -3.0, 3.0)

        asked_questions = []
        responses = []
        available = self.questions.copy()

        for _ in range(min(max_questions, len(available))):
            if not available:
                break

            # Select question with max Fisher Information
            best_question = None
            max_info = -1

            for q in available:
                info = self._fisher_information(current_theta, q)
                if info > max_info:
                    max_info = info
                    best_question = q

            if not best_question:
                break

            # Remove from available
            available = [q for q in available if q['id'] != best_question['id']]

            # Simulate response
            prob = self._probability_correct(student['true_theta'], best_question)
            is_correct = random.random() < prob

            asked_questions.append(best_question)
            responses.append(is_correct)

            # Update theta (simplified)
            gradient = best_question['discrimination_a'] * (is_correct - prob)
            current_theta = np.clip(current_theta + 0.3 * gradient, -3.0, 3.0)

        return {
            'student_id': student['id'],
            'true_theta': student['true_theta'],
            'estimated_theta': current_theta,
            'questions': asked_questions,
            'responses': responses,
            'questions_asked': len(asked_questions)
        }

    def _probability_correct(self, theta: float, question: Dict) -> float:
        """3PL probability"""
        a = question['discrimination_a']
        b = question['difficulty_b']
        c = question['guessing_c']

        exponent = a * (theta - b)
        if exponent > 700:
            return 1.0
        elif exponent < -700:
            return c

        import math
        return c + (1 - c) / (1 + math.exp(-exponent))

    def _fisher_information(self, theta: float, question: Dict) -> float:
        """Fisher information"""
        p = self._probability_correct(theta, question)
        c = question['guessing_c']

        if p <= c or p >= 1.0:
            return 0.0

        q_prob = 1 - p
        p_star = (p - c) / (1 - c)

        if p_star <= 0 or p_star >= 1:
            return 0.0

        a = question['discrimination_a']
        num = (a ** 2) * (p_star * (1 - p_star))
        denom = ((1 - c) ** 2) * p * q_prob

        return num / (denom + 1e-10)

    def _theta_to_tier(self, theta: float) -> str:
        """Convert theta to tier"""
        if theta < -1.0:
            return "C1"
        elif theta < 0.0:
            return "C2"
        elif theta < 1.0:
            return "C3"
        else:
            return "C4"

    def _save_simulations(self, simulations: List[Dict]):
        """Save simulations to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for sim in simulations:
            # Create session
            cursor.execute("""
                INSERT INTO assessment_sessions
                (user_id, subject, theta, sem, tier, questions_asked, completed, completed_at)
                VALUES (?, ?, ?, 1.0, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (
                sim['student_id'],
                self.item_bank_name,
                sim['estimated_theta'],
                self._theta_to_tier(sim['estimated_theta']),
                sim['questions_asked']
            ))

            session_id = cursor.lastrowid

            # Insert responses
            for question, is_correct in zip(sim['questions'], sim['responses']):
                cursor.execute("""
                    INSERT INTO responses
                    (session_id, question_id, selected_option, is_correct, 
                     theta_before, theta_after, topic)
                    VALUES (?, ?, 'A', ?, NULL, NULL, ?)
                """, (
                    session_id,
                    question['id'],
                    is_correct,
                    question['topic']
                ))

        conn.commit()
        conn.close()

    def _calculate_stats(self, simulations: List[Dict]) -> Dict:
        """Calculate simulation statistics"""
        total_responses = sum(s['questions_asked'] for s in simulations)
        total_correct = sum(sum(s['responses']) for s in simulations)
        questions_per_sim = [s['questions_asked'] for s in simulations]

        # Question usage
        question_usage = {}
        for sim in simulations:
            for q in sim['questions']:
                question_usage[q['id']] = question_usage.get(q['id'], 0) + 1

        return {
            'n_students': len(simulations),
            'total_responses': total_responses,
            'accuracy': total_correct / total_responses if total_responses > 0 else 0,
            'questions_per_assessment': {
                'mean': np.mean(questions_per_sim),
                'min': min(questions_per_sim),
                'max': max(questions_per_sim)
            },
            'question_coverage': {
                'questions_used': len(question_usage),
                'total_questions': len(self.questions),
                'avg_responses_per_question': np.mean(list(question_usage.values())),
                'min_responses': min(question_usage.values()),
                'max_responses': max(question_usage.values()),
                'questions_with_100plus': sum(1 for count in question_usage.values() if count >= 100)
            }
        }

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate calibration readiness"""
        print_step(4, "VALIDATION")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check question parameters
        cursor.execute("""
            SELECT tier, discrimination_a, difficulty_b
            FROM questions
        """)

        tier_data = {'C1': [], 'C2': [], 'C3': [], 'C4': []}
        for tier, a, b in cursor.fetchall():
            tier_upper = str(tier).upper() if tier else None
            if tier_upper in tier_data:
                tier_data[tier_upper].append((a, b))

        issues = []

        print_info("Question parameter distribution:")
        expected_ranges = {
            'C1': (-1.5, -0.5),
            'C2': (-0.5, 0.5),
            'C3': (0.5, 1.0),
            'C4': (1.0, 2.0)
        }

        for tier in ['C1', 'C2', 'C3', 'C4']:
            if not tier_data[tier]:
                print_warning(f"  {tier}: No questions")
                issues.append(f"No {tier} questions")
                continue

            difficulties = [b for a, b in tier_data[tier]]
            mean_b = np.mean(difficulties)
            count = len(difficulties)

            expected_min, expected_max = expected_ranges[tier]

            if expected_min <= mean_b <= expected_max:
                print_success(f"  {tier}: {count} questions, mean_b={mean_b:+.2f} ✓")
            else:
                print_warning(
                    f"  {tier}: {count} questions, mean_b={mean_b:+.2f} (expected {expected_min:+.2f} to {expected_max:+.2f})")
                issues.append(f"{tier} difficulty out of expected range")

        # Check response data
        cursor.execute("SELECT COUNT(*) FROM responses")
        response_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT question_id, COUNT(*)
            FROM responses
            GROUP BY question_id
        """)

        question_responses = cursor.fetchall()

        print_info(f"\nResponse data:")
        print_info(f"  Total responses: {response_count}")
        print_info(f"  Questions with responses: {len(question_responses)}/{len(self.questions)}")

        if question_responses:
            counts = [count for _, count in question_responses]
            questions_ready = sum(1 for count in counts if count >= 100)

            print_info(f"  Avg responses per question: {np.mean(counts):.1f}")
            print_info(f"  Questions with ≥100 responses: {questions_ready}")

            if questions_ready < len(self.questions) * 0.8:
                issues.append(f"Only {questions_ready}/{len(self.questions)} questions have sufficient data")
        else:
            issues.append("No response data available")

        conn.close()

        return len(issues) == 0, issues

    def print_summary(self, updated: int, tier_stats: Dict, sim_stats: Dict, validation_passed: bool,
                      issues: List[str]):
        """Print final summary"""
        print_header("SUMMARY")

        print(f"{Colors.BOLD}Parameters Updated:{Colors.ENDC}")
        print_success(f"{updated} questions updated with tier-based parameters")

        print(f"\n{Colors.BOLD}Tier Distribution:{Colors.ENDC}")
        for tier in ['C1', 'C2', 'C3', 'C4']:
            count = tier_stats[tier]
            if count > 0:
                a = self.tier_discrimination[tier]
                b = self.tier_difficulty[tier]
                print_info(f"  {tier}: {count:3d} questions (a={a:.1f}, b={b:+.1f})")

        if sim_stats.get('n_students'):
            print(f"\n{Colors.BOLD}Simulation Results:{Colors.ENDC}")
            print_success(f"{sim_stats['n_students']} assessments simulated")
            print_info(f"  Total responses: {sim_stats['total_responses']}")
            print_info(f"  Accuracy: {100 * sim_stats['accuracy']:.1f}%")
            print_info(f"  Questions per assessment: {sim_stats['questions_per_assessment']['mean']:.1f}")
            print_info(
                f"  Questions with ≥100 responses: {sim_stats['question_coverage']['questions_with_100plus']}/{len(self.questions)}")

        print(f"\n{Colors.BOLD}Validation:{Colors.ENDC}")
        if validation_passed:
            print_success("All checks passed!")
        else:
            print_warning("Issues detected:")
            for issue in issues:
                print_info(f"  - {issue}")

        print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
        if validation_passed and sim_stats.get('n_students'):
            print_success("✓ Ready for calibration!")
            print_info("\nRun calibration via:")
            print_info(f"  {Colors.BOLD}UI:{Colors.ENDC} Admin → Item Banks → {self.item_bank_name} → Recalibrate")
            print_info(f"  {Colors.BOLD}OR{Colors.ENDC}")
            print_info(f"  {Colors.BOLD}CLI:{Colors.ENDC} python backend/scripts/recalibrate_question_bank.py \\")
            print_info(f"           --db {self.db_path} \\")
            print_info(f"           --subject {self.item_bank_name}")
        else:
            print_warning("Complete the steps above before calibrating")


def main():
    parser = argparse.ArgumentParser(
        description="Master script to fix item bank calibration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full fix with default settings
  python fix_item_bank_calibration.py --item-bank physics_oscillations_expanded

  # With more students for better coverage
  python fix_item_bank_calibration.py --item-bank physics_oscillations_expanded -n 800

  # Clear old data and start fresh
  python fix_item_bank_calibration.py --item-bank physics_oscillations_expanded --clear-responses

  # Just update parameters without simulation
  python fix_item_bank_calibration.py --item-bank physics_oscillations_expanded --skip-simulation

  # Test run without making changes
  python fix_item_bank_calibration.py --item-bank physics_oscillations_expanded --dry-run
        """
    )

    parser.add_argument("--item-bank", required=True, help="Item bank name")
    parser.add_argument("-n", "--n-students", type=int, default=600,
                        help="Number of students to simulate (default: 600)")
    parser.add_argument("--questions-per", type=int, default=30,
                        help="Max questions per assessment (default: 30)")
    parser.add_argument("--clear-responses", action="store_true",
                        help="Clear existing response data before simulation")
    parser.add_argument("--skip-simulation", action="store_true",
                        help="Skip simulation (only update parameters)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without making changes")

    args = parser.parse_args()

    print_header("ITEM BANK CALIBRATION FIX")

    if args.dry_run:
        print_warning("DRY RUN MODE - No changes will be made\n")

    print(f"Item Bank: {Colors.BOLD}{args.item_bank}{Colors.ENDC}")
    print(f"Students to simulate: {Colors.BOLD}{args.n_students}{Colors.ENDC}")
    print(f"Questions per assessment: {Colors.BOLD}{args.questions_per}{Colors.ENDC}")

    # Initialize
    fixer = ItemBankFixer(args.item_bank, args.dry_run)

    if not fixer.initialize():
        sys.exit(1)

    # Update parameters
    updated, tier_stats = fixer.update_parameters()

    # Clear responses if requested
    if args.clear_responses:
        fixer.clear_responses()

    # Run simulation
    sim_stats = {}
    if not args.skip_simulation:
        sim_stats = fixer.simulate_assessments(args.n_students, args.questions_per)
    else:
        print_step(3, "SIMULATION")
        print_warning("Skipped (--skip-simulation flag)")

    # Validate
    validation_passed, issues = fixer.validate()

    # Print summary
    fixer.print_summary(updated, tier_stats, sim_stats, validation_passed, issues)

    print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'=' * 80}{Colors.ENDC}")
    if not args.dry_run:
        print(f"{Colors.BOLD}{Colors.OKGREEN}{'CALIBRATION FIX COMPLETE!'.center(80)}{Colors.ENDC}")
    else:
        print(
            f"{Colors.BOLD}{Colors.WARNING}{'DRY RUN COMPLETE - Run without --dry-run to apply changes'.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}{'=' * 80}{Colors.ENDC}\n")


if __name__ == "__main__":
    main()