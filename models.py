from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey, Table, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

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
    status = Column(String, default='active')  # active, completed
    
    user = relationship("User", back_populates="projects")
    extractions = relationship("Extraction", back_populates="project")
    analyses = relationship("Analysis", back_populates="project")
    chat_sessions = relationship("ChatSession", back_populates="project")  # Add this line

class Extraction(Base):
    __tablename__ = 'extractions'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    user_id = Column(String, ForeignKey('users.id'))
    file_name = Column(String, nullable=False)
    content = Column(String)
    images = Column(JSON)  # New field for image URLs
    tables = Column(JSON)  # New field for tables
    file_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String)
    
    project = relationship("Project", back_populates="extractions")
    analyses = relationship("Analysis", secondary="analysis_extraction", back_populates="extractions")

class Analysis(Base):
    __tablename__ = 'analyses'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    user_id = Column(String, ForeignKey('users.id'))
    instructions = Column(JSON)
    results = Column(JSON)
    files = Column(JSON)  # New field for files involved in the analysis
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)
    analysis_type = Column(String)  # 'single' or 'batch'
    
    project = relationship("Project", back_populates="analyses")
    extractions = relationship("Extraction", secondary="analysis_extraction", back_populates="analyses")

# Association table for many-to-many relationship between Analysis and Extraction
analysis_extraction = Table(
    'analysis_extraction', Base.metadata,
    Column('analysis_id', Integer, ForeignKey('analyses.id')),
    Column('extraction_id', Integer, ForeignKey('extractions.id'))
)

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    user_id = Column(String, ForeignKey('users.id'))
    name = Column(String)  # Optional name for the chat session
    files = Column(JSON)  # List of file IDs involved
    created_at = Column(DateTime, default=datetime.utcnow)
    session_type = Column(String)  # 'document' or 'image'
    
    # Relationships
    project = relationship("Project", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.timestamp")
    user = relationship("User")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    additional_data = Column(JSON, nullable=True)  # Renamed from metadata to additional_data
    
    session = relationship("ChatSession", back_populates="messages")

# Remove or deprecate the Conversation class as it's being replaced by ChatSession and ChatMessage

# Remove these classes as they're being replaced
# class Conversation
# class ImageInferencingHistory

def init_db(database_url: str):
    if not database_url:
        raise ValueError("Database URL must be provided")
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session