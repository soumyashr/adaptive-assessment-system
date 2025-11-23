#!/usr/bin/env python3
"""
Enhanced Simulation Using Real IRT Engine

Simulates realistic adaptive assessments using the actual IRT engine.
Generates high-quality synthetic data for calibration.

Usage:
    python simulate_assessments_enhanced.py \
        --item-bank physics_oscillations_expanded \
        -n 500 \
        --questions-per-student 30
"""

import argparse
import sys
import os
import random
import numpy as np
from datetime import datetime
from typing import List, Dict

# Add backend to path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.db_manager import ItemBankDBManager
from irt_engine import IRTEngine, TestPurpose, AdaptiveConfig
from config import Config

random.seed(42)
np.random.seed(42)


class EnhancedSimulator:
    """Simulate assessments using real IRT engine"""

    def __init__(self, item_bank_name: str):
        self.item_bank_name = item_bank_name
        self.db_manager = ItemBankDBManager()
        self.db_path = self.db_manager.get_db_path(item_bank_name)

        # Initialize IRT engine with FORMATIVE config (matches your system)
        self.irt_engine = IRTEngine(
            config=Config.get_config(),
            test_purpose=TestPurpose.FORMATIVE
        )

        self.questions = []

    def load_questions(self):
        """Load questions from database"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, question_id, discrimination_a, difficulty_b, 
                   guessing_c, tier, topic
            FROM questions
        """)

        for row in cursor.fetchall():
            self.questions.append({
                'id': row[0],
                'question_id': row[1],
                'discrimination_a': row[2],
                'difficulty_b': row[3],
                'guessing_c': row[4],
                'tier': row[5],
                'topic': row[6]
            })

        conn.close()

        print(f"✓ Loaded {len(self.questions)} questions")

        # Show tier distribution
        tier_counts = {}
        for q in self.questions:
            tier = q['tier']
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        print("\nQuestion distribution by tier:")
        for tier in sorted(tier_counts.keys()):
            print(f"  {tier}: {tier_counts[tier]} questions")

        return len(self.questions)

    def generate_students(self, n: int) -> List[Dict]:
        """Generate virtual students with realistic ability distribution"""
        students = []

        # Realistic distribution matching expected user base
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

    def simulate_assessment(self, student: Dict, max_questions: int = 30) -> Dict:
        """Simulate one adaptive assessment using IRT engine"""
        import sqlite3

        # Initialize student's estimated theta (with some noise)
        initial_theta_map = {
            'beginner': -1.5,
            'intermediate': 0.0,
            'advanced': 1.5,
            'expert': 2.0
        }

        current_theta = initial_theta_map[student['level']]
        current_theta += np.random.normal(0, 0.3)  # Add noise
        current_theta = np.clip(current_theta, -3.0, 3.0)

        # Track assessment
        asked_questions = []
        response_history = []
        response_data = []

        available_questions = self.questions.copy()

        for question_num in range(max_questions):
            # Use IRT engine to select next question
            next_question = self.irt_engine.select_next_question(
                theta=current_theta,
                available_questions=available_questions,
                response_history=response_history,
                questions_answered=len(asked_questions)
            )

            if not next_question:
                break  # No more questions available

            # Remove from available
            available_questions = [q for q in available_questions if q['id'] != next_question['id']]

            # Simulate response using 3PL model with student's TRUE theta
            prob_correct = self.irt_engine.probability_correct(
                student['true_theta'],  # Use true ability for response
                next_question['difficulty_b'],
                next_question['discrimination_a'],
                next_question['guessing_c']
            )

            is_correct = random.random() < prob_correct

            # Record response
            asked_questions.append(next_question)
            response_history.append(is_correct)
            response_data.append((
                is_correct,
                next_question['difficulty_b'],
                next_question['discrimination_a'],
                next_question['guessing_c']
            ))

            # Update theta using IRT engine
            current_theta, update_info = self.irt_engine.update_theta(
                current_theta=current_theta,
                responses=response_data,
                response_history=response_history,
                questions_answered=len(asked_questions)
            )

            # Check stopping criteria
            questions_info = [(r[1], r[2], r[3]) for r in response_data]
            current_sem = self.irt_engine.calculate_sem(current_theta, questions_info)

            should_stop, _ = self.irt_engine.should_stop_assessment(
                current_sem,
                len(asked_questions),
                response_history,
                TestPurpose.FORMATIVE
            )

            if should_stop and len(asked_questions) >= self.irt_engine.min_questions:
                break

        return {
            'student_id': student['id'],
            'true_theta': student['true_theta'],
            'estimated_theta': current_theta,
            'questions': asked_questions,
            'responses': response_history,
            'questions_asked': len(asked_questions)
        }

    def save_to_database(self, simulations: List[Dict]):
        """Save simulated data to database"""
        import sqlite3

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
                self.irt_engine.theta_to_tier(sim['estimated_theta']),
                sim['questions_asked']
            ))

            session_id = cursor.lastrowid

            # Insert responses
            for i, (question, is_correct) in enumerate(zip(sim['questions'], sim['responses'])):
                theta_before = sim['estimated_theta'] if i == 0 else None  # Simplified
                theta_after = sim['estimated_theta'] if i == len(sim['responses']) - 1 else None

                cursor.execute("""
                    INSERT INTO responses
                    (session_id, question_id, selected_option, is_correct, 
                     theta_before, theta_after, topic)
                    VALUES (?, ?, 'A', ?, ?, ?, ?)
                """, (
                    session_id,
                    question['id'],
                    is_correct,
                    theta_before,
                    theta_after,
                    question['topic']
                ))

        conn.commit()
        conn.close()

    def run(self, n_students: int, max_questions: int):
        """Run complete simulation"""
        print(f"\n{'=' * 80}")
        print(f"ENHANCED SIMULATION - {self.item_bank_name}")
        print(f"{'=' * 80}\n")

        # Load questions
        if not self.load_questions():
            print("❌ No questions found")
            return

        # Generate students
        print(f"\n✓ Generating {n_students} virtual students...")
        students = self.generate_students(n_students)

        level_counts = {}
        for s in students:
            level_counts[s['level']] = level_counts.get(s['level'], 0) + 1

        print("\nStudent distribution:")
        for level, count in sorted(level_counts.items()):
            pct = 100 * count / len(students)
            print(f"  {level:12s}: {count:4d} ({pct:5.1f}%)")

        # Run simulations
        print(f"\n✓ Simulating {n_students} assessments (max {max_questions} questions each)...")
        simulations = []

        for i, student in enumerate(students, 1):
            sim = self.simulate_assessment(student, max_questions)
            simulations.append(sim)

            if i % 100 == 0:
                print(f"  Progress: {i}/{n_students}")

        # Save to database
        print("\n✓ Saving to database...")
        self.save_to_database(simulations)

        # Generate report
        self._print_report(simulations)

    def _print_report(self, simulations: List[Dict]):
        """Print simulation report"""
        total_responses = sum(s['questions_asked'] for s in simulations)
        total_correct = sum(sum(s['responses']) for s in simulations)

        questions_per_sim = [s['questions_asked'] for s in simulations]

        print(f"\n{'=' * 80}")
        print("SIMULATION REPORT")
        print(f"{'=' * 80}\n")
        print(f"Students simulated: {len(simulations)}")
        print(f"Total responses: {total_responses}")
        print(f"Overall accuracy: {100 * total_correct / total_responses:.1f}%")
        print(f"\nQuestions per assessment:")
        print(f"  Mean: {np.mean(questions_per_sim):.1f}")
        print(f"  Range: [{min(questions_per_sim)}, {max(questions_per_sim)}]")

        # Question coverage
        question_usage = {}
        for sim in simulations:
            for q in sim['questions']:
                question_usage[q['id']] = question_usage.get(q['id'], 0) + 1

        print(f"\nQuestion coverage:")
        print(f"  Questions used: {len(question_usage)}/{len(self.questions)}")
        print(f"  Avg responses per question: {np.mean(list(question_usage.values())):.1f}")
        print(f"  Min responses: {min(question_usage.values())}")
        print(f"  Max responses: {max(question_usage.values())}")

        # Ready for calibration
        questions_with_100plus = sum(1 for count in question_usage.values() if count >= 100)

        print(f"\n📊 Calibration readiness:")
        print(f"  Questions with ≥100 responses: {questions_with_100plus}")

        if questions_with_100plus >= 15:
            print(f"\n✅ Ready for calibration!")
            print(f"   Run: python scripts/recalibrate_question_bank.py \\")
            print(f"           --db {self.db_path} \\")
            print(f"           --subject {self.item_bank_name}")
        else:
            print(f"\n⚠️  Need more simulations for calibration")
            print(f"   Run with larger -n value (e.g., -n 800)")


def main():
    parser = argparse.ArgumentParser(description="Enhanced assessment simulation")
    parser.add_argument("--item-bank", required=True, help="Item bank name")
    parser.add_argument("-n", "--n-students", type=int, default=500, help="Number of students")
    parser.add_argument("--questions-per-student", type=int, default=30, help="Max questions per student")

    args = parser.parse_args()

    simulator = EnhancedSimulator(args.item_bank)
    simulator.run(args.n_students, args.questions_per_student)


if __name__ == "__main__":
    main()