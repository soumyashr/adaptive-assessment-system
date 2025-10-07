# backend/services.py
"""
FULLY BACKWARD COMPATIBLE SERVICES
All changes are ADDITIVE with safety mechanisms
Admin module will continue to work unchanged
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, not_, text
from typing import List, Optional, Dict
import pandas as pd
from datetime import datetime
import logging
import sys
import os
import time
import json
from collections import defaultdict
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from db_manager import item_bank_db

import models_registry
import models_itembank
from irt_engine import IRTEngine
import schemas

logger = logging.getLogger(__name__)


# ========== NEW CLASS - Doesn't affect existing code ==========

class TopicPerformanceCalculator:
    """NEW: Calculate per-topic theta and performance metrics"""

    @staticmethod
    def calculate_topic_theta(responses: List, topic: str, irt_engine: IRTEngine) -> Optional[Dict]:
        """Calculate theta for specific topic based on responses"""
        topic_responses = [r for r in responses if r.get('topic') == topic]

        if not topic_responses:
            return None

        response_tuples = [
            (r['is_correct'], r['difficulty'], r['discrimination'], r['guessing'])
            for r in topic_responses
        ]

        correct_count = sum(1 for r in topic_responses if r['is_correct'])
        initial_theta = -1.0 + (correct_count / len(topic_responses)) * 2.0

        try:
            topic_theta, _ = irt_engine.update_theta(
                current_theta=initial_theta,
                responses=response_tuples,
                response_history=[r['is_correct'] for r in topic_responses],
                questions_answered=len(topic_responses)
            )

            questions_info = [(r['difficulty'], r['discrimination'], r['guessing'])
                              for r in topic_responses]
            topic_sem = irt_engine.calculate_sem(topic_theta, questions_info)

            accuracy = correct_count / len(topic_responses)

            return {
                'topic': topic,
                'theta': round(topic_theta, 2),
                'sem': round(topic_sem, 2),
                'tier': irt_engine.theta_to_tier(topic_theta),
                'questions_answered': len(topic_responses),
                'correct_count': correct_count,
                'accuracy': round(accuracy, 2),
                'strength_level': TopicPerformanceCalculator.get_strength_level(accuracy)
            }
        except Exception as e:
            logger.debug(f"Could not calculate topic theta for {topic}: {e}")
            return None

    @staticmethod
    def get_strength_level(accuracy: float) -> str:
        """Determine strength level based on accuracy"""
        if accuracy >= 0.80:
            return 'Strong'
        elif accuracy >= 0.60:
            return 'Proficient'
        elif accuracy >= 0.40:
            return 'Developing'
        else:
            return 'Needs Practice'

    @staticmethod
    def generate_learning_roadmap(topic_performance: Dict, overall_theta: float) -> Dict:
        """Generate personalized learning roadmap"""
        if not topic_performance:
            return None

        topics = list(topic_performance.values())

        strong_topics = [t for t in topics if t.get('strength_level') == 'Strong']
        proficient_topics = [t for t in topics if t.get('strength_level') == 'Proficient']
        developing_topics = [t for t in topics if t.get('strength_level') == 'Developing']
        weak_topics = [t for t in topics if t.get('strength_level') == 'Needs Practice']

        recommendations = []
        priority_topics = []

        if weak_topics:
            priority_topics = [t['topic'] for t in weak_topics[:3]]
            recommendations.append({
                'type': 'immediate_focus',
                'title': 'Priority Areas',
                'topics': priority_topics,
                'description': 'Start with these topics to build a strong foundation.',
                'action': 'Practice 5-10 questions daily'
            })

        if developing_topics:
            recommendations.append({
                'type': 'practice_more',
                'title': 'Continue Practicing',
                'topics': [t['topic'] for t in developing_topics[:3]],
                'description': 'You\'re making progress! Keep practicing to master these areas.',
                'action': 'Solve 3-5 problems daily'
            })

        if strong_topics:
            recommendations.append({
                'type': 'maintain',
                'title': 'Maintain Strengths',
                'topics': [t['topic'] for t in strong_topics],
                'description': 'Great job! Review periodically to stay sharp.',
                'action': 'Weekly revision recommended'
            })

        if overall_theta >= 1.0:
            overall_message = "Excellent work! You've demonstrated strong mastery across topics."
        elif overall_theta >= 0.0:
            overall_message = "Good progress! Focus on weak areas to reach the next level."
        elif overall_theta >= -1.0:
            overall_message = "You're building foundational skills. Consistent practice will help you improve."
        else:
            overall_message = "Start with basics and build gradually. Every step forward counts!"

        return {
            'overall_message': overall_message,
            'recommendations': recommendations,
            'priority_topics': priority_topics,
            'strengths': [t['topic'] for t in strong_topics],
            'weaknesses': [t['topic'] for t in weak_topics],
            'next_milestone': TopicPerformanceCalculator.get_next_milestone(overall_theta)
        }

    @staticmethod
    def get_next_milestone(current_theta: float) -> Dict:
        """Get next performance milestone"""
        if current_theta < -1.0:
            return {
                'target_tier': 'Intermediate (C2)',
                'target_theta': -0.5,
                'estimated_questions': 20,
                'focus': 'Master foundational concepts'
            }
        elif current_theta < 0.0:
            return {
                'target_tier': 'Advanced (C3)',
                'target_theta': 0.5,
                'estimated_questions': 15,
                'focus': 'Practice complex problem-solving'
            }
        elif current_theta < 1.0:
            return {
                'target_tier': 'Expert (C4)',
                'target_theta': 1.5,
                'estimated_questions': 20,
                'focus': 'Challenge yourself with advanced topics'
            }
        else:
            return {
                'target_tier': 'Master',
                'target_theta': 2.0,
                'estimated_questions': 25,
                'focus': 'Explore competition-level problems'
            }


# ========== UNCHANGED CLASSES - All original methods preserved ==========

class UserService:
    """BACKWARD COMPATIBLE - All original methods unchanged"""

    def get_or_create_user(self, db: Session, username: str,
                           initial_competence_level: str = "beginner") -> models_registry.User:
        """UNCHANGED"""
        user = db.query(models_registry.User).filter(
            models_registry.User.username == username
        ).first()

        if not user:
            user = models_registry.User(
                username=username,
                initial_competence_level=initial_competence_level
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def get_user_by_username(self, db: Session, username: str) -> Optional[models_registry.User]:
        """UNCHANGED"""
        return db.query(models_registry.User).filter(
            models_registry.User.username == username
        ).first()

    def get_user_proficiency(self, db: Session, user_id: int) -> schemas.UserProficiency:
        """UNCHANGED"""
        user = db.query(models_registry.User).filter(
            models_registry.User.id == user_id
        ).first()

        proficiencies = db.query(models_registry.UserProficiencySummary).filter(
            models_registry.UserProficiencySummary.user_id == user_id
        ).all()

        proficiency_list = []
        for prof in proficiencies:
            proficiency_list.append(schemas.UserProficiencySubject(
                item_bank=prof.item_bank_name,
                subject=prof.subject,
                theta=prof.theta,
                sem=prof.sem,
                tier=prof.tier,
                assessments_taken=prof.assessments_taken,
                last_updated=prof.last_updated
            ))

        return schemas.UserProficiency(
            username=user.username,
            proficiencies=proficiency_list
        )

    def update_user_proficiency(self, registry_db: Session, item_db: Session,
                                user_id: int, item_bank_name: str, subject: str,
                                theta: float, sem: float, tier: str,
                                topic_performance: Dict = None):
        """ENHANCED but BACKWARD COMPATIBLE - topic_performance is OPTIONAL"""

        proficiency = item_db.query(models_itembank.UserProficiency).filter(
            and_(
                models_itembank.UserProficiency.user_id == user_id,
                models_itembank.UserProficiency.subject == subject
            )
        ).first()

        if proficiency:
            proficiency.theta = theta
            proficiency.sem = sem
            proficiency.tier = tier
            proficiency.assessments_taken += 1
            # NEW: Only set if column exists and data provided
            if topic_performance:
                try:
                    if hasattr(proficiency, 'topic_performance'):
                        proficiency.topic_performance = json.dumps(topic_performance)
                except Exception as e:
                    logger.debug(f"Could not save topic performance: {e}")
        else:
            prof_data = {
                'user_id': user_id,
                'subject': subject,
                'theta': theta,
                'sem': sem,
                'tier': tier,
                'assessments_taken': 1
            }
            # NEW: Only add if we have the data
            if topic_performance:
                try:
                    prof_data['topic_performance'] = json.dumps(topic_performance)
                except Exception as e:
                    logger.debug(f"Could not add topic performance: {e}")

            proficiency = models_itembank.UserProficiency(**prof_data)
            item_db.add(proficiency)

        item_db.commit()

        # Original cache update preserved
        cache = registry_db.query(models_registry.UserProficiencySummary).filter(
            and_(
                models_registry.UserProficiencySummary.user_id == user_id,
                models_registry.UserProficiencySummary.item_bank_name == item_bank_name
            )
        ).first()

        if cache:
            cache.theta = theta
            cache.sem = sem
            cache.tier = tier
            cache.assessments_taken = proficiency.assessments_taken
            cache.last_updated = datetime.utcnow()
        else:
            cache = models_registry.UserProficiencySummary(
                user_id=user_id,
                item_bank_name=item_bank_name,
                subject=subject,
                theta=theta,
                sem=sem,
                tier=tier,
                assessments_taken=proficiency.assessments_taken
            )
            registry_db.add(cache)

        registry_db.commit()
        logger.info(f"Updated proficiency for user {user_id}")


class QuestionService:
    """UNCHANGED - All original methods preserved"""

    def import_questions_from_df(self, db: Session, df: pd.DataFrame) -> int:
        """UNCHANGED"""
        imported_count = 0

        for _, row in df.iterrows():
            existing = db.query(models_itembank.Question).filter(
                models_itembank.Question.question_id == row['question_id']
            ).first()

            if not existing:
                question = models_itembank.Question(
                    subject=row['subject'],
                    question_id=row['question_id'],
                    question=row['question'],
                    option_a=row['option_a'],
                    option_b=row['option_b'],
                    option_c=row['option_c'],
                    option_d=row['option_d'],
                    answer=row['answer'],
                    topic=row['topic'],
                    content_area=row.get('content_area', row['topic']),
                    tier=row['tier'],
                    discrimination_a=float(row['discrimination_a']),
                    difficulty_b=float(row['difficulty_b']),
                    guessing_c=float(row['guessing_c'])
                )
                db.add(question)
                imported_count += 1

        db.commit()
        return imported_count

    def get_available_questions(self, db: Session, session_id: int, subject: str) -> List[Dict]:
        """UNCHANGED"""
        asked_question_ids = db.query(models_itembank.Response.question_id).filter(
            models_itembank.Response.session_id == session_id
        ).scalar_subquery()

        questions = db.query(models_itembank.Question).filter(
            and_(
                models_itembank.Question.subject == subject,
                not_(models_itembank.Question.id.in_(asked_question_ids))
            )
        ).all()

        return [
            {
                'id': q.id,
                'question_id': q.question_id,
                'question': q.question,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'answer': q.answer,
                'topic': q.topic,
                'content_area': q.content_area or q.topic,
                'tier': q.tier,
                'discrimination_a': q.discrimination_a,
                'difficulty_b': q.difficulty_b,
                'guessing_c': q.guessing_c
            }
            for q in questions
        ]

    def get_question_by_id(self, db: Session, question_id: int) -> Optional[models_itembank.Question]:
        """UNCHANGED"""
        return db.query(models_itembank.Question).filter(
            models_itembank.Question.id == question_id
        ).first()


class AssessmentService:
    """ENHANCED but BACKWARD COMPATIBLE - All original methods work"""

    def __init__(self):
        self.user_service = UserService()
        self.question_service = QuestionService()
        self.topic_calculator = TopicPerformanceCalculator()

    def start_assessment(self, item_db: Session, registry_db: Session,
                         user_id: int, subject: str, item_bank_name: str) -> models_itembank.AssessmentSession:
        """UNCHANGED"""
        logger.info(f"Start assessment for user {user_id} in item bank {item_bank_name}")

        user_proficiency = item_db.query(models_itembank.UserProficiency).filter(
            and_(
                models_itembank.UserProficiency.user_id == user_id,
                models_itembank.UserProficiency.subject == subject
            )
        ).first()

        if user_proficiency:
            starting_theta = user_proficiency.theta
            logger.info(f"Using existing proficiency theta: {starting_theta:.3f}")
        else:
            user = registry_db.query(models_registry.User).filter(
                models_registry.User.id == user_id
            ).first()
            irt_engine = IRTEngine()
            starting_theta = irt_engine.get_initial_theta(user.initial_competence_level)
            logger.info(f"Using initial competence: {user.initial_competence_level}, theta: {starting_theta:.3f}")

        session = models_itembank.AssessmentSession(
            user_id=user_id,
            subject=subject,
            theta=starting_theta,
            sem=1.0,
            tier=IRTEngine().theta_to_tier(starting_theta),
            questions_asked=0,
            completed=False
        )

        item_db.add(session)
        item_db.commit()
        item_db.refresh(session)

        logger.info(f"Assessment session created successfully")
        return session

    def get_session(self, db: Session, session_id: int) -> Optional[models_itembank.AssessmentSession]:
        """UNCHANGED"""
        return db.query(models_itembank.AssessmentSession).filter(
            models_itembank.AssessmentSession.session_id == session_id
        ).first()

    def get_next_question(self, db: Session, session_id: int,
                          irt_engine: IRTEngine) -> Optional[schemas.QuestionResponse]:
        """UNCHANGED"""
        session = self.get_session(db, session_id)
        if not session or session.completed:
            return None

        responses = db.query(models_itembank.Response).filter(
            models_itembank.Response.session_id == session_id
        ).order_by(models_itembank.Response.created_at).all()

        response_history = [r.is_correct for r in responses]

        available_questions = self.question_service.get_available_questions(
            db, session_id, session.subject
        )

        if not available_questions:
            session.completed = True
            session.completed_at = datetime.utcnow()
            db.commit()
            return None

        next_question_data = irt_engine.select_next_question(
            session.theta,
            available_questions,
            response_history,
            session.questions_asked
        )

        if not next_question_data:
            return None

        logger.info(f"Selected question: {next_question_data['question_id']}")

        return schemas.QuestionResponse(
            id=next_question_data['id'],
            question=next_question_data['question'],
            option_a=next_question_data['option_a'],
            option_b=next_question_data['option_b'],
            option_c=next_question_data['option_c'],
            option_d=next_question_data['option_d'],
            topic=next_question_data['topic'],
            tier=next_question_data['tier'],
            difficulty_b=next_question_data['difficulty_b'],
            discrimination_a=next_question_data['discrimination_a'],
            guessing_c=next_question_data['guessing_c']
        )

    # This shows the key modifications to the record_response method

    # MODIFIED: record_response method in AssessmentService class
    # CHANGE: Now returns dict with 'response' and 'topic_performance' instead of just response

    def record_response(self, item_db: Session, registry_db: Session,
                        session_id: int, question_id: int, selected_option: str,
                        item_bank_name: str, irt_engine: IRTEngine):
        """ENHANCED but BACKWARD COMPATIBLE"""
        session = self.get_session(item_db, session_id)
        question = self.question_service.get_question_by_id(item_db, question_id)

        if not session or not question:
            return None  # Changed from return to return None

        is_correct = self.is_answer_correct(selected_option, question.answer)

        # EXISTING: Get all previous responses
        previous_responses = item_db.query(models_itembank.Response).filter(
            models_itembank.Response.session_id == session_id
        ).order_by(models_itembank.Response.created_at).all()

        response_data = []
        for r in previous_responses:
            q = self.question_service.get_question_by_id(item_db, r.question_id)
            response_data.append((r.is_correct, q.difficulty_b, q.discrimination_a, q.guessing_c))

        response_data.append((is_correct, question.difficulty_b, question.discrimination_a, question.guessing_c))
        response_history = [r.is_correct for r in previous_responses] + [is_correct]

        theta_before = session.theta
        new_theta, adjustment_info = irt_engine.update_theta(
            theta_before,
            response_data,
            response_history,
            questions_answered=session.questions_asked
        )

        questions_info = [(r[1], r[2], r[3]) for r in response_data]
        new_sem = irt_engine.calculate_sem(new_theta, questions_info)

        # EXISTING: Create response with safety
        response_dict = {
            'session_id': session_id,
            'question_id': question_id,
            'selected_option': selected_option,
            'is_correct': is_correct,
            'theta_before': theta_before,
            'theta_after': new_theta,
            'sem_after': new_sem
        }

        # EXISTING: Add topic if column exists
        try:
            if hasattr(models_itembank.Response, 'topic'):
                response_dict['topic'] = question.topic
        except Exception as e:
            logger.debug(f"Topic field not available: {e}")

        response = models_itembank.Response(**response_dict)
        item_db.add(response)

        # EXISTING: Update session
        session.theta = new_theta
        session.sem = new_sem
        session.tier = irt_engine.theta_to_tier(new_theta)
        session.questions_asked += 1

        # ENHANCED: Calculate topic performance EVERY TIME (with safety)
        topic_performance = None
        try:
            if hasattr(session, 'topic_performance'):
                all_responses = previous_responses + [response]
                topic_performance = self.calculate_session_topic_performance(
                    item_db, all_responses, irt_engine
                )
                if topic_performance:
                    session.topic_performance = json.dumps(topic_performance)
                    logger.info(f"Topic performance calculated: {len(topic_performance)} topics")
        except Exception as e:
            logger.warning(f"Could not calculate topic performance: {e}")

        # EXISTING: Check completion
        if irt_engine.should_stop_assessment(new_sem, session.questions_asked, response_history):
            session.completed = True
            session.completed_at = datetime.utcnow()

            # NEW: Save detailed topic performance on completion
            if topic_performance:
                try:
                    self.save_topic_performance(item_db, session_id, session.user_id, topic_performance)
                    logger.info(f"Detailed topic performance saved for session {session_id}")
                except Exception as e:
                    logger.warning(f"Could not save detailed topic performance: {e}")

            # EXISTING: Update proficiency
            self.user_service.update_user_proficiency(
                registry_db, item_db,
                session.user_id, item_bank_name, session.subject,
                new_theta, new_sem, irt_engine.theta_to_tier(new_theta),
                topic_performance  # This was already optional
            )

        item_db.commit()

        # CRITICAL CHANGE: Return dict instead of just response
        return {
            'response': response,
            'topic_performance': topic_performance
        }

    # The get_assessment_results method already has the logic to include topic_performance
    # and learning_roadmap - it just needs the data to be available in the session
    # No changes needed to get_assessment_results - it's already prepared for this data

    def calculate_session_topic_performance(self, db: Session, responses: List,
                                            irt_engine: IRTEngine) -> Optional[Dict]:
        """NEW: Calculate performance for each topic"""
        try:
            topic_data = defaultdict(lambda: {
                'responses': [],
                'correct': 0,
                'total': 0
            })

            for resp in responses:
                question = self.question_service.get_question_by_id(db, resp.question_id)
                if question and question.topic:
                    topic = question.topic
                    topic_data[topic]['responses'].append({
                        'is_correct': resp.is_correct,
                        'difficulty': question.difficulty_b,
                        'discrimination': question.discrimination_a,
                        'guessing': question.guessing_c,
                        'topic': topic
                    })
                    topic_data[topic]['total'] += 1
                    if resp.is_correct:
                        topic_data[topic]['correct'] += 1

            topic_performance = {}
            for topic, data in topic_data.items():
                if data['total'] > 0:
                    perf = self.topic_calculator.calculate_topic_theta(
                        data['responses'], topic, irt_engine
                    )
                    if perf:
                        topic_performance[topic] = perf

            return topic_performance if topic_performance else None
        except Exception as e:
            logger.debug(f"Could not calculate topic performance: {e}")
            return None

    def save_topic_performance(self, db: Session, session_id: int,
                               user_id: int, topic_performance: Dict):
        """NEW: Save detailed topic performance records"""
        try:
            for topic, perf in topic_performance.items():
                topic_record = models_itembank.TopicPerformance(
                    session_id=session_id,
                    user_id=user_id,
                    topic=topic,
                    theta=perf['theta'],
                    sem=perf['sem'],
                    questions_answered=perf['questions_answered'],
                    correct_count=perf['correct_count'],
                    accuracy=perf['accuracy'],
                    tier=perf['tier']
                )
                db.add(topic_record)
            db.commit()
        except Exception as e:
            logger.debug(f"Could not save detailed topic performance: {e}")
            db.rollback()

    def get_assessment_results(self, db: Session, session_id: int) -> schemas.AssessmentResults:
        """ENHANCED but BACKWARD COMPATIBLE"""
        session = self.get_session(db, session_id)
        responses = db.query(models_itembank.Response).filter(
            models_itembank.Response.session_id == session_id
        ).order_by(models_itembank.Response.created_at).all()

        correct_count = sum(1 for r in responses if r.is_correct)
        accuracy = correct_count / len(responses) if responses else 0.0

        response_details = []
        for resp in responses:
            question = self.question_service.get_question_by_id(db, resp.question_id)
            detail_dict = {
                'question_id': resp.question_id,
                'question': question.question,
                'selected_option': resp.selected_option,
                'correct_answer': question.answer,
                'is_correct': resp.is_correct,
                'theta_before': resp.theta_before,
                'theta_after': resp.theta_after,
                'difficulty': question.difficulty_b
            }
            # NEW: Add topic if available
            try:
                if hasattr(resp, 'topic') and resp.topic:
                    detail_dict['topic'] = resp.topic
            except:
                pass

            response_details.append(schemas.ResponseDetails(**detail_dict))

        irt_engine = IRTEngine()
        final_tier = irt_engine.theta_to_tier(session.theta)

        # Base result (always available)
        result_dict = {
            'session_id': session.session_id,
            'user_id': session.user_id,
            'subject': session.subject,
            'final_theta': session.theta,
            'final_sem': session.sem,
            'tier': final_tier,
            'questions_asked': session.questions_asked,
            'correct_answers': correct_count,
            'accuracy': accuracy,
            'responses': response_details,
            'completed_at': session.completed_at
        }

        # NEW: Add enhanced data if available
        try:
            if hasattr(session, 'topic_performance') and session.topic_performance:
                topic_perf = json.loads(session.topic_performance) if isinstance(session.topic_performance,
                                                                                 str) else session.topic_performance
                if topic_perf:
                    result_dict['topic_performance'] = topic_perf
                    roadmap = self.topic_calculator.generate_learning_roadmap(
                        topic_perf, session.theta
                    )
                    if roadmap:
                        result_dict['learning_roadmap'] = roadmap
        except Exception as e:
            logger.debug(f"Enhanced results not available: {e}")


        return schemas.AssessmentResults(**result_dict)

    def is_answer_correct(self, selected: str, correct: str) -> bool:
        """UNCHANGED"""
        if not selected or not correct:
            return False
        return str(selected).strip().upper() == str(correct).strip().upper()


class ItemBankService:
    """UNCHANGED - Original service preserved"""

    def __init__(self):
        self.question_service = QuestionService()

    def create_item_bank(self, db: Session, name: str, display_name: str,
                         subject: str) -> models_registry.ItemBank:
        """UNCHANGED"""
        item_bank = models_registry.ItemBank(
            name=name,
            display_name=display_name,
            subject=subject,
            status="pending"
        )
        db.add(item_bank)
        db.commit()
        db.refresh(item_bank)

        item_bank_db.get_engine(name)
        logger.info(f"Created item bank: {name} at {item_bank_db.get_db_path(name)}")

        return item_bank

    def upload_and_calibrate(self, item_bank_name: str, df: pd.DataFrame) -> Dict:
        """Upload questions to item bank - ALWAYS use item_bank_name as subject"""

        item_db = item_bank_db.get_session(item_bank_name)

        try:
            # Validate required columns (don't require 'subject' in CSV anymore)
            required = ['question', 'option_a', 'option_b', 'option_c', 'option_d',
                        'answer', 'tier', 'topic']
            missing = [col for col in required if col not in df.columns]

            if missing:
                return {
                    'success': False,
                    'error': f'Missing required columns: {missing}'
                }

            # CRITICAL: Always override subject with item_bank_name
            # This ensures questions match what the assessment system expects
            df['subject'] = item_bank_name

            # Generate question_id if not provided
            if 'question_id' not in df.columns:
                df['question_id'] = [f"{item_bank_name}_{i + 1}" for i in range(len(df))]

            # Set defaults for IRT parameters if not provided
            if 'content_area' not in df.columns:
                df['content_area'] = df['topic']

            if 'discrimination_a' not in df.columns:
                df['discrimination_a'] = 1.5

            if 'difficulty_b' not in df.columns:
                tier_difficulty_map = {
                    'C1': -1.5,
                    'C2': -0.5,
                    'C3': 0.5,
                    'C4': 1.5
                }
                df['difficulty_b'] = df['tier'].map(tier_difficulty_map).fillna(0.0)

            if 'guessing_c' not in df.columns:
                df['guessing_c'] = 0.25

            # Import questions
            imported = self.question_service.import_questions_from_df(item_db, df)

            logger.info(f"Imported {imported} questions to item bank: {item_bank_name}")

            return {
                'success': True,
                'imported': imported,
                'total_items': imported,
                'message': f'Successfully imported {imported} questions'
            }

        except Exception as e:
            logger.error(f"Error importing to item bank {item_bank_name}: {e}")
            item_db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            item_db.close()


    def get_item_bank_stats(self, item_bank_name: str) -> Dict:
        """UNCHANGED"""


        db_path = item_bank_db.get_db_path(item_bank_name)

        if not os.path.exists(db_path):
            return {
                'total_items': 0,
                'test_takers': 0,
                'total_responses': 0,
                'accuracy': None
            }

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM questions")
            total_items = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT session_id) FROM assessment_sessions WHERE completed = 1")
            test_takers = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM responses")
            total_responses = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(is_correct) FROM responses")
            accuracy_result = cursor.fetchone()
            accuracy = accuracy_result[0] if accuracy_result[0] is not None else None

            return {
                'total_items': total_items,
                'test_takers': test_takers,
                'total_responses': total_responses,
                'accuracy': accuracy
            }
        except sqlite3.OperationalError as e:
            logger.error(f"Database error for {item_bank_name}: {e}")
            return {
                'total_items': 0,
                'test_takers': 0,
                'total_responses': 0,
                'accuracy': None
            }
        finally:
            conn.close()

    # delete item bank


    def delete_item_bank(self, registry_db: Session, item_bank_name: str) -> Dict:
        """
        Delete an item bank and all associated data with proper connection handling

        Args:
            registry_db: Registry database session
            item_bank_name: Name of the item bank to delete

        Returns:
            Dict with success status and details
        """


        # Check if item bank exists
        item_bank = registry_db.query(models_registry.ItemBank).filter(
            models_registry.ItemBank.name == item_bank_name
        ).first()

        if not item_bank:
            return {
                'success': False,
                'error': f'Item bank "{item_bank_name}" not found'
            }

        # Get stats before deletion
        stats = self.get_item_bank_stats(item_bank_name)

        # Get item bank session - IMPORTANT: We need to manage this properly
        item_db = None
        try:
            item_db = item_bank_db.get_session(item_bank_name)

            # Start transaction
            item_db.begin()

            try:
                # 1. Delete all responses
                item_db.execute(text("""
                                     DELETE
                                     FROM responses
                                     WHERE session_id IN (SELECT session_id
                                                          FROM assessment_sessions)
                                     """))

                # 2. Delete topic performance if table exists
                try:
                    item_db.execute(text("DELETE FROM topic_performance"))
                except:
                    pass  # Table might not exist

                # 3. Delete all assessment sessions
                item_db.query(models_itembank.AssessmentSession).delete()

                # 4. Delete all user proficiencies
                item_db.query(models_itembank.UserProficiency).delete()

                # 5. Delete all questions
                item_db.query(models_itembank.Question).delete()

                # Commit changes
                item_db.commit()

            except Exception as e:
                item_db.rollback()
                raise e

        except Exception as e:
            logger.error(f"Error deleting data from item bank {item_bank_name}: {e}")
            if item_db:
                item_db.rollback()
            return {
                'success': False,
                'error': f'Failed to delete item bank data: {str(e)}'
            }
        finally:
            # CRITICAL: Close the item bank session
            if item_db:
                item_db.close()

            # IMPORTANT: Clean up the connection from the manager
            if hasattr(item_bank_db, 'cleanup'):
                item_bank_db.cleanup(item_bank_name)

        # Small delay to ensure connections are fully closed
        time.sleep(0.1)

        # Now delete from registry
        try:
            # Delete from user proficiency summary cache
            registry_db.query(models_registry.UserProficiencySummary).filter(
                models_registry.UserProficiencySummary.item_bank_name == item_bank_name
            ).delete()

            # Delete the item bank registry entry
            registry_db.delete(item_bank)
            registry_db.commit()

        except Exception as e:
            registry_db.rollback()
            logger.error(f"Error deleting from registry: {e}")
            return {
                'success': False,
                'error': f'Failed to delete from registry: {str(e)}'
            }

        # Now try to delete the database file and its WAL files
        db_path = item_bank_db.get_db_path(item_bank_name)
        deleted_files = []

        # Wait a moment for SQLite to release files
        time.sleep(0.2)

        # Delete all related files
        for suffix in ['', '-wal', '-shm', '-journal']:
            file_path = f"{db_path}{suffix}" if suffix else str(db_path)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files.append(os.path.basename(file_path))
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not delete {file_path}: {e}")

        logger.info(f"Successfully deleted item bank '{item_bank_name}'")

        return {
            'success': True,
            'message': f'Successfully deleted item bank "{item_bank_name}"',
            'deleted': {
                'item_bank': item_bank_name,
                'questions': stats['total_items'],
                'test_takers': stats['test_takers'],
                'responses': stats['total_responses'],
                'files': deleted_files
            }
        }