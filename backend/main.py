from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import pandas as pd
import io
import logging

from database import get_db, engine
import models
import schemas
from irt_engine import IRTEngine
from services import UserService, QuestionService, AssessmentService
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

@app.post("/api/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user or get existing user"""
    return user_service.get_or_create_user(db, user.username, user.competence_level)

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
    """Start a new assessment session"""
    user = user_service.get_user_by_username(db, assessment_start.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session = assessment_service.start_assessment(
        db, user.id, assessment_start.subject
    )

    # Get first question
    first_question = assessment_service.get_next_question(
        db, session.id, irt_engine
    )

    return {
        "session_id": session.id,
        "current_question": first_question,
        "theta": session.current_theta,
        "sem": session.current_sem,
        "questions_asked": session.questions_asked
    }

@app.post("/api/assessments/{session_id}/answer", response_model=schemas.AssessmentSession)
def submit_answer(
    session_id: int,
    answer: schemas.AnswerSubmission,
    db: Session = Depends(get_db)
):
    """Submit an answer and get next question"""

    # Record response
    recorded_response = assessment_service.record_response(
        db, session_id, answer.question_id, answer.selected_option, irt_engine
    )

    # Get updated session
    session = assessment_service.get_session(db, session_id)

    # Check if assessment should continue
    if session.is_completed:
        response_data = {
            "session_id": session.id,
            "current_question": None,
            "theta": session.current_theta,
            "sem": session.current_sem,
            "questions_asked": session.questions_asked,
            "completed": True,
            "last_response_correct": recorded_response.is_correct
        }
        logger.info(f"Returning completion response: {response_data}")
        return response_data

    # Get next question
    next_question = assessment_service.get_next_question(
        db, session_id, irt_engine
    )

    return {
        "session_id": session.id,
        "current_question": next_question,
        "theta": session.current_theta,
        "sem": session.current_sem,
        "questions_asked": session.questions_asked,
        "completed": session.is_completed,
        "last_response_correct": recorded_response.is_correct

    }

@app.get("/api/assessments/{session_id}/results", response_model=schemas.AssessmentResults)
def get_assessment_results(session_id: int, db: Session = Depends(get_db)):
    """Get assessment results"""
    return assessment_service.get_assessment_results(db, session_id)

@app.get("/api/users/{username}/proficiency", response_model=schemas.UserProficiency)
def get_user_proficiency(username: str, db: Session = Depends(get_db)):
    """Get user's proficiency across subjects"""
    user = user_service.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user_service.get_user_proficiency(db, user.id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=config.API_CONFIG["host"], 
        port=config.API_CONFIG["port"]
    )
