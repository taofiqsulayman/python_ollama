import streamlit as st
from config.settings import settings
from ui.state import SessionState
from ui.components import render_sidebar
from ui.pages import (
    login_page,
    upload_page,
    show_text_page,
    add_instructions_page,
    analyze_page
)

def initialize_app():
    """Initialize application settings and state"""
    st.set_page_config(
        layout="wide",
        page_title=settings.APP_TITLE,
        page_icon=settings.APP_ICON,
        initial_sidebar_state="expanded"
    )
    SessionState.init()

def route_to_page():
    """Route to appropriate page based on session state"""
    pages = {
        "login": login_page,
        "upload": upload_page,
        "show_text": show_text_page,
        "add_instructions": add_instructions_page,
        "analyze": analyze_page
    }
    
    current_page = st.session_state.stage
    if current_page in pages:
        pages[current_page]()
    else:
        st.error("Invalid page")
        SessionState.reset()
        st.experimental_rerun()

def main():
    """Main application entry point"""
    try:
        initialize_app()
        render_sidebar()
        route_to_page()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)
        # In production, you might want to log the error instead of showing it
        if not settings.DEBUG:
            st.error("An unexpected error occurred. Please try again later.")

if __name__ == "__main__":
    main()