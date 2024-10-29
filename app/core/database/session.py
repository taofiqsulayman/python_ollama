from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings

class DatabaseSession:
    _engine = None
    _SessionLocal = None

    @classmethod
    def initialize(cls):
        if not cls._engine:
            cls._engine = create_engine(settings.DATABASE_URL)
            cls._SessionLocal = sessionmaker(bind=cls._engine)

    @classmethod
    def get_session(cls) -> Session:
        if not cls._SessionLocal:
            cls.initialize()
        return cls._SessionLocal()