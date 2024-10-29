from functools import wraps
import streamlit as st

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'token' not in st.session_state:
            st.warning("Please log in to access this feature.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def role_required(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'user_role' not in st.session_state or st.session_state['user_role'] != required_role:
                st.warning(f"You need {required_role} access to use this feature.")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def handle_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.stop()
    return wrapper
