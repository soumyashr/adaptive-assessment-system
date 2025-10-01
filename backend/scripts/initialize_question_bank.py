#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize Question Bank - Schema Integrated

Populates questions table with IRT-calibrated parameters.

Usage:
    python initialize_question_bank.py --input questions.txt --db backend/adaptive_assessment.db --subject Python
"""

import argparse
import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Dict

DEFAULT_DISCRIMINATION = 1.5
DEFAULT_GUESSING = 0.25

TIER_RANGES = {
    "C1": {"b_min": -2.0, "b_max": 0.0},
    "C2": {"b_min": -1.0, "b_max": 1.0},
    "C3": {"b_min": 0.0, "b_max": 2.0},
    "C4": {"b_min": 1.0, "b_max": 3.0}
}


@dataclass
class Question:
    subject: str
    question_id: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    answer: str
    topic: str
    content_area: Optional[str]
    tier: str
    discrimination_a: float
    difficulty_b: float
    guessing_c: float


class QuestionBankInitializer:

    def __init__(self, subject: str):
        self.subject = subject
        self.questions: List[Question] = []
        self.tier_counts = {"C1": 0, "C2": 0, "C3": 0, "C4": 0}

    def parse_raw_format(self, text: str) -> List[Dict]:
        questions = []
        current = {}

        for line in text.strip().split('\n'):
            line = line.strip()

            if line == '---':
                if current:
                    questions.append(current)
                    current = {}
                continue

            if not line:
                continue

            if line.startswith('Question:'):
                current['question'] = line[9:].strip()
            elif line.startswith('A)'):
                current['option_a'] = line[2:].strip()
            elif line.startswith('B)'):
                current['option_b'] = line[2:].strip()
            elif line.startswith('C)'):
                current['option_c'] = line[2:].strip()
            elif line.startswith('D)'):
                current['option_d'] = line[2:].strip()
            elif line.startswith('Answer:'):
                current['answer'] = line[7:].strip().upper()
            elif line.startswith('Tier:'):
                current['tier'] = line[5:].strip().upper()
            elif line.startswith('Topic:'):
                current['topic'] = line[6:].strip()
            elif line.startswith('Content:'):
                current['content'] = line[8:].strip()
            elif line.startswith('Difficulty:'):
                current['difficulty'] = line[11:].strip().lower()

        if current:
            questions.append(current)

        return questions

    def calculate_difficulty_b(self, tier: str, difficulty_label: Optional[str] = None) -> float:
        b_min = TIER_RANGES[tier]["b_min"]
        b_max = TIER_RANGES[tier]["b_max"]

        if difficulty_label:
            label_map = {'easy': 0.25, 'medium': 0.50, 'hard': 0.75}
            normalized = label_map.get(difficulty_label, 0.50)
            return round(b_min + (b_max - b_min) * normalized, 2)

        count = self.tier_counts[tier]
        spacing = (b_max - b_min) / 4
        position = count % 5
        return round(b_min + (spacing * position), 2)

    def add_question(self, question_text: str, options: List[str],
                     answer: str, tier: str, topic: str,
                     content_area: Optional[str] = None,
                     difficulty_label: Optional[str] = None) -> Question:
        if len(options) != 4:
            raise ValueError("Need 4 options")
        if answer.upper() not in ['A', 'B', 'C', 'D']:
            raise ValueError("Answer must be A/B/C/D")

        difficulty_b = self.calculate_difficulty_b(tier, difficulty_label)
        question_id = f"{self.subject}_{tier}_{self.tier_counts[tier] + 1:03d}"

        q = Question(
            subject=self.subject,
            question_id=question_id,
            question=question_text,
            option_a=options[0],
            option_b=options[1],
            option_c=options[2],
            option_d=options[3],
            answer=answer.upper(),
            topic=topic,
            content_area=content_area or topic,
            tier=tier.upper(),
            discrimination_a=DEFAULT_DISCRIMINATION,
            difficulty_b=difficulty_b,
            guessing_c=DEFAULT_GUESSING
        )

        self.questions.append(q)
        self.tier_counts[tier.upper()] += 1
        return q

    def load_from_file(self, filepath: str, default_tier: str = "C2") -> int:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        raw = self.parse_raw_format(text)

        for rq in raw:
            try:
                self.add_question(
                    question_text=rq.get('question', ''),
                    options=[
                        rq.get('option_a', ''),
                        rq.get('option_b', ''),
                        rq.get('option_c', ''),
                        rq.get('option_d', '')
                    ],
                    answer=rq.get('answer', 'A'),
                    tier=rq.get('tier', default_tier),
                    topic=rq.get('topic', 'General'),
                    content_area=rq.get('content'),
                    difficulty_label=rq.get('difficulty')
                )
            except Exception as e:
                print(f"Error: {e}")
                continue

        return len(raw)

    def export_to_db(self, db_path: str):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS questions
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           subject
                           VARCHAR
                       (
                           50
                       ) NOT NULL,
                           question_id VARCHAR
                       (
                           50
                       ) NOT NULL,
                           question TEXT NOT NULL,
                           option_a TEXT NOT NULL,
                           option_b TEXT NOT NULL,
                           option_c TEXT NOT NULL,
                           option_d TEXT NOT NULL,
                           answer VARCHAR
                       (
                           1
                       ) NOT NULL,
                           topic VARCHAR
                       (
                           100
                       ) NOT NULL,
                           content_area VARCHAR
                       (
                           100
                       ),
                           tier VARCHAR
                       (
                           10
                       ) NOT NULL,
                           discrimination_a FLOAT NOT NULL,
                           difficulty_b FLOAT NOT NULL,
                           guessing_c FLOAT NOT NULL,
                           created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                           )
                       """)

        inserted = 0
        for q in self.questions:
            try:
                cursor.execute("""
                               INSERT INTO questions
                               (subject, question_id, question, option_a, option_b, option_c, option_d,
                                answer, topic, content_area, tier, discrimination_a, difficulty_b, guessing_c)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                               """, (q.subject, q.question_id, q.question, q.option_a, q.option_b,
                                     q.option_c, q.option_d, q.answer, q.topic, q.content_area,
                                     q.tier, q.discrimination_a, q.difficulty_b, q.guessing_c))
                inserted += 1
            except sqlite3.IntegrityError:
                print(f"Skipped duplicate: {q.question_id}")
                continue

        conn.commit()
        conn.close()

        print(f"\n✓ Exported {inserted} questions to {db_path}")
        print(f"  Subject: {self.subject}")
        print(f"  IRT: a={DEFAULT_DISCRIMINATION}, c={DEFAULT_GUESSING}")

        return inserted

    def print_summary(self):
        if not self.questions:
            print("No questions loaded")
            return

        print(f"\n=== Question Bank Summary ===")
        print(f"Subject: {self.subject}")
        print(f"Total: {len(self.questions)}")

        print("\nBy Tier:")
        for tier in sorted(self.tier_counts.keys()):
            if self.tier_counts[tier] > 0:
                diffs = [q.difficulty_b for q in self.questions if q.tier == tier]
                print(f"  {tier}: {self.tier_counts[tier]} questions, "
                      f"b ∈ [{min(diffs):.2f}, {max(diffs):.2f}]")

        topics = {}
        for q in self.questions:
            topics[q.topic] = topics.get(q.topic, 0) + 1

        if topics:
            print("\nBy Topic:")
            for topic in sorted(topics.keys()):
                print(f"  {topic}: {topics[topic]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--subject", "-s", required=True)
    parser.add_argument("--tier", "-t", choices=["C1", "C2", "C3", "C4"], default="C2")

    args = parser.parse_args()

    init = QuestionBankInitializer(args.subject)

    count = init.load_from_file(args.input, args.tier)
    print(f"Loaded {count} questions from {args.input}")

    if not init.questions:
        print("No valid questions")
        return

    init.print_summary()
    init.export_to_db(args.db)


if __name__ == "__main__":
    main()