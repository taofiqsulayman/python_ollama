import os
from sqlalchemy import Index, Table, create_engine, Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("Project", back_populates="user")
    
    __table_args__ = (
        Index('idx_user_id', 'id'),
        Index('idx_username', 'username'),
    )

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="projects")
    extractions = relationship("Extraction", back_populates="project")
    analyses = relationship("Analysis", back_populates="project")
    chat_history = relationship("ChatHistory", back_populates="project")

class Extraction(Base):
    __tablename__ = 'extractions'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    user_id = Column(String, ForeignKey('users.id'))  # Add this line
    file_name = Column(String, nullable=False)
    content = Column(String)
    processing_status = Column(String)  # Add this line back
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="extractions")
    user = relationship("User")  # Add this line

class Analysis(Base):
    __tablename__ = 'analyses'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    instructions = Column(JSON)
    results = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="analyses")

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    prompt = Column(String, nullable=False)
    response = Column(String, nullable=False)
    chat_type = Column(String)  # 'document' or 'image'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="chat_history")

# Association table for many-to-many relationship between Analysis and Extraction
analysis_extraction = Table(
    'analysis_extraction', Base.metadata,
    Column('analysis_id', Integer, ForeignKey('analyses.id')),
    Column('extraction_id', Integer, ForeignKey('extractions.id'))
)

def init_db(database_url: str = None):
    """Initialize database with URL from environment"""
    if not database_url:
        database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("Database URL must be provided or set in environment")
    
    engine = create_engine(database_url)
    # Create all tables
    Base.metadata.drop_all(engine)  # In development, drop all tables first
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session, engine  # Return both Session and engine