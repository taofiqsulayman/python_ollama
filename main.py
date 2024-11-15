from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import json

from models import init_db, User, Project, Extraction, Analysis, Conversation
from utils import process_files
from ollama_setup import run_inference_on_document, chat_with_document
from dev_auth import DevAuth

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
db = init_db('postgresql://fileprocessor:yourpassword@localhost:5432/fileprocessor')

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

# User endpoints
@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Project endpoints
@app.post("/projects/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_project = Project(
        user_id=current_user.id,
        name=project.name,
        description=project.description
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.get("/projects/", response_model=List[ProjectResponse])
async def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Project).filter_by(user_id=current_user.id).all()

# Document processing endpoints
@app.post("/projects/{project_id}/documents/")
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check project exists and belongs to user
    project = db.query(Project).filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Process the file
    content = await process_files(file)
    
    # Save extraction
    extraction = Extraction(
        user_id=current_user.id,
        project_id=project_id,
        file_name=file.filename,
        content=content,
        processing_status="completed"
    )
    db.add(extraction)
    db.commit()
    
    return {"message": "File processed successfully", "extraction_id": extraction.id}

# Analysis endpoints
@app.post("/projects/{project_id}/analyze/")
async def analyze_documents(
    project_id: int,
    instructions: List[AnalysisInstruction],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get project documents
    extractions = db.query(Extraction).filter_by(project_id=project_id).all()
    if not extractions:
        raise HTTPException(status_code=404, detail="No documents found")

    # Run analysis
    analyses_data = []
    for extraction in extractions:
        response = run_inference_on_document(
            extraction.content,
            [inst.dict() for inst in instructions]
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
        instructions=[inst.dict() for inst in instructions],
        results={"batch_results": analyses_data},
        status="completed",
        analysis_type="batch"
    )
    db.add(analysis)
    db.commit()

    return {"analysis_id": analysis.id, "results": analyses_data}

# Chat endpoints
@app.post("/projects/{project_id}/chat/")
async def chat(
    project_id: int,
    message: str,
    document_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get documents
    documents = db.query(Extraction).filter(
        Extraction.id.in_(document_ids),
        Extraction.project_id == project_id
    ).all()

    if not documents:
        raise HTTPException(status_code=404, detail="Documents not found")

    # Get conversation history
    history = db.query(Conversation).filter(
        Conversation.project_id == project_id,
        Conversation.document_id.in_(document_ids)
    ).order_by(Conversation.timestamp).all()

    # Combine document contents
    combined_content = "\n\n".join([
        f"file name: {doc.file_name}\ncontent:\n{doc.content}"
        for doc in documents
    ])

    # Get response
    response = chat_with_document(combined_content, message, history)

    # Save conversation for each document
    for doc in documents:
        conversation = Conversation(
            user_id=current_user.id,
            project_id=project_id,
            document_id=doc.id,
            files=document_ids,
            user_input=message,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0/0", port=8000)