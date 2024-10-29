# # models.py
# from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker, relationship
# from datetime import datetime

# Base = declarative_base()

# class User(Base):
#     __tablename__ = 'users'
    
#     id = Column(String, primary_key=True)
#     username = Column(String, unique=True, nullable=False)
#     email = Column(String, unique=True, nullable=False)
#     role = Column(String, nullable=False)  # 'basic' or 'advanced'
#     created_at = Column(DateTime, default=datetime.utcnow)
    
#     extractions = relationship("Extraction", back_populates="user")
#     analyses = relationship("Analysis", back_populates="user")

# class Extraction(Base):
#     __tablename__ = 'extractions'
    
#     id = Column(Integer, primary_key=True)
#     user_id = Column(String, ForeignKey('users.id'))
#     file_name = Column(String, nullable=False)
#     content = Column(String, nullable=False)
#     created_at = Column(DateTime, default=datetime.utcnow)
    
#     user = relationship("User", back_populates="extractions")
#     analyses = relationship("Analysis", back_populates="extraction")

# class Analysis(Base):
#     __tablename__ = 'analyses'
    
#     id = Column(Integer, primary_key=True)
#     user_id = Column(String, ForeignKey('users.id'))
#     extraction_id = Column(Integer, ForeignKey('extractions.id'))
#     instructions = Column(JSON, nullable=False)
#     results = Column(JSON, nullable=False)
#     created_at = Column(DateTime, default=datetime.utcnow)
    
#     user = relationship("User", back_populates="analyses")
#     extraction = relationship("Extraction", back_populates="analyses")

# def init_db(database_url):
#     engine = create_engine(database_url)
#     Base.metadata.create_all(engine)
#     return sessionmaker(bind=engine)


# models.py
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class Extraction(Base):
    __tablename__ = 'extractions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    file_name = Column(String, nullable=False)
    content = Column(String)
    file_hash = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    processing_status = Column(String)

class Analysis(Base):
    __tablename__ = 'analyses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    extraction_id = Column(Integer, ForeignKey('extractions.id'))
    instructions = Column(JSON)
    results = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String)

def init_db(database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session