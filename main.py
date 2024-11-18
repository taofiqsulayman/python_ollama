from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import base64
import logging
import torch

from models import ChatHistory, init_db, User, Project, Extraction, Analysis, Base
from utils import process_files
from ollama_setup import run_inference_on_document, chat_with_document, chat_with_image

from dotenv import load_dotenv
load_dotenv()

# Initialize logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize FastAPI app
app = FastAPI(title="Document Processing API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database connection on module level
try:
    db_session, engine = init_db(os.getenv("DATABASE_URL"))
    db = db_session
    logging.info("Database initialization successful")
except Exception as e:
    logging.error(f"Failed to initialize database: {str(e)}")
    raise

# Default user configuration
DEFAULT_USER = {
    "id": "default-user-001",
    "username": "demo_user",
    "role": "advanced"
}

def ensure_default_user():
    """Ensure default user exists in database"""
    session = db()
    try:
        # First ensure tables exist
        Base.metadata.create_all(engine)
        
        user = session.query(User).filter_by(id=DEFAULT_USER["id"]).first()
        if not user:
            logging.info("Creating default user...")
            user = User(
                id=DEFAULT_USER["id"],
                username=DEFAULT_USER["username"],
                role=DEFAULT_USER["role"]
            )
            session.add(user)
            session.commit()
            logging.info("Default user created successfully")
        return user
    except Exception as e:
        logging.error(f"Error ensuring default user: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

# Dependency to get database session
def get_db():
    session = db()
    try:
        yield session
    finally:
        session.close()

# Modified dependency to use cached default user
def get_current_user(db_session: Session = Depends(get_db)) -> User:
    """Get or create default user, with proper error handling"""
    try:
        user = db_session.query(User).filter_by(id=DEFAULT_USER["id"]).first()
        if not user:
            # If user doesn't exist, create it
            user = User(
                id=DEFAULT_USER["id"],
                username=DEFAULT_USER["username"],
                role=DEFAULT_USER["role"]
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            logging.info("Created default user during request")
        return user
    except Exception as e:
        logging.error(f"Error getting/creating default user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while accessing user"
        )

# Request/Response Models
class UserResponse(BaseModel):
    id: str
    username: str
    role: str
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

class FileResponse(BaseModel):
    id: int
    file_name: str
    content: str
    created_at: datetime

class AnalysisInstruction(BaseModel):
    title: str
    description: str
    data_type: str = "text"  # default to text

class AnalysisRequest(BaseModel):
    instructions: List[AnalysisInstruction]

class AnalysisResponse(BaseModel):
    id: int
    instructions: List[AnalysisInstruction]
    results: dict
    created_at: datetime

class ChatRequest(BaseModel):
    prompt: str
    chat_type: str = "document"  # or "image"
    image_data: Optional[str] = None  # base64 string for images

# User endpoints
@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

# Project endpoints
@app.post("/api/v1/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project"""
    try:
        logging.info(f"Creating project: {project.dict()}")
        logging.info(f"Current user: {current_user.id}")
        
        db_project = Project(
            user_id=current_user.id,
            name=project.name,
            description=project.description
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        
        logging.info(f"Project created: {db_project.id}")
        return db_project
    except Exception as e:
        logging.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/projects", response_model=List[ProjectResponse])
async def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all projects for current user"""
    return db.query(Project).filter_by(user_id=current_user.id).all()

# Document processing endpoints
@app.post("/api/v1/projects/{project_id}/files")
async def upload_project_files(
    project_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload multiple files to a project and return their processed content"""
    project = db.query(Project).filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    results = []
    for file in files:
        content = await process_files(file)
        extraction = Extraction(
            project_id=project_id,  # Keep only these fields
            file_name=file.filename,
            content=content,
            processing_status="completed"
        )
        db.add(extraction)
        db.commit()
        
        results.append({
            "id": extraction.id,
            "file_name": file.filename,
            "content": content,
            "status": "completed"
        })
    
    return {"message": "Files processed successfully", "files": results}

@app.get("/api/v1/projects/{project_id}/files", response_model=List[FileResponse])
async def get_project_files(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all files associated with a project"""
    files = db.query(Extraction).filter_by(project_id=project_id).all()  # Remove user_id filter
    if not files:
        return []
    return files


# Analysis endpoints
@app.post("/api/v1/projects/{project_id}/analyze", response_model=AnalysisResponse)
async def analyze_documents(
    project_id: int,
    analysis: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    documents = db.query(Extraction).filter_by(project_id=project_id).all()
    if not documents:
        raise HTTPException(status_code=404, detail="No documents found")

    # Format documents in a more structured way
    combined_content = "\n\n".join(
        f"### Document: {doc.file_name}\n"
        f"Content:\n{doc.content}\n"
        f"{'='*50}"  # Clear visual separator
        for doc in documents
    )
    
    # Add a preamble to help guide the LLM
    context = (
        "You have been provided with multiple documents. "
        "Each document is clearly marked with its name and content, "
        "separated by '=' symbols. "
        "Please analyze these documents according to the given instructions.\n\n"
    )
    
    final_content = context + combined_content

    # Convert instructions to the format expected by run_inference_on_document
    formatted_instructions = []
    for instr in analysis.instructions:
        formatted_instructions.append({
            "title": instr.title,
            "description": instr.description,
            "data_type": instr.data_type
        })
    
    results = run_inference_on_document(final_content, formatted_instructions)
    
    # Convert instructions to JSON-compatible format for storage
    instructions_data = [
        instr.dict() for instr in analysis.instructions
    ]
    
    db_analysis = Analysis(
        project_id=project_id,
        instructions=instructions_data,
        results=results
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    
    return db_analysis

@app.get("/api/v1/projects/{project_id}/analyses", response_model=List[AnalysisResponse])
async def get_project_analyses(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Analysis).filter_by(project_id=project_id).all()


# Chat endpoints
@app.post("/api/v1/projects/{project_id}/chat")
async def chat_with_project(
    project_id: int,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Chat with documents or images in a project"""
    project = db.query(Project).filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get last 5 conversations for context, filtered by chat_type
    recent_history = (
        db.query(ChatHistory)
        .filter_by(
            project_id=project_id,
            chat_type=chat_request.chat_type  # Add this filter
        )
        .order_by(ChatHistory.created_at.desc())
        .limit(5)
        .all()
    )
    
    conversation_history = [
        {"role": "user", "content": h.prompt} if i % 2 == 0 else {"role": "assistant", "content": h.response}
        for h in reversed(recent_history)
        for i in range(2)
    ]

    if chat_request.chat_type == "document":
        documents = db.query(Extraction).filter_by(project_id=project_id).all()
        
        # Format documents with clear structure
        combined_content = "\n\n".join(
            f"### Document: {doc.file_name}\n"
            f"Content:\n{doc.content}\n"
            f"{'='*50}"  # Clear visual separator
            for doc in documents
        )
        
        # Add context for the LLM
        context = (
            "You have access to the following documents. "
            "Each document is marked with its name and content, "
            "separated by '=' symbols. "
            "Please use these documents to answer the user's question.\n\n"
        )
        
        final_content = context + combined_content
        response = chat_with_document(final_content, chat_request.prompt, conversation_history)
    
    elif chat_request.chat_type == "image":
        if not chat_request.image_data:
            raise HTTPException(status_code=400, detail="Image data required for image chat")
        image_bytes = base64.b64decode(chat_request.image_data)
        response = chat_with_image(image_bytes, chat_request.prompt, conversation_history)
    
    else:
        raise HTTPException(status_code=400, detail="Invalid chat type")

    # Updated chat history creation
    chat_history = ChatHistory(
        project_id=project_id,
        user_id=current_user.id,  # This will now work with the updated model
        prompt=chat_request.prompt,
        response=response,
        chat_type=chat_request.chat_type
    )
    db.add(chat_history)
    db.commit()

    return {"response": response}

@app.get("/api/v1/projects/{project_id}/chat-history")
async def get_chat_history(
    project_id: int,
    chat_type: Optional[str] = None,  # Add this parameter
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat history for a project, optionally filtered by chat type"""
    query = db.query(ChatHistory).filter_by(project_id=project_id)
    
    if chat_type:  # Filter by chat_type if provided
        query = query.filter_by(chat_type=chat_type)
    
    history = query.order_by(ChatHistory.created_at).all()
    
    return {
        "history": [
            {
                "prompt": h.prompt,
                "response": h.response,
                "type": h.chat_type,
                "timestamp": h.created_at
            }
            for h in history
        ]
    }

@app.on_event("startup")
async def startup_event():
    """Initialize app requirements on startup"""
    try:
        # Ensure default user exists
        ensure_default_user()
        
        # Check GPU availability
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_names = [torch.cuda.get_device_name(i) for i in range(device_count)]
            logging.info(f"GPU available: {device_count} device(s)")
            for i, name in enumerate(device_names):
                logging.info(f"GPU {i}: {name}")
        else:
            logging.warning("No GPU available, running on CPU")
        
        logging.info("Application startup complete")
    except Exception as e:
        logging.error(f"Fatal error during startup: {str(e)}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0/0", port=8000)