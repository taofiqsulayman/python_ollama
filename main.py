from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel
import base64
import logging

from models import ChatMessage, ChatSession, init_db, User, Project, Extraction, Analysis
from utils import process_files
from ollama_setup import run_inference_on_document, chat_with_document, chat_with_image

from dotenv import load_dotenv
load_dotenv()

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

# Initialize database
db = init_db(os.getenv("DATABASE_URL"))

# Default user configuration
DEFAULT_USER = {
    "id": "default-user-001",
    "username": "demo_user",
    "role": "advanced"
}

# Initialize the default user in database
def init_default_user(db_session: Session):
    user = db_session.query(User).filter_by(id=DEFAULT_USER["id"]).first()
    if not user:
        user = User(
            id=DEFAULT_USER["id"],
            username=DEFAULT_USER["username"],
            role=DEFAULT_USER["role"]
        )
        db_session.add(user)
        db_session.commit()
    return user

# Dependency to get database session
def get_db():
    session = db()
    try:
        yield session
    finally:
        session.close()

# Modified dependency to always return default user
async def get_current_user(db: Session = Depends(get_db)):
    return init_default_user(db)

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

class AnalysisInstruction(BaseModel):
    title: str
    data_type: str
    description: str

# Add this new model for chat requests
class ChatRequest(BaseModel):
    message: str
    document_ids: List[int]

# Add this new model for the analyze request
class AnalyzeRequest(BaseModel):
    instructions: List[AnalysisInstruction]

# Add this new model for image chat requests
class ImageChatRequest(BaseModel):
    message: str
    image: str  # base64 encoded image
    project_id: int

# New Response Models
class FileResponse(BaseModel):
    id: int
    file_name: str
    content: str
    processing_status: str
    created_at: datetime

class ChatHistoryItem(BaseModel):
    user_input: str
    response: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    history: List[ChatHistoryItem]

# Add new models
class ChatSessionCreate(BaseModel):
    name: Optional[str]
    file_ids: List[int]
    session_type: str = "document"  # 'document' or 'image'

class ChatMessageCreate(BaseModel):
    content: str
    additional_data: Optional[Dict] = None  # Updated from metadata to additional_data

class ChatSessionResponse(BaseModel):
    id: int
    name: Optional[str]
    files: List[int]  # Changed from file_ids to match the model
    session_type: str
    created_at: datetime

    class Config:
        orm_mode = True  # Enable ORM mode to allow direct model return

class ChatMessageResponse(BaseModel):
    role: str
    content: str
    timestamp: datetime

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
            user_id=current_user.id,
            project_id=project_id,
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
    files = db.query(Extraction).filter_by(
        project_id=project_id,
        user_id=current_user.id
    ).all()
    
    if not files:
        return []
    return files

# Analysis endpoints
@app.post("/api/v1/projects/{project_id}/analyze")
async def analyze_project_documents(
    project_id: int,
    analyze_request: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze documents in a project based on given instructions"""
    # Get project documents
    extractions = db.query(Extraction).filter_by(project_id=project_id).all()
    if not extractions:
        raise HTTPException(status_code=404, detail="No documents found")

    # Run analysis
    analyses_data = []
    for extraction in extractions:
        response = run_inference_on_document(
            extraction.content,
            [inst.dict() for inst in analyze_request.instructions]
        )
        analyses_data.append({
            "file_name": extraction.file_name,
            "extraction_id": extraction.id,
            "results": response
        })

    # Save analysis
    analysis = Analysis(
        project_id=project_id,
        user_id=current_user.id,
        instructions=[inst.dict() for inst in analyze_request.instructions],
        results={"batch_results": analyses_data},
        status="completed",
        analysis_type="batch"
    )
    db.add(analysis)
    db.commit()

    return {"analysis_id": analysis.id, "results": analyses_data}

# Chat endpoints
@app.post("/api/v1/projects/{project_id}/chat-sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    project_id: int,
    session: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat session"""
    chat_session = ChatSession(
        project_id=project_id,
        user_id=current_user.id,
        name=session.name,
        files=session.file_ids,
        session_type=session.session_type
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)  # Make sure to refresh to get the ID
    return chat_session

@app.get("/api/v1/projects/{project_id}/chat-sessions")
async def list_chat_sessions(
    project_id: int,
    session_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List chat sessions in a project, optionally filtered by type"""
    query = db.query(ChatSession).filter_by(project_id=project_id)
    if session_type:
        query = query.filter_by(session_type=session_type)
    return query.order_by(ChatSession.created_at.desc()).all()

@app.post("/api/v1/chat-sessions/{session_id}/messages")
async def add_chat_message(
    session_id: int,
    message: ChatMessageCreate,
    db: Session = Depends(get_db)
):
    """Add a message to a chat session"""
    session = db.query(ChatSession).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Handle different session types
    if session.session_type == "document":
        documents = db.query(Extraction).filter(
            Extraction.id.in_(session.files)
        ).all()
        
        # Get chat history
        history = db.query(ChatMessage).filter_by(session_id=session_id).all()
        
        # Get response from model
        response = chat_with_document(
            "\n\n".join(doc.content for doc in documents),
            message.content,
            history
        )
    elif session.session_type == "image":
        if not message.additional_data or "image" not in message.additional_data:  # Updated from metadata
            raise HTTPException(status_code=400, detail="Image data required for image chat")
        
        image_bytes = base64.b64decode(message.additional_data["image"])  # Updated from metadata
        history = db.query(ChatMessage).filter_by(session_id=session_id).all()
        
        response = chat_with_image(
            image_bytes=image_bytes,
            prompt=message.content,
            conversation_history=history
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid session type")

    # Save messages
    messages_to_add = [
        ChatMessage(
            session_id=session_id,
            role="user",
            content=message.content,
            additional_data=message.additional_data  # Updated from metadata
        ),
        ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response
        )
    ]
    
    db.add_all(messages_to_add)
    db.commit()

    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0/0", port=8000)