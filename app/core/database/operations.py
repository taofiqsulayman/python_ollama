from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models.schemas import User, Extraction, Analysis


def get_or_create_user(
    session: Session,
    user_id: str,
    username: str,
    role: str
) -> User:
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        user_role = role if role else 'basic'
        user = User(
            id=user_id,
            username=username,
            role=user_role,
            created_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
    return user

@staticmethod
def save_extraction(
    session: Session,
    user_id: str,
    file_name: str,
    content: str
) -> Extraction:
    extraction = Extraction(
        user_id=user_id,
        file_name=file_name,
        content=content,
        created_at=datetime.utcnow()
    )
    session.add(extraction)
    session.commit()
    return extraction

@staticmethod
def save_analysis(
    session: Session,
    user_id: str,
    extraction_id: int,
    instructions: List[Dict[str, Any]],
    results: Dict[str, Any]
) -> Analysis:
    analysis = Analysis(
        user_id=user_id,
        extraction_id=extraction_id,
        instructions=instructions,
        results=results,
        created_at=datetime.utcnow()
    )
    session.add(analysis)
    session.commit()
    return analysis