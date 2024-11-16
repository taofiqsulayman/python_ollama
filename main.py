from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel
import json
import base64

from models import ImageInferencingHistory, init_db, User, Project, Extraction, Analysis, Conversation
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
    db_project = Project(
        user_id=current_user.id,
        name=project.name,
        description=project.description
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

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
@app.post("/api/v1/projects/{project_id}/chat")
async def chat_with_documents(
    project_id: int,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Chat with selected documents in a project"""
    # Get documents
    documents = db.query(Extraction).filter(
        Extraction.id.in_(chat_request.document_ids),
        Extraction.project_id == project_id
    ).all()

    if not documents:
        raise HTTPException(status_code=404, detail="Documents not found")

    # Get conversation history
    history = db.query(Conversation).filter(
        Conversation.project_id == project_id,
        Conversation.document_id.in_(chat_request.document_ids)
    ).order_by(Conversation.timestamp).all()

    # Combine document contents
    combined_content = "\n\n".join([
        f"file name: {doc.file_name}\ncontent:\n{doc.content}"
        for doc in documents
    ])

    # Get response
    response = chat_with_document(combined_content, chat_request.message, history)

    # Save conversation for each document
    for doc in documents:
        conversation = Conversation(
            user_id=current_user.id,
            project_id=project_id,
            document_id=doc.id,
            files=chat_request.document_ids,
            user_input=chat_request.message,
            response=response,
            history=[{
                "id": h.id,
                "user_input": h.user_input,
                "response": h.response,
                "timestamp": h.timestamp.isoformat()
            } for h in history]
        )
        db.add(conversation)
    
    db.commit()

    return {"response": response}

@app.get("/api/v1/projects/{project_id}/chat-history", response_model=ChatHistoryResponse)
async def get_project_chat_history(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document chat history for a project"""
    history = db.query(Conversation).filter_by(
        project_id=project_id,
        user_id=current_user.id
    ).order_by(Conversation.timestamp).all()
    
    return {
        "history": [
            {"user_input": h.user_input, "response": h.response, "timestamp": h.timestamp}
            for h in history
        ]
    }

@app.get("/api/v1/projects/{project_id}/image-chat-history", response_model=ChatHistoryResponse)
async def get_project_image_chat_history(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get image chat history for a project"""
    history = db.query(ImageInferencingHistory).filter_by(
        project_id=project_id,
        user_id=current_user.id
    ).order_by(ImageInferencingHistory.timestamp).all()
    
    chat_history = []
    for h in history:
        if h.history:
            for item in h.history:
                if item.get("role") == "user":
                    chat_history.append({
                        "user_input": item["content"],
                        "response": next(
                            (x["content"] for x in h.history if x["role"] == "assistant"),
                            "No response"
                        ),
                        "timestamp": h.timestamp
                    })
    
    return {"history": chat_history}

# Image chat endpoint
@app.post("/api/v1/projects/{project_id}/image-chat")
async def chat_with_your_image(
    project_id: int,
    request: ImageChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Chat about an image in a project"""
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(request.image)
        
        # Get conversation history
        history = db.query(ImageInferencingHistory).filter(
            ImageInferencingHistory.project_id == request.project_id
        ).order_by(ImageInferencingHistory.timestamp.desc()).limit(5).all()

        conversation_history = []
        for h in history:
            if h.history:
                conversation_history.extend(h.history)

        # Get response from model
        response = chat_with_image(
            image_bytes=image_bytes,
            prompt=request.message,
            conversation_history=conversation_history
        )

        # Save to history
        history_entry = ImageInferencingHistory(
            user_id=current_user.id,
            project_id=request.project_id,
            file=f"chat_{datetime.utcnow().isoformat()}",
            history=[*conversation_history, {
                "role": "user",
                "content": request.message
            }, {
                "role": "assistant",
                "content": response
            }]
        )
        db.add(history_entry)
        db.commit()

        return {"response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0/0", port=8000)