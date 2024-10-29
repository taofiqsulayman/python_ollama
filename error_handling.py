import logging
import sys
from functools import wraps
from typing import Type, Callable, Any
import streamlit as st
from pathlib import Path

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base exception class for application errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class FileProcessingError(AppError):
    """Raised when file processing fails"""
    pass

class AuthenticationError(AppError):
    """Raised when authentication fails"""
    pass

class DatabaseError(AppError):
    """Raised when database operations fail"""
    pass

class ModelInferenceError(AppError):
    """Raised when model inference fails"""
    pass

def handle_error(error_class: Type[Exception]) -> Callable:
    """Decorator for handling errors in Streamlit pages"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except error_class as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                st.error(f"Error: {str(e)}")
                if hasattr(e, 'status_code') and e.status_code == 401:
                    st.session_state.stage = "login"
                    st.experimental_rerun()
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
                st.error("An unexpected error occurred. Please try again later.")
        return wrapper
    return decorator

def log_function_call(func: Callable) -> Callable:
    """Decorator for logging function calls"""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.info(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"Completed {func.__name__}")
        return result
    return wrapper