# models.py
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey, Table, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

# Many-to-many relationship table between Analysis and Extraction
analysis_extraction = Table('analysis_extraction', Base.metadata,
    Column('analysis_id', Integer, ForeignKey('analyses.id')),
    Column('extraction_id', Integer, ForeignKey('extractions.id'))
)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    extractions = relationship("Extraction", back_populates="user")
    analyses = relationship("Analysis", back_populates="user")

class Extraction(Base):
    __tablename__ = 'extractions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    file_name = Column(String, nullable=False)
    content = Column(String)
    file_hash = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    processing_status = Column(String)
    
    user = relationship("User", back_populates="extractions")
    analyses = relationship("Analysis", secondary=analysis_extraction, back_populates="extractions")

class Analysis(Base):
    __tablename__ = 'analyses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    instructions = Column(JSON)
    results = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String)
    analysis_type = Column(String)  # 'single' or 'batch'
    
    user = relationship("User", back_populates="analyses")
    extractions = relationship("Extraction", secondary=analysis_extraction, back_populates="analyses")

def init_db(database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session
