# config.py
import os
from dotenv import load_dotenv
from pathlib import Path

def init_config():
    """Initialize configuration by loading environment variables"""
    # Try to load from .env file
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)
    
    # Required configuration with defaults
    config = {
        'DATABASE_URL': os.getenv('DATABASE_URL', 'sqlite:///fileprocessor.db'),
        'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
        'SECRET_KEY': os.getenv('SECRET_KEY', 'default-secret-key'),
        'MAX_FILE_SIZE': int(os.getenv('MAX_FILE_SIZE', 10485760)),
        'UPLOAD_FOLDER': os.getenv('UPLOAD_FOLDER', './uploads'),
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
    }
    
    # Validate required configurations
    if config['DATABASE_URL'] is None:
        raise ValueError("DATABASE_URL must be set in environment or .env file")
    
    return config

# Database initialization function
def get_database_url():
    """Get database URL with fallback to SQLite"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        # Fallback to SQLite database
        db_path = Path('.') / 'fileprocessor.db'
        db_url = f'sqlite:///{db_path}'
        print(f"Warning: DATABASE_URL not set, falling back to SQLite at {db_path}")
    return db_url