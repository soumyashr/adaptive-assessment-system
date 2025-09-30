from sqlalchemy.orm import Session
from sqlalchemy import and_, not_
from typing import List, Optional, Dict
import pandas as pd
from datetime import datetime
import logging

import models
import schemas
from irt_engine import IRTEngine


logger = logging.getLogger(__name__)

class UserService:
    def get_or_create_user(self, db: Session, username: str, competence_level: str = "C1") -> models.User:
        """Get existing user or create new one"""
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            user = models.User(username=username, competence_level=competence_level)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def get_user_by_username(self, db: Session, username: str) -> Optional[models.User]:
        """Get user by username"""
        return db.query(models.User).filter(models.User.username == username).first()

    def get_user_proficiency(self, db: Session, user_id: int) -> schemas.UserProficiency:
        """Get user's proficiency across all subjects"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        proficiencies = db.query(models.UserProficiency).filter(
            models.UserProficiency.user_id == user_id
        ).all()

        proficiency_list = []
        for prof in proficiencies:
            proficiency_list.append(schemas.UserProficiencySubject(
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

    def update_user_proficiency(self, db: Session, user_id: int, subject: str, 
                               theta: float, sem: float, tier: str):
        """Update or create user proficiency for a subject"""
        proficiency = db.query(models.UserProficiency).filter(
            and_(
                models.UserProficiency.user_id == user_id,
                models.UserProficiency.subject == subject
            )
        ).first()

        if proficiency:
            proficiency.theta = theta
            proficiency.sem = sem
            proficiency.tier = tier
            proficiency.assessments_taken += 1
        else:
            proficiency = models.UserProficiency(
                user_id=user_id,
                subject=subject,
                theta=theta,
                sem=sem,
                tier=tier,
                assessments_taken=1
            )
            db.add(proficiency)

        try:
            db.commit()
            logger.info("Database committed successfully")
        except Exception as e:
            logger.error(f"Database commit failed: {e}")
            db.rollback()
            raise

class QuestionService:
    def import_questions_from_df(self, db: Session, df: pd.DataFrame) -> int:
        """Import questions from pandas DataFrame"""
        imported_count = 0

        for _, row in df.iterrows():
            # Check if question already exists
            existing = db.query(models.Question).filter(
                models.Question.question_id == row['question_id']
            ).first()

            if not existing:
                question = models.Question(
                    subject=row['subject'],
                    question_id=row['question_id'],
                    question=row['question'],
                    option_a=row['option_a'],
                    option_b=row['option_b'],
                    option_c=row['option_c'],
                    option_d=row['option_d'],
                    answer=row['answer'],
                    topic=row['topic'],
                    tier=row['tier'],
                    discrimination_a=float(row['discrimination_a']),
                    difficulty_b=float(row['difficulty_b']),
                    guessing_c=float(row['guessing_c']),
                    selected_option_text=row.get('selected_option_text', '')
                )
                db.add(question)
                imported_count += 1

        db.commit()
        return imported_count

    def get_available_questions(self, db: Session, session_id: int, subject: str) -> List[Dict]:
        """Get available questions for a session (not yet asked)"""
        asked_question_ids = db.query(models.Response.question_id).filter(
            models.Response.session_id == session_id
        ).subquery()

        questions = db.query(models.Question).filter(
            and_(
                models.Question.subject == subject,
                not_(models.Question.id.in_(asked_question_ids))
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
                'tier': q.tier,
                'discrimination_a': q.discrimination_a,
                'difficulty_b': q.difficulty_b,
                'guessing_c': q.guessing_c
            }
            for q in questions
        ]

    def get_question_by_id(self, db: Session, question_id: int) -> Optional[models.Question]:
        """Get question by ID"""
        return db.query(models.Question).filter(models.Question.id == question_id).first()

class AssessmentService:
    def __init__(self):
        self.user_service = UserService()
        self.question_service = QuestionService()

    def start_assessment(self, db: Session, user_id: int, subject: str) -> models.AssessmentSession:
        """Start a new assessment session"""
        # Get user's previous proficiency for this subject
        user_proficiency = db.query(models.UserProficiency).filter(
            and_(
                models.UserProficiency.user_id == user_id,
                models.UserProficiency.subject == subject
            )
        ).first()

        # Set initial theta based on proficiency or competence level
        if user_proficiency:
            initial_theta = user_proficiency.theta
        else:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            irt_engine = IRTEngine()
            initial_theta = irt_engine.get_initial_theta(user.competence_level)

        session = models.AssessmentSession(
            user_id=user_id,
            subject=subject,
            initial_theta=initial_theta,
            current_theta=initial_theta,
            current_sem=1.0
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        return session

    def get_session(self, db: Session, session_id: int) -> Optional[models.AssessmentSession]:
        """Get assessment session by ID"""
        return db.query(models.AssessmentSession).filter(
            models.AssessmentSession.id == session_id
        ).first()

    def get_next_question(self, db: Session, session_id: int, 
                         irt_engine: IRTEngine) -> Optional[schemas.QuestionResponse]:
        """Get next question for assessment"""
        session = self.get_session(db, session_id)
        if not session or session.is_completed:
            return None

        # Get response history
        responses = db.query(models.Response).filter(
            models.Response.session_id == session_id
        ).order_by(models.Response.created_at).all()

        response_history = [r.is_correct for r in responses]

        # Get available questions
        available_questions = self.question_service.get_available_questions(
            db, session_id, session.subject
        )

        if not available_questions:
            # No more questions available, complete assessment
            session.is_completed = True
            session.completed_at = datetime.utcnow()
            db.commit()
            return None

        # Select next question using IRT engine
        next_question_data = irt_engine.select_next_question(
            session.current_theta, available_questions, response_history
        )

        if not next_question_data:
            return None
        print(f"DEBUG: Rendered Question: {next_question_data['question']}")
        print(f"DEBUG: Rendered Question difficulty_b: {next_question_data['difficulty_b']}")
        return schemas.QuestionResponse(
            id=next_question_data['id'],
            question=next_question_data['question'],
            option_a=next_question_data['option_a'],
            option_b=next_question_data['option_b'],
            option_c=next_question_data['option_c'],
            option_d=next_question_data['option_d'],
            topic=next_question_data['topic'],
            tier=next_question_data['tier'],
            difficulty_b=next_question_data['difficulty_b'],  # ADD THIS
            discrimination_a=next_question_data['discrimination_a'],  # ADD THIS
            guessing_c=next_question_data['guessing_c']  # ADD THIS
        )

    def record_response(self, db: Session, session_id: int, question_id: int,
                        selected_option: str, irt_engine: IRTEngine):
        """Record a response and update theta with enhanced consecutive response handling"""
        print("-" * 50)
        session = self.get_session(db, session_id)
        question = self.question_service.get_question_by_id(db, question_id)

        if not session or not question:
            return

        # DEBUG: Print comparison details
        print("\n\n")
        print("-"*50)
        print(f"DEBUG: services.record_response():Question Id: {question.question_id}")
        print(f"DEBUG: Question: {question.question}")
        print(f"DEBUG: Selected option: '{selected_option}' (type: {type(selected_option)})")
        print(f"DEBUG: Correct answer: '{question.answer}' (type: {type(question.answer)})")
        print(f"DEBUG: Selected upper: '{selected_option.upper()}'")
        print(f"DEBUG: Answer upper: '{question.answer.upper()}'")

        # Check if answer is correct
        # is_correct = selected_option.upper() == question.answer.upper()
        is_correct = self.is_answer_correct(selected_option, question.answer)

        print(f"DEBUG: Is correct: {is_correct}")


        # Get all previous responses for theta calculation
        previous_responses = db.query(models.Response).filter(
            models.Response.session_id == session_id
        ).order_by(models.Response.created_at).all()

        # Prepare response data for theta update
        response_data = [
            (r.is_correct,
             self.question_service.get_question_by_id(db, r.question_id).difficulty_b,
             self.question_service.get_question_by_id(db, r.question_id).discrimination_a,
             self.question_service.get_question_by_id(db, r.question_id).guessing_c)
            for r in previous_responses
        ]

        # Add current response
        response_data.append((
            is_correct,
            question.difficulty_b,
            question.discrimination_a,
            question.guessing_c
        ))

        # Create response history for consecutive detection
        response_history = [r.is_correct for r in previous_responses] + [is_correct]

        # Update theta with enhanced logic
        theta_before = session.current_theta
        print(f"DEBUG: AssessmentService.record_response(): theta_before: {theta_before}")
        new_theta, adjustment_info = irt_engine.update_theta(theta_before, response_data, response_history)
        print(f"DEBUG: AssessmentService.record_response(): new_theta: {new_theta}")

        # Log theta adjustment information
        if adjustment_info.get('consecutive_info', {}).get('apply_jump'):
            consecutive_info = adjustment_info['consecutive_info']
            logger.info(f"Session {session_id}: Applied theta jump for {consecutive_info['consecutive_count']} "
                        f"consecutive {consecutive_info['response_type']} responses. "
                        f"Theta change: {adjustment_info['theta_change']:.3f}")
        else:
            logger.debug(f"Session {session_id}: Regular theta update. "
                         f"Theta change: {adjustment_info['theta_change']:.3f}")

        # Calculate SEM
        questions_info = []
        for resp in previous_responses:
            q = self.question_service.get_question_by_id(db, resp.question_id)
            questions_info.append((q.difficulty_b, q.discrimination_a, q.guessing_c))

        # Add current question
        questions_info.append((question.difficulty_b, question.discrimination_a, question.guessing_c))

        new_sem = irt_engine.calculate_sem(new_theta, questions_info)

        # Record response
        response = models.Response(
            session_id=session_id,
            question_id=question_id,
            selected_option=selected_option,
            is_correct=is_correct,
            theta_before=theta_before,
            theta_after=new_theta,
            sem_after=new_sem
        )

        db.add(response)

        # Update session
        session.current_theta = new_theta
        session.current_sem = new_sem
        session.questions_asked += 1

        # Check if assessment should stop (with enhanced consecutive logic)
        if irt_engine.should_stop_assessment(new_sem, session.questions_asked, response_history):
            session.is_completed = True
            session.completed_at = datetime.utcnow()

            # Update user proficiency
            new_tier = irt_engine.theta_to_tier(new_theta)
            self.user_service.update_user_proficiency(
                db, session.user_id, session.subject, new_theta, new_sem, new_tier
            )

            # Log final assessment metrics
            metrics = irt_engine.calculate_assessment_metrics(response_data, new_theta, response_history)
            logger.info(f"Assessment {session_id} completed. Final metrics: {metrics}")

        print("-" * 50)
        db.commit()
        return response


    def get_assessment_results(self, db: Session, session_id: int) -> schemas.AssessmentResults:
        """Get assessment results"""
        session = self.get_session(db, session_id)
        responses = db.query(models.Response).filter(
            models.Response.session_id == session_id
        ).order_by(models.Response.created_at).all()

        # Calculate metrics
        correct_count = sum(1 for r in responses if r.is_correct)
        accuracy = correct_count / len(responses) if responses else 0.0

        # Prepare response details
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
        final_tier = irt_engine.theta_to_tier(session.current_theta)

        return schemas.AssessmentResults(
            session_id=session.id,
            user_id=session.user_id,
            subject=session.subject,
            final_theta=session.current_theta,
            final_sem=session.current_sem,
            tier=final_tier,
            questions_asked=session.questions_asked,
            correct_answers=correct_count,
            accuracy=accuracy,
            responses=response_details,
            completed_at=session.completed_at
        )


    def is_answer_correct(self,selected: str, correct: str) -> bool:
        """Robust answer comparison"""
        if not selected or not correct:
            return False

        # Clean both strings
        selected_clean = str(selected).strip().upper()
        correct_clean = str(correct).strip().upper()

        print(f"Comparing: '{selected_clean}' == '{correct_clean}'")

        return selected_clean == correct_clean


