import streamlit as st
from datetime import datetime
import pandas as pd
from pathlib import Path
import tempfile
import time
from typing import List, Dict, Any

from config.settings import settings
from core.auth.keycloak import KeycloakAuth
from core.auth.dev import DevAuth
from ui.state import SessionState
from utils.decorators import login_required, role_required
from services.extraction import ExtractionService
from services.analysis import AnalysisService

# Initialize auth provider based on settings
auth_provider = DevAuth() if settings.DEBUG else KeycloakAuth()

def login_page():
    """Render login page with authentication handling"""
    st.title("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted and username and password:
            token_response = auth_provider.get_token(username, password)
            
            if token_response:
                token = token_response['access_token']
                user_info = auth_provider.verify_token(token)
                
                if user_info:
                    SessionState.update({
                        "token": token,
                        "user_id": user_info['sub'],
                        "username": user_info['preferred_username'],
                        "user_role": user_info.get('role', 'basic'),
                        "stage": "upload"
                    })
                    st.experimental_rerun()
                else:
                    st.error("Invalid token")
            else:
                st.error("Invalid credentials")

@login_required
def upload_page():
    """Handle file upload and text extraction"""
    st.title("Upload Files")
    
    uploaded_files = st.file_uploader(
        "Upload supported files",
        accept_multiple_files=True,
        type=[ext[1:] for exts in settings.SUPPORTED_EXTENSIONS.values() for ext in exts]
    )
    
    if st.button("Extract Text", key="extract_btn") and uploaded_files:
        with st.spinner("Extracting text..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                # Process uploaded files
                files_data = []
                for uploaded_file in uploaded_files:
                    temp_path = Path(temp_dir) / uploaded_file.name
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    files_data.append({
                        "path": str(temp_path),
                        "name": uploaded_file.name
                    })
                
                # Extract text using service
                extracted_files = ExtractionService.process_files(
                    files_data,
                    st.session_state.user_id
                )
                
                SessionState.update({
                    "extracted_files": extracted_files,
                    "stage": "show_text"
                })
                st.experimental_rerun()

@login_required
def show_text_page():
    """Display extracted text with download options"""
    st.title("Extracted Text")
    
    for file_data in st.session_state.extracted_files:
        with st.expander(f"{file_data['file_name']} - Extracted Text"):
            st.markdown(file_data["content"])
            st.download_button(
                "Download Extracted Text",
                file_data["content"],
                file_name=f"{Path(file_data['file_name']).stem}_extracted.md"
            )
    
    if st.session_state.user_role == "advanced":
        if st.button("Proceed to Analysis", key="to_analysis_btn"):
            SessionState.update({"stage": "add_instructions"})
            st.experimental_rerun()

@login_required
@role_required("advanced")
def add_instructions_page():
    """Add analysis instructions"""
    st.title("Analysis Instructions")
    
    with st.form("instruction_form"):
        title = st.text_input("Title")
        data_type = st.selectbox("Data Type", ["string", "number"])
        description = st.text_area("Description")
        submitted = st.form_submit_button("Add Instruction")
        
        if submitted and title and description:
            instructions = st.session_state.get("instructions", [])
            instructions.append({
                "title": title,
                "data_type": data_type,
                "description": description
            })
            SessionState.update({"instructions": instructions})
    
    if st.session_state.instructions:
        st.markdown("### Current Instructions")
        for instruction in st.session_state.instructions:
            with st.expander(instruction["title"]):
                st.markdown(instruction["description"])
                st.markdown(f"Data Type: {instruction['data_type']}")
        
        if st.button("Run Analysis", key="run_analysis_btn"):
            SessionState.update({"stage": "analyze"})
            st.experimental_rerun()

@login_required
@role_required("advanced")
def analyze_page():
    """Run analysis and display results"""
    st.title("Analysis Results")
    
    start_time = time.time()
    
    with st.spinner("Analyzing documents..."):
        # Run analysis using service
        analysis_service = AnalysisService()
        results = analysis_service.analyze_documents(
            st.session_state.extracted_files,
            st.session_state.instructions,
            st.session_state.user_id
        )
        
        # Create DataFrame for display
        df_data = []
        for result in results:
            row = {"File Name": result["file_name"]}
            row.update(result["analysis_results"])
            df_data.append(row)
        
        if df_data:
            st.markdown("### Results")
            st.markdown(f"Processing time: {time.time() - start_time:.2f} seconds")
            
            # Display results
            df = pd.DataFrame(df_data)
            st.dataframe(df)
            
            # Download option
            csv = df.to_csv(index=False)
            st.download_button(
                "Download Results as CSV",
                csv,
                file_name="analysis_results.csv"
            )