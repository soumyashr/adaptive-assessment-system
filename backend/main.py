from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import pandas as pd
import io, os
import logging
import subprocess
import sys
from sqlalchemy import and_


# Registry DB
from backend.scripts.database import get_db, engine
# Item bank DB manager
from scripts.db_manager import item_bank_db

# For registry operations
import models_registry as models
# When querying item banks
import models_itembank

import schemas
from irt_engine import IRTEngine
from services import UserService, QuestionService, AssessmentService, ItemBankService
from config import get_config

# Get configuration
config = get_config()
config.validate_config()

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOGGING_CONFIG["level"]),
    format=config.LOGGING_CONFIG["format"],
    handlers=[
        logging.FileHandler(config.LOGGING_CONFIG["log_file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=config.API_CONFIG["title"], 
    version=config.API_CONFIG["version"]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.API_CONFIG["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
user_service = UserService()
question_service = QuestionService()
assessment_service = AssessmentService()
irt_engine = IRTEngine()

def get_item_bank_session(item_bank_name: str):
    """Get database session for an item bank"""
    session = item_bank_db.get_session(item_bank_name)
    try:
        yield session
    finally:
        session.close()


@app.post("/api/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user or get existing user"""
    return user_service.get_or_create_user(db, user.username, user.initial_competence_level)

@app.get("/api/users/{username}", response_model=schemas.User)
def get_user(username: str, db: Session = Depends(get_db)):
    """Get user by username"""
    user = user_service.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/questions/upload")
def upload_questions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload questions from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Read CSV content
    content = file.file.read()
    df = pd.read_csv(io.StringIO(content.decode('utf-8')))

    # Validate required columns
    required_columns = ['subject', 'question_id', 'question', 'option_a', 'option_b', 
                       'option_c', 'option_d', 'answer', 'topic', 'tier', 
                       'discrimination_a', 'difficulty_b', 'guessing_c']

    if not all(col in df.columns for col in required_columns):
        raise HTTPException(status_code=400, detail="CSV missing required columns")

    # Import questions
    imported_count = question_service.import_questions_from_df(db, df)
    return {"message": f"Successfully imported {imported_count} questions"}


@app.post("/api/assessments/start", response_model=schemas.AssessmentSession)
def start_assessment(
        assessment_start: schemas.AssessmentStart,
        db: Session = Depends(get_db)
):
    """Start a new assessment session in an item bank"""
    user = user_service.get_user_by_username(db, assessment_start.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    item_bank_name = assessment_start.subject

    item_bank = db.query(models.ItemBank).filter(
        models.ItemBank.name == item_bank_name
    ).first()
    if not item_bank:
        available = [b.name for b in db.query(models.ItemBank).all()]
        raise HTTPException(
            status_code=404,
            detail=f"Item bank '{item_bank_name}' not found. Available: {available}"
        )

    item_db = item_bank_db.get_session(item_bank_name)

    try:
        session = assessment_service.start_assessment(
            item_db=item_db,
            registry_db=db,
            user_id=user.id,
            subject=assessment_start.subject,
            item_bank_name=item_bank_name  # ← Make sure this is passed
        )

        first_question = assessment_service.get_next_question(
            item_db, session.session_id, irt_engine
        )

        if not first_question:
            raise HTTPException(
                status_code=404,
                detail=f"No questions available in item bank '{item_bank_name}'"
            )

        return {
            "session_id": session.session_id,
            "current_question": first_question,
            "theta": session.theta,
            "sem": session.sem,
            "questions_asked": session.questions_asked
        }
    finally:
        item_db.close()


@app.post("/api/assessments/{session_id}/answer", response_model=schemas.AssessmentSession)
def submit_answer(
        session_id: int,
        answer: schemas.AnswerSubmission,
        item_bank_name: str,
        db: Session = Depends(get_db)
):
    """Submit an answer and get next question"""

    logger.info(f"=== SUBMIT ANSWER DEBUG ===")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Question ID: {answer.question_id}")
    logger.info(f"Selected Option: {answer.selected_option}")
    logger.info(f"Item Bank: {item_bank_name}")

    # Verify item bank exists
    item_bank = db.query(models.ItemBank).filter(
        models.ItemBank.name == item_bank_name
    ).first()
    if not item_bank:
        raise HTTPException(status_code=404, detail="Item bank not found")

    # Get item bank database
    item_db = item_bank_db.get_session(item_bank_name)

    try:
        # Record response in item bank DB
        recorded_response = assessment_service.record_response(
            item_db=item_db,
            registry_db=db,
            session_id=session_id,
            question_id=answer.question_id,
            selected_option=answer.selected_option,
            item_bank_name=item_bank_name,
            irt_engine=irt_engine
        )

        if not recorded_response:
            raise HTTPException(status_code=400, detail="Failed to record response")

        # Get updated session
        session = assessment_service.get_session(item_db, session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Check if assessment is complete
        if session.completed:
            response_data = {
                "session_id": session.session_id,
                "current_question": None,
                "theta": session.theta,
                "sem": session.sem,
                "questions_asked": session.questions_asked,
                "completed": True,
                "last_response_correct": recorded_response.is_correct
            }
            logger.info(f"Assessment {session_id} completed")
            return response_data

        # Get next question
        next_question = assessment_service.get_next_question(
            item_db, session_id, irt_engine
        )

        return {
            "session_id": session.session_id,
            "current_question": next_question,
            "theta": session.theta,
            "sem": session.sem,
            "questions_asked": session.questions_asked,
            "completed": session.completed,
            "last_response_correct": recorded_response.is_correct
        }
    except Exception as e:
        logger.error(f"Error in submit_answer: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    finally:
        item_db.close()

@app.get("/api/assessments/{session_id}/results", response_model=schemas.AssessmentResults)
def get_assessment_results(
        session_id: int,
        item_bank_name: str,  # NEW: Need to know which item bank
        db: Session = Depends(get_db)
):
    """Get assessment results"""
    item_db = item_bank_db.get_session(item_bank_name)

    try:
        return assessment_service.get_assessment_results(item_db, session_id)
    finally:
        item_db.close()



@app.get("/api/users/{username}/proficiency")
def get_user_proficiency(username: str, db: Session = Depends(get_db)):
    """Get user's proficiency across all item banks (from cache)"""
    # Get user from registry
    user = user_service.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Query cached proficiencies from registry (FAST - single query)
    proficiencies = db.query(models.UserProficiencySummary).filter(
        models.UserProficiencySummary.user_id == user.id
    ).all()

    proficiency_list = []
    for prof in proficiencies:
        proficiency_list.append({
            "item_bank": prof.item_bank_name,
            "subject": prof.subject,
            "theta": prof.theta,
            "sem": prof.sem,
            "tier": prof.tier,
            "assessments_taken": prof.assessments_taken,
            "last_updated": prof.last_updated
        })

    return {
        "username": user.username,
        "proficiencies": proficiency_list
    }


# File upload
item_bank_service = ItemBankService()


@app.post("/api/item-banks/create")
async def create_item_bank(
        name: str,
        display_name: str,
        subject: str,
        db: Session = Depends(get_db)
):
    """Create a new item bank or return existing"""
    try:
        # Check if already exists
        existing = db.query(models.ItemBank).filter(
            models.ItemBank.name == name
        ).first()

        if existing:
            return {
                "success": True,
                "message": "Item bank already exists",
                "item_bank": {
                    "name": existing.name,
                    "display_name": existing.display_name,
                    "subject": existing.subject,
                    "status": existing.status
                }
            }

        # Create new
        item_bank = item_bank_service.create_item_bank(
            db, name, display_name, subject
        )
        return {
            "success": True,
            "message": "Item bank created",
            "item_bank": {
                "name": item_bank.name,
                "display_name": item_bank.display_name,
                "subject": item_bank.subject,
                "status": item_bank.status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/item-banks/{item_bank_name}/upload")
async def upload_to_item_bank(
        item_bank_name: str,
        file: UploadFile = File(...)
):
    """Upload questions CSV to item bank"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")

    content = await file.read()
    df = pd.read_csv(io.StringIO(content.decode('utf-8')))

    result = item_bank_service.upload_and_calibrate(item_bank_name, df)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return result


@app.get("/api/item-banks")
async def list_item_banks(db: Session = Depends(get_db)):
    """List all item banks"""
    banks = db.query(models.ItemBank).all()

    result = []
    for bank in banks:
        stats = item_bank_service.get_item_bank_stats(bank.name)
        result.append({
            "name": bank.name,
            "display_name": bank.display_name,
            "subject": bank.subject,
            "status": bank.status,
            "irt_model": bank.irt_model,
            "total_items": stats['total_items'],
            "test_takers": stats['test_takers'],
            "accuracy": stats['accuracy'],
            "total_responses": stats['total_responses']
        })

    return result


@app.post("/api/item-banks/{item_bank_name}/calibrate")
async def calibrate_item_bank(
        item_bank_name: str,
        n_examinees: int = 200,
        questions_per: int = 15,
        db: Session = Depends(get_db)
):
    """Run simulation and recalibration on item bank"""
    # Check item bank exists
    item_bank = db.query(models.ItemBank).filter(
        models.ItemBank.name == item_bank_name
    ).first()

    if not item_bank:
        raise HTTPException(status_code=404, detail="Item bank not found")

    db_path = item_bank_db.get_db_path(item_bank_name)

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Item bank database not found")

    # Get absolute paths
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(backend_dir, 'scripts')
    simulate_script = os.path.join(scripts_dir, 'simulate_test_takers.py')
    recalibrate_script = os.path.join(scripts_dir, 'recalibrate_question_bank.py')
    report_path = os.path.join(backend_dir, 'data', f'{item_bank_name}_calibration_report.txt')

    try:
        logger.info(f"Starting calibration for {item_bank_name}...")

        # Run simulation
        logger.info(f"Running simulation: {simulate_script}")
        sim_result = subprocess.run([
            sys.executable,
            simulate_script,  # ← Use absolute path
            "--db", db_path,
            "--subject", item_bank_name,
            "-n", str(n_examinees),
            "--questions-per-examinee", str(questions_per)
        ], capture_output=True, text=True, check=True, cwd=backend_dir)  # ← Set working directory

        logger.info(f"Simulation output: {sim_result.stdout}")

        # Run calibration
        logger.info(f"Running recalibration: {recalibrate_script}")
        calib_result = subprocess.run([
            sys.executable,
            recalibrate_script,  # ← Use absolute path
            "--db", db_path,
            "--subject", item_bank_name,
            "--min-responses", "30",
            "--report", report_path
        ], capture_output=True, text=True, check=True, cwd=backend_dir)  # ← Set working directory

        logger.info(f"Calibration output: {calib_result.stdout}")

        # Update item bank status
        item_bank.status = "calibrated"
        item_bank.last_calibrated = datetime.utcnow()

        # Update stats
        stats = item_bank_service.get_item_bank_stats(item_bank_name)
        item_bank.total_items = stats['total_items']
        item_bank.test_takers = stats['test_takers']
        item_bank.accuracy = stats['accuracy']

        db.commit()

        return {
            "success": True,
            "message": f"Calibrated {item_bank_name} with {n_examinees} simulated test-takers",
            "simulation_output": sim_result.stdout,
            "calibration_output": calib_result.stdout,
            "stats": stats
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Calibration failed: {e.stderr}")
        raise HTTPException(
            status_code=500,
            detail=f"Calibration failed: {e.stderr}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Calibration error: {str(e)}"
        )


@app.get("/api/sessions")
def get_all_sessions(db: Session = Depends(get_db)):
    """Get all assessment sessions across all item banks"""
    sessions_list = []

    # Get all item banks
    item_banks = db.query(models.ItemBank).all()

    for item_bank in item_banks:
        item_db = item_bank_db.get_session(item_bank.name)
        try:
            # Get sessions from this item bank
            sessions = item_db.query(models_itembank.AssessmentSession).all()

            for session in sessions:
                # Get user info from registry
                user = db.query(models.User).filter(
                    models.User.id == session.user_id
                ).first()

                # Calculate accuracy
                responses = item_db.query(models_itembank.Response).filter(
                    models_itembank.Response.session_id == session.session_id
                ).all()

                correct_count = sum(1 for r in responses if r.is_correct)
                accuracy = correct_count / len(responses) if responses else 0

                sessions_list.append({
                    "session_id": session.session_id,
                    "username": user.username if user else "Unknown",
                    "item_bank": item_bank.name,
                    "status": "Completed" if session.completed else "Active",
                    "theta": session.theta,
                    "questions_asked": session.questions_asked,
                    "accuracy": accuracy,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None
                })
        finally:
            item_db.close()

    # Sort by most recent first
    sessions_list.sort(key=lambda x: x['started_at'] if x['started_at'] else '', reverse=True)

    return sessions_list

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.API_CONFIG["host"],
        port=config.API_CONFIG["port"]
    )