# backend/main.py
# UPDATED: XLSX format only - CSV support removed

from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import pandas as pd
import io, os
import logging
import subprocess
import sys
from sqlalchemy import and_
from pathlib import Path

# Registry DB
from scripts.database import get_db, engine
# Item bank DB manager
from scripts.db_manager import item_bank_db

# For registry operations
import models_registry as models
# When querying item banks
import models_itembank

import schemas
from irt_engine import IRTEngine
from services import (
    UserService,
    QuestionService,
    AssessmentService,
    ItemBankService,
    SessionManagementService,
    PDFExportService
)
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
    version=config.API_CONFIG["version"],
    description="IRT Assessment API - XLSX format only for optimal mathematical symbol preservation"
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
session_management_service = SessionManagementService()
pdf_export_service = PDFExportService()
irt_engine = IRTEngine()


def get_item_bank_session(item_bank_name: str):
    """Get database session for an item bank"""
    session = item_bank_db.get_session(item_bank_name)
    try:
        yield session
    finally:
        session.close()


# ========== USER ENDPOINTS ==========

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


@app.get("/api/users/{username}/proficiency")
def get_user_proficiency(username: str, db: Session = Depends(get_db)):
    """Get user's proficiency across all item banks"""
    user = user_service.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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


# ========== QUESTION UPLOAD - XLSX ONLY ==========

@app.post("/api/questions/upload")
async def upload_questions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload questions from Excel file (XLSX/XLS only)

    Required format:
    - Excel file (.xlsx or .xls)
    - Contains columns: question, option_a-d, answer, topic, tier
    - Optional: subject, question_id, discrimination_a, difficulty_b, guessing_c

    Mathematical symbols are perfectly preserved in Excel format.
    """
    filename = file.filename.lower()

    # Check file extension - XLSX/XLS only
    if not (filename.endswith('.xlsx') or filename.endswith('.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be Excel format (.xlsx or .xls). Excel format is required for proper mathematical symbol preservation."
        )

    content = await file.read()

    try:
        # Read Excel file
        excel_file = pd.ExcelFile(io.BytesIO(content))

        # Find the data sheet (skip instruction sheets if present)
        data_sheet = None
        for sheet_name in excel_file.sheet_names:
            if 'instruction' not in sheet_name.lower() and 'template' not in sheet_name.lower():
                data_sheet = sheet_name
                break

        if data_sheet is None and excel_file.sheet_names:
            data_sheet = 0  # Use first sheet if no data sheet found

        df = pd.read_excel(io.BytesIO(content), sheet_name=data_sheet)
        logger.info(
            f"Read Excel file with {len(df)} rows from sheet: {excel_file.sheet_names[data_sheet] if isinstance(data_sheet, int) else data_sheet}")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read Excel file: {str(e)}")

    # Validate columns
    required_columns = ['subject', 'question_id', 'question', 'option_a', 'option_b',
                        'option_c', 'option_d', 'answer', 'topic', 'tier',
                        'discrimination_a', 'difficulty_b', 'guessing_c']

    # Normalize column names
    df.columns = df.columns.str.lower().str.strip()

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        # Check if it's a simplified format (missing IRT parameters)
        basic_required = ['question', 'option_a', 'option_b', 'option_c', 'option_d',
                          'answer', 'topic', 'tier']
        basic_missing = [col for col in basic_required if col not in df.columns]

        if basic_missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(basic_missing)}"
            )

        # Auto-generate missing columns
        logger.info("Auto-generating missing IRT parameters and metadata")
        df = question_service.auto_complete_dataframe(df)

    imported_count = question_service.import_questions_from_df(db, df)

    return {
        "message": f"Successfully imported {imported_count} questions from Excel file",
        "format": "Excel",
        "sheet_used": excel_file.sheet_names[data_sheet] if isinstance(data_sheet, int) else data_sheet,
        "total_questions": len(df)
    }


# ========== ITEM BANK MANAGEMENT ==========

item_bank_service = ItemBankService()


@app.post("/api/item-banks/create")
async def create_item_bank(
        name: str,
        display_name: str,
        subject: str,
        db: Session = Depends(get_db)
):
    """Create a new item bank"""
    try:
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
    """
    Upload questions to item bank - Excel format only

    Required format:
    - Excel file (.xlsx or .xls)
    - Required columns: question, option_a-d, answer, tier, topic
    - Optional: subject, question_id, discrimination_a, difficulty_b, guessing_c

    IRT parameters will be auto-generated if not provided.
    """
    filename = file.filename.lower()

    if not (filename.endswith('.xlsx') or filename.endswith('.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be Excel format (.xlsx or .xls). This ensures proper preservation of mathematical symbols."
        )

    content = await file.read()

    try:
        # Read Excel file
        excel_file = pd.ExcelFile(io.BytesIO(content))

        # Log available sheets
        if len(excel_file.sheet_names) > 1:
            logger.info(f"Multiple sheets found: {excel_file.sheet_names}")

            # Find data sheet (skip instruction/template sheets)
            data_sheet = None
            for sheet in excel_file.sheet_names:
                if 'instruction' not in sheet.lower() and 'template' not in sheet.lower():
                    data_sheet = sheet
                    break

            if data_sheet is None:
                data_sheet = 0  # Default to first sheet

            logger.info(
                f"Using sheet: {excel_file.sheet_names[data_sheet] if isinstance(data_sheet, int) else data_sheet}")
        else:
            data_sheet = 0

        df = pd.read_excel(io.BytesIO(content), sheet_name=data_sheet)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read Excel file: {str(e)}")

    # Upload and calibrate
    result = item_bank_service.upload_and_calibrate(item_bank_name, df)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    result['file_format'] = 'Excel'
    result['sheets_available'] = excel_file.sheet_names
    return result


@app.get("/api/item-banks")
async def list_item_banks(db: Session = Depends(get_db)):
    """List all item banks with statistics"""
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


@app.delete("/api/item-banks/{item_bank_name}")
async def delete_item_bank(
        item_bank_name: str,
        db: Session = Depends(get_db)
):
    """Delete an item bank and all associated data"""

    # Verify item bank exists in registry
    item_bank = db.query(models.ItemBank).filter(
        models.ItemBank.name == item_bank_name
    ).first()

    if not item_bank:
        raise HTTPException(
            status_code=404,
            detail=f"Item bank '{item_bank_name}' not found"
        )

    # Check for active sessions first
    item_db = None
    try:
        item_db = item_bank_db.get_session(item_bank_name)

        active_sessions = item_db.query(models_itembank.AssessmentSession).filter(
            models_itembank.AssessmentSession.completed == False
        ).count()

        if active_sessions > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete: {active_sessions} active session(s) in progress. Terminate them first."
            )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        # If database doesn't exist or other errors, log but continue
        logger.warning(f"Could not check active sessions for {item_bank_name}: {e}")
    finally:
        if item_db:
            item_db.close()

    # Proceed with deletion
    result = item_bank_service.delete_item_bank(db, item_bank_name)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return result
# ========== TEMPLATE DOWNLOADS ==========

@app.get("/api/templates/download")
async def download_template():
    """
    Download Excel question template

    The template includes:
    - Data entry sheet with validation
    - Instruction sheet with detailed guidelines
    - Examples sheet with sample questions
    - Built-in data validation for answers and tiers
    """
    from scripts.xlsx_templates import TemplateGenerator

    generator = TemplateGenerator()
    buffer = generator.create_xlsx_template()

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=question_template_{datetime.now().strftime('%Y%m%d')}.xlsx"
        }
    )


# ========== ASSESSMENT ENDPOINTS ==========

@app.post("/api/assessments/start", response_model=schemas.AssessmentSession)
def start_assessment(
        assessment_start: schemas.AssessmentStart,
        db: Session = Depends(get_db)
):
    """Start a new assessment session"""
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
            item_bank_name=item_bank_name
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

    # Verify item bank exists
    item_bank = db.query(models.ItemBank).filter(
        models.ItemBank.name == item_bank_name
    ).first()
    if not item_bank:
        raise HTTPException(status_code=404, detail="Item bank not found")

    item_db = item_bank_db.get_session(item_bank_name)

    try:
        recorded_data = assessment_service.record_response(
            item_db=item_db,
            registry_db=db,
            session_id=session_id,
            question_id=answer.question_id,
            selected_option=answer.selected_option,
            item_bank_name=item_bank_name,
            irt_engine=irt_engine
        )

        if not recorded_data:
            raise HTTPException(status_code=400, detail="Failed to record response")

        recorded_response = recorded_data.get('response')
        topic_performance = recorded_data.get('topic_performance')

        session = assessment_service.get_session(item_db, session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.completed:
            response_data = {
                "session_id": session.session_id,
                "current_question": None,
                "theta": session.theta,
                "sem": session.sem,
                "questions_asked": session.questions_asked,
                "completed": True,
                "last_response_correct": recorded_response.is_correct,
                "topic_performance": topic_performance
            }
            return response_data

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
            "last_response_correct": recorded_response.is_correct,
            "topic_performance": topic_performance
        }
    except Exception as e:
        logger.error(f"Error in submit_answer: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    finally:
        item_db.close()


@app.get("/api/assessments/{session_id}/results", response_model=schemas.AssessmentResults)
def get_assessment_results(
        session_id: int,
        item_bank_name: str,
        db: Session = Depends(get_db)
):
    """Get assessment results"""
    item_db = item_bank_db.get_session(item_bank_name)

    try:
        return assessment_service.get_assessment_results(item_db, session_id)
    finally:
        item_db.close()


# ========== SESSION MANAGEMENT ==========

@app.get("/api/sessions")
def get_all_sessions(db: Session = Depends(get_db)):
    """Get all assessment sessions across all item banks"""
    sessions_list = []

    item_banks = db.query(models.ItemBank).all()

    for item_bank in item_banks:
        item_db = item_bank_db.get_session(item_bank.name)
        try:
            sessions = item_db.query(models_itembank.AssessmentSession).all()

            for session in sessions:
                # Check if session already added (in case of duplicate data)
                if not any(s['session_id'] == session.session_id and s['item_bank'] == item_bank.name
                          for s in sessions_list):
                    user = db.query(models.User).filter(
                        models.User.id == session.user_id
                    ).first()

                responses = item_db.query(models_itembank.Response).filter(
                    models_itembank.Response.session_id == session.session_id
                ).all()

                correct_count = sum(1 for r in responses if r.is_correct)
                accuracy = correct_count / len(responses) if responses else 0

                sessions_list.append({
                    "global_id": f"{item_bank.name}-{session.session_id}",  # for global unique id
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

    sessions_list.sort(key=lambda x: x['started_at'] if x['started_at'] else '', reverse=True)

    return sessions_list


@app.post("/api/sessions/{session_id}/terminate")
async def terminate_single_session(
        session_id: int,
        item_bank_name: str,
        db: Session = Depends(get_db)
):
    """Terminate a specific assessment session"""
    item_db = item_bank_db.get_session(item_bank_name)

    try:
        result = session_management_service.terminate_single_session(
            item_db, db, session_id, item_bank_name
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])

        return result

    except Exception as e:
        logger.error(f"Error terminating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        item_db.close()


@app.post("/api/sessions/terminate-all")
async def terminate_all_active_sessions(db: Session = Depends(get_db)):
    """Terminate all active sessions across all item banks"""
    try:
        result = session_management_service.terminate_all_active_sessions(db)

        if not result['success'] and result.get('errors'):
            return {
                **result,
                'status': 'partial_success'
            }

        return result

    except Exception as e:
        logger.error(f"Error terminating all sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/item-banks/{item_bank_name}/sessions/terminate")
async def terminate_item_bank_sessions(
        item_bank_name: str,
        db: Session = Depends(get_db)
):
    """Terminate all active sessions for a specific item bank"""

    # Verify item bank exists
    item_bank = db.query(models.ItemBank).filter(
        models.ItemBank.name == item_bank_name
    ).first()

    if not item_bank:
        raise HTTPException(status_code=404, detail=f"Item bank '{item_bank_name}' not found")

    item_db = item_bank_db.get_session(item_bank_name)

    try:
        result = session_management_service.terminate_item_bank_sessions(
            item_db, db, item_bank_name
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating sessions for {item_bank_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        item_db.close()


# ========== CALIBRATION ==========

@app.post("/api/item-banks/{item_bank_name}/calibrate")
async def calibrate_item_bank(
        item_bank_name: str,
        n_examinees: int = 200,
        questions_per: int = 15,
        db: Session = Depends(get_db)
):
    """Run simulation and recalibration on item bank"""
    item_bank = db.query(models.ItemBank).filter(
        models.ItemBank.name == item_bank_name
    ).first()

    if not item_bank:
        raise HTTPException(status_code=404, detail="Item bank not found")

    db_path = item_bank_db.get_db_path(item_bank_name)

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Item bank database not found")

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(backend_dir, 'scripts')
    simulate_script = os.path.join(scripts_dir, 'simulate_test_takers.py')
    recalibrate_script = os.path.join(scripts_dir, 'recalibrate_question_bank.py')
    report_path = os.path.join(backend_dir, 'data', f'{item_bank_name}_calibration_report.txt')

    try:
        logger.info(f"Starting calibration for {item_bank_name}...")

        # Run simulation
        sim_result = subprocess.run([
            sys.executable,
            simulate_script,
            "--db", db_path,
            "--subject", item_bank_name,
            "-n", str(n_examinees),
            "--questions-per-examinee", str(questions_per)
        ], capture_output=True, text=True, check=True, cwd=backend_dir)

        # Run recalibration
        calib_result = subprocess.run([
            sys.executable,
            recalibrate_script,
            "--db", db_path,
            "--subject", item_bank_name,
            "--min-responses", "30",
            "--report", report_path
        ], capture_output=True, text=True, check=True, cwd=backend_dir)

        item_bank.status = "calibrated"
        item_bank.last_calibrated = datetime.utcnow()

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


# ========== STATISTICS & INFO ==========

@app.get("/api/item-banks/{item_bank_name}/stats")
async def get_item_bank_stats(
        item_bank_name: str,
        db: Session = Depends(get_db)
):
    """Get detailed statistics for an item bank"""

    # Verify item bank exists
    item_bank = db.query(models.ItemBank).filter(
        models.ItemBank.name == item_bank_name
    ).first()

    if not item_bank:
        raise HTTPException(status_code=404, detail="Item bank not found")

    stats = item_bank_service.get_item_bank_stats(item_bank_name)

    # Get additional details
    item_db = item_bank_db.get_session(item_bank_name)
    try:
        # Count active sessions
        active_sessions = item_db.query(models_itembank.AssessmentSession).filter(
            models_itembank.AssessmentSession.completed == False
        ).count()

        # Get topic distribution
        topics = item_db.query(
            models_itembank.Question.topic,
            func.count(models_itembank.Question.id).label('count')
        ).group_by(models_itembank.Question.topic).all()

        stats['active_sessions'] = active_sessions
        stats['topics'] = [{'topic': t.topic, 'count': t.count} for t in topics]
        stats['can_delete'] = active_sessions == 0

    finally:
        item_db.close()

    return stats


# ========== PDF EXPORT ==========
@app.get("/api/sessions/{session_id}/export-pdf")
async def export_session_pdf(
        session_id: int,
        item_bank_name: str,
        db: Session = Depends(get_db)
):
    """
    Export session results as a comprehensive PDF report

    ✅ BACKWARD COMPATIBLE - Same API contract, cleaner implementation
    """
    # Verify item bank exists
    item_bank = db.query(models.ItemBank).filter(
        models.ItemBank.name == item_bank_name
    ).first()

    if not item_bank:
        raise HTTPException(status_code=404, detail=f"Item bank '{item_bank_name}' not found")

    item_db = item_bank_db.get_session(item_bank_name)

    try:
        # ALL business logic moved to service
        pdf_buffer = pdf_export_service.export_complete_session(
            registry_db=db,
            item_db=item_db,
            session_id=session_id,
            item_bank_name=item_bank_name
        )

        # Only HTTP response formatting here
        filename = f"assessment_report_{item_bank_name}_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except ValueError as e:
        # Service raises ValueError for not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error exporting PDF for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
    finally:
        item_db.close()


#====== Below is to test the uniqueness of session IDs across item banks.
#======= Each item bank has its own database, so session ID may exist in multiple item banks.

@app.get("/api/debug/sessions")
def debug_sessions(db: Session = Depends(get_db)):
    """Debug endpoint to see session distribution"""
    debug_info = {}

    item_banks = db.query(models.ItemBank).all()

    for item_bank in item_banks:
        item_db = item_bank_db.get_session(item_bank.name)
        try:
            sessions = item_db.query(models_itembank.AssessmentSession).all()
            session_ids = [s.session_id for s in sessions]

            debug_info[item_bank.name] = {
                'count': len(sessions),
                'session_ids': session_ids,
                'min_id': min(session_ids) if session_ids else None,
                'max_id': max(session_ids) if session_ids else None
            }
        finally:
            item_db.close()

    return debug_info



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.API_CONFIG["host"],
        port=config.API_CONFIG["port"]
    )