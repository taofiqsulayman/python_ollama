import os
import streamlit as st
import tempfile
from pathlib import Path
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from sqlalchemy import desc

from config import init_config, get_database_url

from auth import KeycloakAuth, login_required, role_required
from models import init_db, User, Extraction, Analysis
from utils import process_files
from ollama_setup import run_inference_on_document
import time

# Initialize services
# db_session = init_db(os.getenv('DATABASE_URL'))
# keycloak_auth = KeycloakAuth()

config = init_config()
db_session = init_db(get_database_url())

if os.getenv("DEBUG") == "True":
    from dev_auth import DevAuth
    keycloak_auth = DevAuth()
else:
    from auth import KeycloakAuth
    keycloak_auth = KeycloakAuth()

# Page config
st.set_page_config(
    layout="wide",
    page_title="File Processor",
    page_icon="📄",
    initial_sidebar_state="expanded"
)

# Session state initialization
def init_session_state():
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

init_session_state()

# Database operations
def get_or_create_user(session: Session, user_id: str, username: str, role: str) -> User:
    """Check if user exists, and create if not."""
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        # Ensure that the role is not null; assign a default role if necessary
        user_role = role if role else 'basic'
        user = User(id=user_id, username=username, role=user_role, created_at=datetime.utcnow())
        session.add(user)
        session.commit()
    return user

def save_extraction(session: Session, user_id: str, file_name: str, content: str) -> Extraction:
    """Save extracted content to database with status"""
    extraction = Extraction(
        user_id=user_id,
        file_name=file_name,
        content=content,
        processing_status="completed",
        created_at=datetime.utcnow()
    )
    session.add(extraction)
    session.commit()
    return extraction

def save_analysis(session: Session, user_id: str, extraction_id: int, instructions: List[Dict[str, Any]], results: Dict[str, Any]) -> Analysis:
    """Save analysis results to database with status"""
    analysis = Analysis(
        user_id=user_id,
        extraction_id=extraction_id,
        instructions=instructions,
        results=results,
        status="completed",
        created_at=datetime.utcnow()
    )
    session.add(analysis)
    session.commit()
    return analysis

def get_user_history(session: Session, user_id: str) -> Dict[str, List]:
    """Fetch user's extraction and analysis history"""
    extractions = session.query(Extraction).filter_by(user_id=user_id).order_by(desc(Extraction.created_at)).all()
    analyses = session.query(Analysis).filter_by(user_id=user_id).order_by(desc(Analysis.created_at)).all()
    
    return {
        "extractions": extractions,
        "analyses": analyses
    }

# UI Components
def render_sidebar():
    """Render sidebar with user info and logout button"""
    with st.sidebar:
        st.title("File Processor")
        
        if st.session_state.get("username"):
            st.markdown(f"### Welcome, {st.session_state.username}")
            st.markdown(f"Role: {st.session_state.user_role}")
            
            if st.button("Logout", key="logout_btn"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                init_session_state()
                st.experimental_rerun()
        
        st.markdown("---")
        st.markdown("### Navigation")
        stages = ["upload", "show_text", "history"]
        if st.session_state.get("user_role") == "advanced":
            stages.extend(["add_instructions", "analyze"])
        
        for stage in stages:
            if st.button(stage.replace("_", " ").title(), key=f"nav_{stage}"):
                st.session_state.stage = stage
                st.experimental_rerun()

def login_page():
    """Render login page"""
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted and username and password:
            token_response = keycloak_auth.get_token(username, password)
            if token_response:
                token = token_response['access_token']
                user_info = keycloak_auth.verify_token(token)
                
                if user_info:
                    st.session_state.update({
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
    """Render file upload page"""
    st.title("Upload Files")
    
    uploaded_files = st.file_uploader(
        "Upload supported files",
        accept_multiple_files=True,
        type=["pdf", "xlsx", "csv", "tsv", "docx", "doc", "txt", "jpg", "jpeg", "png"]
    )
    
    if st.button("Extract Text", key="extract_btn") and uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        extracted_files = []
        
        with st.spinner("Extracting text..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                input_dir = Path(temp_dir) / "input"
                input_dir.mkdir()
                
                session = db_session()
                try:
                    # Get the user's role from session state or provide a default
                    user_role = st.session_state.get('user_role', 'basic')
                    
                    # Ensure the user exists in the database
                    user = get_or_create_user(
                        session,
                        st.session_state.user_id,
                        st.session_state.username,
                        user_role
                    )

                    for uploaded_file in uploaded_files:
                        input_file = input_dir / uploaded_file.name
                        with open(input_file, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        extracted_text = process_files(input_file)
                        extraction = save_extraction(
                            session,
                            st.session_state.user_id,
                            uploaded_file.name,
                            extracted_text
                        )
                        
                        extracted_files.append({
                            "file_name": uploaded_file.name,
                            "content": extracted_text,
                            "extraction_id": extraction.id
                        })
                finally:
                    session.close()
        
        st.session_state.extracted_files = extracted_files
        st.session_state.stage = "show_text"
        st.experimental_rerun()

@login_required
def show_text_page():
    """Render extracted text page"""
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
            st.session_state.stage = "add_instructions"
            st.experimental_rerun()

@login_required
@role_required("advanced")
def add_instructions_page():
    """Render instructions page"""
    st.title("Analysis Instructions")
    
    with st.form("instruction_form"):
        title = st.text_input("Title")
        data_type = st.selectbox("Data Type", ["string", "number"])
        description = st.text_area("Description")
        submitted = st.form_submit_button("Add Instruction")
        
        if submitted and title and description:
            st.session_state.instructions.append({
                "title": title,
                "data_type": data_type,
                "description": description
            })
    
    if st.session_state.instructions:
        st.markdown("### Current Instructions")
        for instruction in st.session_state.instructions:
            with st.expander(instruction["title"]):
                st.markdown(instruction["description"])
                st.markdown(f"Data Type: {instruction['data_type']}")
        
        if st.button("Run Analysis", key="run_analysis_btn"):
            st.session_state.stage = "analyze"
            st.experimental_rerun()

@login_required
@role_required("advanced")
def analyze_page():
    """Render analysis page"""
    st.title("Analysis Results")
    
    start_time = time.time()
    responses = []
    
    session = db_session()
    try:
        with st.spinner("Analyzing documents..."):
            for file_data in st.session_state.extracted_files:
                response = run_inference_on_document(
                    file_data["content"],
                    st.session_state.instructions
                )
                
                save_analysis(
                    session,
                    st.session_state.user_id,
                    file_data["extraction_id"],
                    st.session_state.instructions,
                    response
                )
                
                responses.append({
                    "file_name": file_data["file_name"],
                    "data": response
                })
        
        # Create DataFrame for display
        df_data = []
        for response in responses:
            row = {"File Name": response["file_name"]}
            data = response["data"]
            if data:
                for instruction in st.session_state.instructions:
                    title = instruction["title"]
                    formatted_title = title.lower().replace(" ", "_")
                    row[title] = data.get(formatted_title)
            df_data.append(row)
        
        if df_data:
            st.markdown("### Results")
            st.markdown(f"Processing time: {time.time() - start_time:.2f} seconds")
            st.dataframe(pd.DataFrame(df_data))
            
            # Download results
            csv = pd.DataFrame(df_data).to_csv(index=False)
            st.download_button(
                "Download Results as CSV",
                csv,
                file_name="analysis_results.csv"
            )
    finally:
        session.close()

@login_required
def history_page():
    """Render history page showing saved extractions and analyses"""
    st.title("History")
    
    session = db_session()
    try:
        history = get_user_history(session, st.session_state.user_id)
        
        # Display Extractions
        st.header("Extracted Files")
        if history["extractions"]:
            for extraction in history["extractions"]:
                with st.expander(f"{extraction.file_name} - {extraction.created_at.strftime('%Y-%m-%d %H:%M')}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.text(f"Status: {extraction.processing_status}")
                        if extraction.content:
                            st.markdown("### Content Preview")
                            st.markdown(extraction.content[:500] + "..." if len(extraction.content) > 500 else extraction.content)
                            st.download_button(
                                "Download Full Content",
                                extraction.content,
                                file_name=f"{extraction.file_name}_content.md"
                            )
                    
                    # Show related analyses in second column
                    with col2:
                        related_analyses = [a for a in history["analyses"] if a.extraction_id == extraction.id]
                        if related_analyses:
                            st.markdown("### Related Analyses")
                            for analysis in related_analyses:
                                st.markdown(f"**Analysis {analysis.id}** - {analysis.created_at.strftime('%Y-%m-%d %H:%M')}")
                                st.markdown("#### Instructions")
                                for instruction in analysis.instructions:
                                    st.markdown(f"- **{instruction['title']}**: {instruction['description']}")
                                
                                st.markdown("#### Results")
                                st.json(analysis.results)
                                
                                # Convert results to CSV for download
                                if analysis.results:
                                    df = pd.DataFrame([analysis.results])
                                    csv = df.to_csv(index=False)
                                    st.download_button(
                                        f"Download Analysis {analysis.id} Results",
                                        csv,
                                        file_name=f"analysis_{analysis.id}_results.csv"
                                    )
                                st.markdown("---")
                        else:
                            st.info("No analyses found for this extraction")
        else:
            st.info("No extractions found")
            
        # Add filter options
        st.sidebar.markdown("### Filters")
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(datetime.now().date(), datetime.now().date())
        )
        
        if st.session_state.user_role == "advanced":
            st.sidebar.markdown("### Bulk Actions")
            if st.sidebar.button("Delete Selected"):
                # Add deletion logic here
                pass
            
            if st.sidebar.button("Export All Results"):
                # Add export logic here
                pass
    finally:
        session.close()

# Main app routing
def main():
    render_sidebar()
    
    if st.session_state.stage == "login":
        login_page()
    elif st.session_state.stage == "upload":
        upload_page()
    elif st.session_state.stage == "show_text":
        show_text_page()
    elif st.session_state.stage == "add_instructions":
        add_instructions_page()
    elif st.session_state.stage == "analyze":
        analyze_page()
    elif st.session_state.stage == "history":
        history_page()

if __name__ == "__main__":
    main()