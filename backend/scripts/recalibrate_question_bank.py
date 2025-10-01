#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recalibrate Question Bank - Updated for Schema

Recalibrates IRT parameters in 'questions' table using data from 'responses'.

Schema integration:
- Reads responses from responses + assessment_sessions tables
- Updates discrimination_a, difficulty_b, guessing_c in questions table
- Generates quality reports

Usage:
    python recalibrate_question_bank.py --db backend/adaptive_assessment.db --subject Python
"""

import argparse
import sqlite3
import numpy as np
import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from scipy.optimize import minimize
import warnings

warnings.filterwarnings('ignore')


@dataclass
class QuestionData:
    """Question with response data"""
    id: int
    subject: str
    question_id: str
    current_a: float
    current_b: float
    current_c: float
    tier: str
    responses: List[Tuple[int, int]]  # [(user_id, correct), ...]
    n_responses: int


@dataclass
class CalibrationResult:
    """Recalibration result"""
    question_id: int
    question_db_id: str
    old_a: float
    old_b: float
    old_c: float
    new_a: float
    new_b: float
    new_c: float
    n_responses: int
    accuracy: float
    point_biserial: float
    fit_warning: Optional[str]


class IRTRecalibrator:
    """IRT parameter estimation from response data"""

    def __init__(self, db_path: str, subject: str, min_responses: int = 100):
        self.db_path = db_path
        self.subject = subject
        self.min_responses = min_responses
        self.questions: Dict[int, QuestionData] = {}
        self.user_thetas: Dict[int, float] = {}

        # Bayesian priors
        self.prior_a_mean = 1.5
        self.prior_a_std = 0.5
        self.prior_b_mean = 0.0
        self.prior_b_std = 2.0
        self.prior_c_mean = 0.25
        self.prior_c_std = 0.05

    def load_data(self) -> int:
        """Load questions and responses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load questions for subject
        cursor.execute("""
                       SELECT id,
                              subject,
                              question_id,
                              discrimination_a,
                              difficulty_b,
                              guessing_c,
                              tier
                       FROM questions
                       WHERE subject = ?
                       """, (self.subject,))

        for row in cursor.fetchall():
            q_id = row[0]
            self.questions[q_id] = QuestionData(
                id=q_id,
                subject=row[1],
                question_id=row[2],
                current_a=row[3],
                current_b=row[4],
                current_c=row[5],
                tier=row[6],
                responses=[],
                n_responses=0
            )

        # Load responses (only completed sessions)
        cursor.execute("""
                       SELECT r.question_id, s.user_id, r.is_correct
                       FROM responses r
                                JOIN assessment_sessions s ON r.session_id = s.session_id
                       WHERE s.subject = ?
                         AND s.completed = 1
                       """, (self.subject,))

        for row in cursor.fetchall():
            question_id = row[0]
            user_id = row[1]
            correct = row[2]

            if question_id in self.questions:
                self.questions[question_id].responses.append((user_id, correct))
                self.questions[question_id].n_responses += 1

        conn.close()

        eligible = sum(1 for q in self.questions.values()
                       if q.n_responses >= self.min_responses)

        print(f"Loaded {len(self.questions)} questions")
        print(f"  {eligible} with >= {self.min_responses} responses (eligible)")
        print(f"  {len(self.questions) - eligible} with insufficient data")

        return eligible

    def estimate_user_abilities(self):
        """Estimate theta for each user using MLE"""
        print("\nEstimating user abilities...")

        # Collect responses by user
        user_responses = {}
        for question in self.questions.values():
            for user_id, correct in question.responses:
                if user_id not in user_responses:
                    user_responses[user_id] = []
                user_responses[user_id].append({
                    'question_id': question.id,
                    'correct': correct,
                    'a': question.current_a,
                    'b': question.current_b,
                    'c': question.current_c
                })

        # Estimate theta for each user
        for user_id, responses in user_responses.items():
            theta = self._estimate_theta_mle(responses)
            self.user_thetas[user_id] = theta

        thetas = list(self.user_thetas.values())
        print(f"Estimated {len(thetas)} user abilities")
        print(f"  Mean θ: {np.mean(thetas):.2f}")
        print(f"  Std θ: {np.std(thetas):.2f}")
        print(f"  Range: [{np.min(thetas):.2f}, {np.max(thetas):.2f}]")

    def _estimate_theta_mle(self, responses: List[Dict]) -> float:
        """Estimate theta using Newton-Raphson"""
        accuracy = sum(r['correct'] for r in responses) / len(responses)

        # Starting value
        if accuracy > 0.95:
            theta = 2.0
        elif accuracy > 0.75:
            theta = 1.0
        elif accuracy > 0.5:
            theta = 0.0
        elif accuracy > 0.25:
            theta = -1.0
        else:
            theta = -2.0

        # Newton-Raphson
        for _ in range(20):
            first_d = 0.0
            second_d = 0.0

            for r in responses:
                p = self._prob_3pl(theta, r['a'], r['b'], r['c'])
                p = np.clip(p, 0.001, 0.999)
                q = 1 - p

                if r['correct']:
                    first_d += r['a'] * q / p
                else:
                    first_d -= r['a'] * p / q

                second_d -= (r['a'] ** 2) * p * q

            if abs(second_d) < 1e-6:
                break

            delta = -first_d / second_d
            delta = np.clip(delta, -0.5, 0.5)
            theta += delta
            theta = np.clip(theta, -3.0, 3.0)

            if abs(delta) < 0.001:
                break

        return theta

    def _prob_3pl(self, theta: float, a: float, b: float, c: float) -> float:
        """3PL probability"""
        exponent = a * (theta - b)
        if exponent > 700:
            return 1.0
        elif exponent < -700:
            return c
        return c + (1 - c) / (1 + math.exp(-exponent))

    def recalibrate_question(self, question: QuestionData) -> Optional[CalibrationResult]:
        """Recalibrate single question"""
        if question.n_responses < self.min_responses:
            return None

        # Prepare data
        thetas = []
        responses = []
        for user_id, correct in question.responses:
            if user_id in self.user_thetas:
                thetas.append(self.user_thetas[user_id])
                responses.append(correct)

        if len(thetas) < self.min_responses:
            return None

        thetas = np.array(thetas)
        responses = np.array(responses)

        accuracy = np.mean(responses)

        # Point-biserial correlation
        if np.std(thetas) > 0 and 0 < accuracy < 1:
            point_biserial = np.corrcoef(thetas, responses)[0, 1]
        else:
            point_biserial = 0.0

        # Optimize parameters
        initial = [question.current_a, question.current_b, question.current_c]

        result = minimize(
            self._negative_log_likelihood,
            initial,
            args=(thetas, responses),
            method='L-BFGS-B',
            bounds=[(0.3, 3.0), (-3.0, 3.0), (0.0, 0.5)]
        )

        new_a, new_b, new_c = result.x

        # Bayesian shrinkage for small samples
        if question.n_responses < 200:
            shrinkage = self.min_responses / question.n_responses
            new_a = shrinkage * self.prior_a_mean + (1 - shrinkage) * new_a
            new_b = shrinkage * self.prior_b_mean + (1 - shrinkage) * new_b
            new_c = shrinkage * self.prior_c_mean + (1 - shrinkage) * new_c

        # Quality checks
        fit_warning = None

        if point_biserial < 0.15:
            fit_warning = "LOW_DISCRIMINATION"
        elif point_biserial < 0:
            fit_warning = "NEGATIVE_DISCRIMINATION"

        if new_a < 0.5:
            fit_warning = "VERY_LOW_A"

        if accuracy < 0.1 or accuracy > 0.95:
            fit_warning = "EXTREME_DIFFICULTY"

        return CalibrationResult(
            question_id=question.id,
            question_db_id=question.question_id,
            old_a=question.current_a,
            old_b=question.current_b,
            old_c=question.current_c,
            new_a=new_a,
            new_b=new_b,
            new_c=new_c,
            n_responses=question.n_responses,
            accuracy=accuracy,
            point_biserial=point_biserial,
            fit_warning=fit_warning
        )

    def _negative_log_likelihood(self, params: np.ndarray,
                                 thetas: np.ndarray,
                                 responses: np.ndarray) -> float:
        """Negative log-likelihood with Bayesian priors"""
        a, b, c = params

        a = np.clip(a, 0.3, 3.0)
        b = np.clip(b, -3.0, 3.0)
        c = np.clip(c, 0.0, 0.5)

        # Log-likelihood
        log_lik = 0.0
        for theta, correct in zip(thetas, responses):
            p = self._prob_3pl(theta, a, b, c)
            p = np.clip(p, 0.001, 0.999)

            if correct:
                log_lik += np.log(p)
            else:
                log_lik += np.log(1 - p)

        # Priors
        prior = 0.0
        prior += -0.5 * ((a - self.prior_a_mean) / self.prior_a_std) ** 2
        prior += -0.5 * ((b - self.prior_b_mean) / self.prior_b_std) ** 2
        prior += -0.5 * ((c - self.prior_c_mean) / self.prior_c_std) ** 2

        return -(log_lik + prior)

    def update_database(self, results: List[CalibrationResult]):
        """Update questions table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for result in results:
            cursor.execute("""
                           UPDATE questions
                           SET discrimination_a = ?,
                               difficulty_b     = ?,
                               guessing_c       = ?
                           WHERE id = ?
                           """, (result.new_a, result.new_b, result.new_c, result.question_id))

        conn.commit()
        conn.close()

    def generate_report(self, results: List[CalibrationResult]) -> str:
        """Generate report"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"IRT RECALIBRATION REPORT - {self.subject}")
        lines.append("=" * 80)
        lines.append("")

        total = len(results)
        flagged = sum(1 for r in results if r.fit_warning)

        lines.append(f"Questions Recalibrated: {total}")
        lines.append(f"Questions Flagged: {flagged}")
        lines.append("")

        # Parameter changes
        a_changes = [abs(r.new_a - r.old_a) for r in results]
        b_changes = [abs(r.new_b - r.old_b) for r in results]
        c_changes = [abs(r.new_c - r.old_c) for r in results]

        lines.append("Average Parameter Changes:")
        lines.append(f"  Discrimination (a): {np.mean(a_changes):.3f} ± {np.std(a_changes):.3f}")
        lines.append(f"  Difficulty (b):     {np.mean(b_changes):.3f} ± {np.std(b_changes):.3f}")
        lines.append(f"  Guessing (c):       {np.mean(c_changes):.3f} ± {np.std(c_changes):.3f}")
        lines.append("")

        # Top changes
        lines.append("Top 10 Largest Changes:")
        lines.append("-" * 80)

        sorted_results = sorted(results,
                                key=lambda r: abs(r.new_a - r.old_a) + abs(r.new_b - r.old_b),
                                reverse=True)

        for r in sorted_results[:10]:
            lines.append(f"{r.question_db_id}:")
            lines.append(f"  a: {r.old_a:.2f} → {r.new_a:.2f} (Δ={r.new_a - r.old_a:+.2f})")
            lines.append(f"  b: {r.old_b:.2f} → {r.new_b:.2f} (Δ={r.new_b - r.old_b:+.2f})")
            lines.append(f"  c: {r.old_c:.2f} → {r.new_c:.2f} (Δ={r.new_c - r.old_c:+.2f})")
            lines.append(f"  Responses: {r.n_responses}, Accuracy: {r.accuracy:.2f}")
            lines.append("")

        # Flagged questions
        if flagged > 0:
            lines.append("=" * 80)
            lines.append("FLAGGED QUESTIONS")
            lines.append("=" * 80)
            lines.append("")

            for r in results:
                if r.fit_warning:
                    lines.append(f"{r.question_db_id}: {r.fit_warning}")
                    lines.append(f"  a={r.new_a:.2f}, b={r.new_b:.2f}, c={r.new_c:.2f}")
                    lines.append(f"  Point-biserial: {r.point_biserial:.3f}")
                    lines.append(f"  Accuracy: {r.accuracy:.2f}, N={r.n_responses}")
                    lines.append("")

        # Quality metrics
        lines.append("=" * 80)
        lines.append("QUALITY METRICS")
        lines.append("=" * 80)
        lines.append("")

        pb_values = [r.point_biserial for r in results]
        lines.append(f"Point-Biserial: {np.mean(pb_values):.3f} ± {np.std(pb_values):.3f}")
        lines.append(f"Range: [{np.min(pb_values):.3f}, {np.max(pb_values):.3f}]")
        lines.append("")

        excellent = sum(1 for pb in pb_values if pb > 0.4)
        good = sum(1 for pb in pb_values if 0.3 <= pb <= 0.4)
        acceptable = sum(1 for pb in pb_values if 0.15 <= pb < 0.3)
        poor = sum(1 for pb in pb_values if pb < 0.15)

        lines.append("Quality Distribution:")
        lines.append(f"  Excellent (>0.40):  {excellent} ({100 * excellent / total:.1f}%)")
        lines.append(f"  Good (0.30-0.40):   {good} ({100 * good / total:.1f}%)")
        lines.append(f"  Acceptable (0.15-0.30): {acceptable} ({100 * acceptable / total:.1f}%)")
        lines.append(f"  Poor (<0.15):       {poor} ({100 * poor / total:.1f}%)")
        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def run(self) -> List[CalibrationResult]:
        """Run recalibration"""
        print("\n" + "=" * 80)
        print(f"IRT RECALIBRATION - {self.subject}")
        print("=" * 80 + "\n")

        eligible = self.load_data()

        if eligible == 0:
            print(f"\nNo questions with >= {self.min_responses} responses")
            return []

        self.estimate_user_abilities()

        print(f"\nRecalibrating {eligible} questions...")
        results = []

        for i, question in enumerate(self.questions.values(), 1):
            if question.n_responses >= self.min_responses:
                result = self.recalibrate_question(question)
                if result:
                    results.append(result)

                if i % 10 == 0:
                    print(f"  Progress: {i}/{len(self.questions)}")

        print(f"\nRecalibrated {len(results)} questions")

        if results:
            print("Updating database...")
            self.update_database(results)
            print("Complete")

        return results


def main():
    parser = argparse.ArgumentParser(description="Recalibrate IRT parameters")
    parser.add_argument("--db", required=True, help="Database path")
    parser.add_argument("--subject", "-s", required=True, help="Subject")
    parser.add_argument("--min-responses", type=int, default=100,
                        help="Min responses per question (default: 100)")
    parser.add_argument("--report", help="Output report file (optional)")

    args = parser.parse_args()

    recalibrator = IRTRecalibrator(args.db, args.subject, args.min_responses)
    results = recalibrator.run()

    if not results:
        print("\nNo recalibration performed")
        return

    report = recalibrator.generate_report(results)
    print("\n" + report)

    if args.report:
        with open(args.report, 'w') as f:
            f.write(report)
        print(f"\nReport saved: {args.report}")

    print("\n" + "=" * 80)
    print("Recalibration complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()