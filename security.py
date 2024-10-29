import hmac
import hashlib
import time
from typing import Dict, Optional
from functools import wraps
import streamlit as st
from error_handling import AuthenticationError, logger

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}

    def is_rate_limited(self, key: str) -> bool:
        current_time = time.time()
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key]
                            if current_time - req_time < self.window_seconds]
        
        # Check if rate limit is exceeded
        if len(self.requests[key]) >= self.max_requests:
            return True
        
        self.requests[key].append(current_time)
        return False

class SecurityManager:
    def __init__(self):
        self.rate_limiter = RateLimiter()
    
    def generate_csrf_token(self) -> str:
        """Generate CSRF token for forms"""
        if 'csrf_token' not in st.session_state:
            st.session_state.csrf_token = hashlib.sha256(
                str(time.time()).encode()
            ).hexdigest()
        return st.session_state.csrf_token

    def validate_csrf_token(self, token: Optional[str]) -> bool:
        """Validate CSRF token"""
        if not token or 'csrf_token' not in st.session_state:
            return False
        return hmac.compare_digest(token, st.session_state.csrf_token)

def check_rate_limit(func):
    """Decorator to apply rate limiting to functions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in st.session_state:
            raise AuthenticationError("User not authenticated", 401)
        
        security_manager = SecurityManager()
        if security_manager.rate_limiter.is_rate_limited(st.session_state.user_id):
            logger.warning(f"Rate limit exceeded for user {st.session_state.user_id}")
            raise AuthenticationError("Rate limit exceeded. Please try again later.", 429)
        
        return func(*args, **kwargs)
    return wrapper

def validate_file_type(file_type: str) -> bool:
    """Validate if file type is allowed"""
    allowed_types = {
        'pdf', 'xlsx', 'csv', 'tsv', 'docx', 'doc', 
        'txt', 'jpg', 'jpeg', 'png'
    }
    return file_type.lower() in allowed_types

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    return ''.join(c for c in filename if c.isalnum() or c in '._-')