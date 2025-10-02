# backend/services.py

from sqlalchemy.orm import Session
from sqlalchemy import and_, not_
from typing import List, Optional, Dict
import pandas as pd
from datetime import datetime
import logging
import sys
import os
from sqlalchemy import and_


# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from db_manager import item_bank_db

# Import both model files
import models_registry  # For User, ItemBank operations
import models_itembank  # For Question, Session, Response operations
from irt_engine import IRTEngine
import schemas

logger = logging.getLogger(__name__)


class UserService:
    """Manages users in registry database"""

    def get_or_create_user(self, db: Session, username: str,
                           initial_competence_level: str = "beginner") -> models_registry.User:
        """Get existing user or create new one in registry"""
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
        """Get user by username from registry"""
        return db.query(models_registry.User).filter(
            models_registry.User.username == username
        ).first()

    def get_user_proficiency(self, db: Session, user_id: int) -> schemas.UserProficiency:
        """Get user's proficiency across all item banks"""
        user = db.query(models_registry.User).filter(
            models_registry.User.id == user_id
        ).first()

        # Get cached proficiencies from registry
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
                                theta: float, sem: float, tier: str):
        """Update proficiency in both item bank DB and registry cache"""

        # 1. Update in item bank database
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
        else:
            proficiency = models_itembank.UserProficiency(
                user_id=user_id,
                subject=subject,
                theta=theta,
                sem=sem,
                tier=tier,
                assessments_taken=1
            )
            item_db.add(proficiency)

        item_db.commit()

        # 2. Update cache in registry database
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
        logger.info(f"Updated proficiency cache for user {user_id} in {item_bank_name}")


class QuestionService:
    """Manages questions in item bank databases"""

    def import_questions_from_df(self, db: Session, df: pd.DataFrame) -> int:
        """Import questions from pandas DataFrame into item bank DB"""
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
        """Get available questions for a session (not yet asked)"""
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
        """Get question by ID from item bank DB"""
        return db.query(models_itembank.Question).filter(
            models_itembank.Question.id == question_id
        ).first()


class AssessmentService:
    """Manages assessments in item bank databases"""

    def __init__(self):
        self.user_service = UserService()
        self.question_service = QuestionService()

    def start_assessment(self, item_db: Session, registry_db: Session,
                         user_id: int, subject: str, item_bank_name: str) -> models_itembank.AssessmentSession:
        """Start a new assessment session in item bank DB"""
        logger.info(f"Start assessment for user {user_id} in item bank {item_bank_name}")

        # Check for existing proficiency in item bank
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
            # Get user from registry to check competence level
            user = registry_db.query(models_registry.User).filter(
                models_registry.User.id == user_id
            ).first()
            irt_engine = IRTEngine()
            starting_theta = irt_engine.get_initial_theta(user.initial_competence_level)
            logger.info(f"Using initial competence: {user.initial_competence_level}, theta: {starting_theta:.3f}")

        # Create session in item bank DB
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
        """Get assessment session by ID from item bank DB"""
        return db.query(models_itembank.AssessmentSession).filter(
            models_itembank.AssessmentSession.session_id == session_id
        ).first()

    def get_next_question(self, db: Session, session_id: int,
                          irt_engine: IRTEngine) -> Optional[schemas.QuestionResponse]:
        """Get next question for assessment from item bank DB"""
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

    def record_response(self, item_db: Session, registry_db: Session,
                        session_id: int, question_id: int, selected_option: str,
                        item_bank_name: str, irt_engine: IRTEngine):
        """Record a response and update theta in item bank DB"""
        session = self.get_session(item_db, session_id)
        question = self.question_service.get_question_by_id(item_db, question_id)

        if not session or not question:
            return

        is_correct = self.is_answer_correct(selected_option, question.answer)

        previous_responses = item_db.query(models_itembank.Response).filter(
            models_itembank.Response.session_id == session_id
        ).order_by(models_itembank.Response.created_at).all()

        response_data = [
            (r.is_correct,
             self.question_service.get_question_by_id(item_db, r.question_id).difficulty_b,
             self.question_service.get_question_by_id(item_db, r.question_id).discrimination_a,
             self.question_service.get_question_by_id(item_db, r.question_id).guessing_c)
            for r in previous_responses
        ]

        response_data.append((
            is_correct,
            question.difficulty_b,
            question.discrimination_a,
            question.guessing_c
        ))

        response_history = [r.is_correct for r in previous_responses] + [is_correct]

        theta_before = session.theta
        new_theta, adjustment_info = irt_engine.update_theta(
            theta_before,
            response_data,
            response_history,
            questions_answered=session.questions_asked
        )

        questions_info = []
        for resp in previous_responses:
            q = self.question_service.get_question_by_id(item_db, resp.question_id)
            questions_info.append((q.difficulty_b, q.discrimination_a, q.guessing_c))

        questions_info.append((question.difficulty_b, question.discrimination_a, question.guessing_c))
        new_sem = irt_engine.calculate_sem(new_theta, questions_info)

        # Record response
        response = models_itembank.Response(
            session_id=session_id,
            question_id=question_id,
            selected_option=selected_option,
            is_correct=is_correct,
            theta_before=theta_before,
            theta_after=new_theta,
            sem_after=new_sem
        )

        item_db.add(response)

        # Update session
        session.theta = new_theta
        session.sem = new_sem
        session.tier = irt_engine.theta_to_tier(new_theta)
        session.questions_asked += 1

        # Check if assessment should stop
        if irt_engine.should_stop_assessment(new_sem, session.questions_asked, response_history):
            session.completed = True
            session.completed_at = datetime.utcnow()

            # Update user proficiency in both DBs
            new_tier = irt_engine.theta_to_tier(new_theta)
            self.user_service.update_user_proficiency(
                registry_db, item_db,
                session.user_id, item_bank_name, session.subject,
                new_theta, new_sem, new_tier
            )

        item_db.commit()
        return response

    def get_assessment_results(self, db: Session, session_id: int) -> schemas.AssessmentResults:
        """Get assessment results from item bank DB"""
        session = self.get_session(db, session_id)
        responses = db.query(models_itembank.Response).filter(
            models_itembank.Response.session_id == session_id
        ).order_by(models_itembank.Response.created_at).all()

        correct_count = sum(1 for r in responses if r.is_correct)
        accuracy = correct_count / len(responses) if responses else 0.0

        response_details = []
        for resp in responses:
            question = self.question_service.get_question_by_id(db, resp.question_id)
            response_details.append(schemas.ResponseDetails(
                question_id=resp.question_id,
                question=question.question,
                selected_option=resp.selected_option,
                correct_answer=question.answer,
                is_correct=resp.is_correct,
                theta_before=resp.theta_before,
                theta_after=resp.theta_after
            ))

        irt_engine = IRTEngine()
        final_tier = irt_engine.theta_to_tier(session.theta)

        return schemas.AssessmentResults(
            session_id=session.session_id,
            user_id=session.user_id,
            subject=session.subject,
            final_theta=session.theta,
            final_sem=session.sem,
            tier=final_tier,
            questions_asked=session.questions_asked,
            correct_answers=correct_count,
            accuracy=accuracy,
            responses=response_details,
            completed_at=session.completed_at
        )

    def is_answer_correct(self, selected: str, correct: str) -> bool:
        """Robust answer comparison"""
        if not selected or not correct:
            return False
        return str(selected).strip().upper() == str(correct).strip().upper()


class ItemBankService:
    """Service for managing item banks"""

    def __init__(self):
        self.question_service = QuestionService()

    def create_item_bank(self, db: Session, name: str, display_name: str,
                         subject: str) -> models_registry.ItemBank:
        """Create a new item bank entry in registry and create its database"""
        item_bank = models_registry.ItemBank(
            name=name,
            display_name=display_name,
            subject=subject,
            status="pending"
        )
        db.add(item_bank)
        db.commit()
        db.refresh(item_bank)

        # Create separate database file
        item_bank_db.get_engine(name)
        logger.info(f"Created item bank: {name} at {item_bank_db.get_db_path(name)}")

        return item_bank

    def upload_and_calibrate(self, item_bank_name: str, df: pd.DataFrame) -> Dict:
        """Upload questions CSV to item bank and apply default calibration"""
        item_db = item_bank_db.get_session(item_bank_name)

        try:
            required = ['question', 'option_a', 'option_b', 'option_c', 'option_d',
                        'answer', 'tier', 'topic']
            missing = [col for col in required if col not in df.columns]

            if missing:
                return {
                    'success': False,
                    'error': f'Missing required columns: {missing}'
                }

            if 'subject' not in df.columns:
                df['subject'] = item_bank_name

            if 'question_id' not in df.columns:
                df['question_id'] = [f"{item_bank_name}_{i + 1}" for i in range(len(df))]

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
        """Get statistics for an item bank"""
        import sqlite3

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