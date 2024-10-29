from typing import Dict, Any
import streamlit as st

class SessionState:
    @staticmethod
    def init():
        if "initialized" not in st.session_state:
            st.session_state.update({
                "initialized": True,
                "stage": "login",
                "extracted_files": [],
                "instructions": [],
                "uploaded_files": [],
                "user_id": None,
                "username": None,
                "user_role": None,
                "token": None
            })
    
    @staticmethod
    def reset():
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        SessionState.init()
    
    @staticmethod
    def update(data: Dict[str, Any]):
        st.session_state.update(data)