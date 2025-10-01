#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulate Test Takers - Schema Integrated

Generates synthetic responses in assessment_sessions and responses tables.

Usage:
    python simulate_test_takers.py --db backend/adaptive_assessment.db --subject Python -n 500
"""

import argparse
import sqlite3
import random
import math
import numpy as np
from typing import List, Tuple, Dict
from dataclasses import dataclass

random.seed(42)
np.random.seed(42)


@dataclass
class Question:
    id: int
    a: float
    b: float
    c: float
    tier: str


@dataclass
class Examinee:
    id: int
    theta: float
    competence: str


class TestTakerSimulator:

    def __init__(self, db_path: str, subject: str):
        self.db_path = db_path
        self.subject = subject
        self.questions: List[Question] = []
        self.examinees: List[Examinee] = []

    def load_questions(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT id, discrimination_a, difficulty_b, guessing_c, tier
                       FROM questions
                       WHERE subject = ?
                       """, (self.subject,))

        for row in cursor.fetchall():
            self.questions.append(Question(row[0], row[1], row[2], row[3], row[4]))

        conn.close()
        return len(self.questions)

    def generate_examinees(self, n: int, distribution: str = "realistic") -> List[Examinee]:
        examinees = []

        if distribution == "realistic":
            proportions = [0.20, 0.40, 0.30, 0.10]
            competences = ["beginner", "intermediate", "advanced", "expert"]
            theta_params = {
                "beginner": (-1.5, 0.6),
                "intermediate": (0.0, 0.7),
                "advanced": (1.0, 0.6),
                "expert": (2.0, 0.5)
            }

            for i in range(n):
                rand = random.random()
                cumulative = 0
                competence = "intermediate"
                for j, prop in enumerate(proportions):
                    cumulative += prop
                    if rand < cumulative:
                        competence = competences[j]
                        break

                mean, std = theta_params[competence]
                theta = np.clip(np.random.normal(mean, std), -3.0, 3.0)
                examinees.append(Examinee(i + 1, theta, competence))

        elif distribution == "uniform":
            for i in range(n):
                theta = np.random.uniform(-2.0, 2.0)
                examinees.append(Examinee(i + 1, theta, self._theta_to_competence(theta)))

        else:
            for i in range(n):
                theta = np.clip(np.random.normal(0.0, 1.0), -3.0, 3.0)
                examinees.append(Examinee(i + 1, theta, self._theta_to_competence(theta)))

        self.examinees = examinees
        return examinees

    def _theta_to_competence(self, theta: float) -> str:
        if theta < -1.0:
            return "beginner"
        elif theta < 0.0:
            return "intermediate"
        elif theta < 1.0:
            return "advanced"
        else:
            return "expert"

    def _theta_to_tier(self, theta: float) -> str:
        if theta < -1.0:
            return "C1"
        elif theta < 0.0:
            return "C2"
        elif theta < 1.0:
            return "C3"
        else:
            return "C4"

    def probability_correct(self, theta: float, q: Question) -> float:
        exponent = q.a * (theta - q.b)
        if exponent > 700:
            return 1.0
        elif exponent < -700:
            return q.c
        return q.c + (1 - q.c) / (1 + math.exp(-exponent))

    def _fisher_information(self, theta: float, q: Question) -> float:
        p = self.probability_correct(theta, q)
        if p <= q.c or p >= 1.0: return 0.0

        q_prob = 1 - p
        p_star = (p - q.c) / (1 - q.c)
        if p_star <= 0 or p_star >= 1: return 0.0

        num = (q.a ** 2) * (p_star * (1 - p_star))
        denom = ((1 - q.c) ** 2) * p * q_prob
        return num / (denom + 1e-10)

    def simulate_adaptive(self, questions_per_examinee: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for examinee in self.examinees:
            initial_theta_map = {
                "beginner": -1.5, "intermediate": 0.0,
                "advanced": 1.5, "expert": 2.0
            }
            current_theta = initial_theta_map.get(examinee.competence, 0.0)
            current_theta += np.random.normal(0, 0.3)
            current_theta = np.clip(current_theta, -3.0, 3.0)

            # Create session
            cursor.execute("""
                           INSERT INTO assessment_sessions
                               (user_id, subject, theta, sem, tier, questions_asked, completed)
                           VALUES (?, ?, ?, 1.0, ?, 0, 0)
                           """, (examinee.id, self.subject, current_theta, self._theta_to_tier(current_theta)))

            session_id = cursor.lastrowid
            asked = set()
            q_count = 0

            for _ in range(questions_per_examinee):
                # Select max info question
                best = None
                max_info = -1

                for q in self.questions:
                    if q.id in asked:
                        continue
                    info = self._fisher_information(current_theta, q)
                    if info > max_info:
                        max_info = info
                        best = q

                if not best:
                    break

                asked.add(best.id)
                theta_before = current_theta

                # Simulate response
                prob = self.probability_correct(examinee.theta, best)
                is_correct = 1 if random.random() < prob else 0

                # Log response
                cursor.execute("""
                               INSERT INTO responses
                               (session_id, question_id, selected_option, is_correct,
                                theta_before, theta_after)
                               VALUES (?, ?, 'A', ?, ?, NULL)
                               """, (session_id, best.id, is_correct, theta_before))

                q_count += 1

                # Update theta
                gradient = best.a * (is_correct - prob)
                current_theta = np.clip(current_theta + 0.3 * gradient, -3.0, 3.0)

                # Update theta_after
                cursor.execute("""
                               UPDATE responses
                               SET theta_after = ?
                               WHERE session_id = ?
                                 AND question_id = ?
                               """, (current_theta, session_id, best.id))

            # Complete session
            cursor.execute("""
                           UPDATE assessment_sessions
                           SET theta           = ?,
                               tier            = ?,
                               questions_asked = ?,
                               completed_at    = CURRENT_TIMESTAMP,
                               completed       = 1
                           WHERE session_id = ?
                           """, (current_theta, self._theta_to_tier(current_theta), q_count, session_id))

        conn.commit()
        conn.close()

    def generate_report(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT COUNT(*), SUM(is_correct)
                       FROM responses r
                                JOIN assessment_sessions s ON r.session_id = s.session_id
                       WHERE s.subject = ?
                       """, (self.subject,))

        total, correct = cursor.fetchone()

        cursor.execute("""
                       SELECT question_id, COUNT(*)
                       FROM responses r
                                JOIN assessment_sessions s ON r.session_id = s.session_id
                       WHERE s.subject = ?
                       GROUP BY question_id
                       """, (self.subject,))

        counts = cursor.fetchall()
        conn.close()

        thetas = [e.theta for e in self.examinees]

        return {
            "examinees": len(self.examinees),
            "questions": len(self.questions),
            "responses": total,
            "accuracy": correct / total if total else 0,
            "questions_used": len(counts),
            "avg_resp_per_q": np.mean([c[1] for c in counts]) if counts else 0,
            "min_resp": min([c[1] for c in counts]) if counts else 0,
            "max_resp": max([c[1] for c in counts]) if counts else 0,
            "theta_mean": np.mean(thetas),
            "theta_std": np.std(thetas),
            "comp_dist": {
                "beginner": sum(1 for e in self.examinees if e.competence == "beginner"),
                "intermediate": sum(1 for e in self.examinees if e.competence == "intermediate"),
                "advanced": sum(1 for e in self.examinees if e.competence == "advanced"),
                "expert": sum(1 for e in self.examinees if e.competence == "expert")
            }
        }

    def print_report(self, r: Dict):
        print("\n" + "=" * 60)
        print("SIMULATION REPORT")
        print("=" * 60)
        print(f"\nSubject: {self.subject}")
        print(f"Examinees: {r['examinees']}")
        print(f"  θ: {r['theta_mean']:.2f} ± {r['theta_std']:.2f}")

        print("\nCompetence:")
        for level, count in r['comp_dist'].items():
            pct = 100 * count / r['examinees']
            print(f"  {level:12s}: {count:4d} ({pct:5.1f}%)")

        print(f"\nQuestions: {r['questions']} total, {r['questions_used']} used")
        print(f"  Avg responses: {r['avg_resp_per_q']:.1f}")
        print(f"  Range: [{r['min_resp']}, {r['max_resp']}]")

        print(f"\nResponses: {r['responses']} total")
        print(f"  Accuracy: {100 * r['accuracy']:.1f}%")

        print("\n" + "=" * 60)
        print("Next: Run recalibrate_question_bank.py")
        print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--subject", "-s", required=True)
    parser.add_argument("-n", "--n-examinees", type=int, default=500)
    parser.add_argument("-q", "--questions-per-examinee", type=int, default=30)
    parser.add_argument("--distribution", choices=["realistic", "uniform", "normal"], default="realistic")

    args = parser.parse_args()

    print(f"\nSimulator for {args.subject}...")
    sim = TestTakerSimulator(args.db, args.subject)

    n_q = sim.load_questions()
    print(f"Loaded {n_q} questions")

    if n_q == 0:
        print("No questions. Run initialize_question_bank.py first.")
        return

    print(f"Generating {args.n_examinees} examinees...")
    sim.generate_examinees(args.n_examinees, args.distribution)

    print("Simulating assessments...")
    sim.simulate_adaptive(args.questions_per_examinee)

    report = sim.generate_report()
    sim.print_report(report)


if __name__ == "__main__":
    main()