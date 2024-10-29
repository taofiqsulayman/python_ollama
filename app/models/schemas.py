from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)

class Extraction(Base):
    __tablename__ = "extractions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    file_name = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    extraction_id = Column(Integer, ForeignKey("extractions.id"), nullable=False)
    instructions = Column(JSON, nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)