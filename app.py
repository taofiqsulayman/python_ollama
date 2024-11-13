import os
from uuid import uuid4
import streamlit as st
import tempfile
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from sqlalchemy import desc
import json
import zipfile
from io import BytesIO

from auth import KeycloakAuth, login_required, role_required
from models import init_db, User, Extraction, Analysis, Project
from utils import process_files
from ollama_setup import run_inference_on_document
import time

from collections import Counter
import streamlit_nested_layout
import uuid


db_session = init_db('postgresql://fileprocessor:yourpassword@localhost:5432/fileprocessor')

if os.getenv("DEV") == "True":
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
            "token": None,
            "current_project_id": None
        })

def reset_session_state():
    st.session_state.update({
        "stage": "projects",
        "extracted_files": [],
        "instructions": [],
        "uploaded_files": [],
        "current_project_id": None
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
        project_id=st.session_state.current_project_id,
        file_name=file_name,
        content=content,
        processing_status="completed",
        created_at=datetime.utcnow()
    )
    session.add(extraction)
    session.commit()
    return extraction

def save_batch_analysis(session: Session, user_id: str, analyses_data: List[Dict[str, Any]], instructions: List[Dict[str, Any]]) -> Analysis:
    """Save a batch of analysis results"""
    batch_analysis = Analysis(
        project_id=st.session_state.current_project_id,
        user_id=user_id,
        instructions=instructions,
        results={
            'batch_results': analyses_data,
            'summary': {
                'total_files': len(analyses_data),
                'timestamp': datetime.utcnow().isoformat(),
            }
        },
        status="completed",
        analysis_type="batch"
    )
    
    extraction_ids = [data['extraction_id'] for data in analyses_data]
    extractions = session.query(Extraction).filter(Extraction.id.in_(extraction_ids)).all()
    batch_analysis.extractions.extend(extractions)
    
    session.add(batch_analysis)
    session.commit()
    return batch_analysis

def generate_session_name() -> str:
    """Generate a unique session name based on timestamp"""
    return f"Session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

def get_user_history(session: Session, user_id: str) -> Dict[str, List]:
    """Fetch user's extraction and analysis history"""
    extractions = session.query(Extraction).filter_by(user_id=user_id).order_by(desc(Extraction.created_at)).all()
    analyses = session.query(Analysis).filter_by(user_id=user_id).order_by(desc(Analysis.created_at)).all()
    
    return {
        "extractions": extractions,
        "analyses": analyses
    }

def create_project(session: Session, user_id: str, name: str, description: str) -> Project:
    project = Project(user_id=user_id, name=name, description=description)
    session.add(project)
    session.commit()
    reset_session_state()  # Reset session state on new project creation
    return project

def get_user_projects(session: Session, user_id: str) -> List[Project]:
    return session.query(Project).filter_by(user_id=user_id).all()

def create_project_zip(project: Project) -> BytesIO:
    """Create a ZIP file containing all project files and their analyses"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Save extractions
        for extraction in project.extractions:
            file_name = f"extractions/{extraction.file_name}_content.txt"
            zip_file.writestr(file_name, extraction.content)
        
        # Save analyses
        for analysis in project.analyses:
            # Save instructions
            if analysis.instructions:
                file_name = f"analyses/analysis_{analysis.id}/instructions.json"
                zip_file.writestr(file_name, json.dumps(analysis.instructions, indent=2))
            
            # Save results
            if analysis.results:
                file_name = f"analyses/analysis_{analysis.id}/results.json"
                zip_file.writestr(file_name, json.dumps(analysis.results, indent=2))
                
                # If it's a batch analysis, also save as CSV
                if analysis.analysis_type == "batch" and "batch_results" in analysis.results:
                    results_df = pd.DataFrame([
                        {'File': res['file_name'], **res['results']}
                        for res in analysis.results['batch_results']
                    ])
                    file_name = f"analyses/analysis_{analysis.id}/results.csv"
                    zip_file.writestr(file_name, results_df.to_csv(index=False))
    
    zip_buffer.seek(0)
    return zip_buffer

def create_project_json(project: Project) -> dict:
    """Create a JSON representation of the entire project"""
    return {
        "project_info": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at.isoformat(),
            "status": project.status
        },
        "extractions": [
            {
                "id": extraction.id,
                "file_name": extraction.file_name,
                "content": extraction.content,
                "created_at": extraction.created_at.isoformat(),
                "status": extraction.processing_status
            }
            for extraction in project.extractions
        ],
        "analyses": [
            {
                "id": analysis.id,
                "instructions": analysis.instructions,
                "results": analysis.results,
                "created_at": analysis.created_at.isoformat(),
                "status": analysis.status,
                "type": analysis.analysis_type
            }
            for analysis in project.analyses
        ]
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
        stages = ["projects", "upload", "show_text"]
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
                    reset_session_state()  # Reset session state on sign in
                    st.session_state.update({
                        "token": token,
                        "user_id": user_info['sub'],
                        "username": user_info['preferred_username'],
                        "user_role": user_info.get('role', 'basic'),
                        "stage": "projects"
                    })
                    st.experimental_rerun()
                else:
                    st.error("Invalid token")
            else:
                st.error("Invalid credentials")

@login_required
def project_page():
    """Render project page with project creation and history"""
    st.title("Projects")
    
    session = db_session()
    try:
        # Get all user projects
        projects = session.query(Project).filter_by(user_id=st.session_state.user_id).all()
        
        # Display metrics
        st.markdown("## Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Projects", len(projects))
        with col2:
            total_files = sum(len(project.extractions) for project in projects)
            st.metric("Total Files Processed", total_files)
        with col3:
            total_analyses = sum(len(project.analyses) for project in projects)
            st.metric("Total Analyses", total_analyses)
        
        # Create Project section
        with st.expander("Create New Project"):
            with st.form("create_project_form"):
                name = st.text_input("Project Name")
                description = st.text_area("Project Description")
                submitted = st.form_submit_button("Create Project")
                
                if submitted and name:
                    new_project = create_project(session, st.session_state.user_id, name, description)
                    st.session_state.current_project_id = new_project.id
                    st.session_state.stage = "upload"
                    st.experimental_rerun()
        
        # Previous Projects section
        with st.expander("Previous Projects"):
            for project in projects:
                with st.expander(f"📁 {project.name} - Created: {project.created_at.strftime('%Y-%m-%d %H:%M')}"):
                    # Project info
                    st.markdown(f"""
                        **Description:** {project.description}  
                        **Status:** {project.status}  
                        **Created:** {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                    """)
                    
                    # Download options
                    col1, col2 = st.columns(2)
                    with col1:
                        if project.extractions or project.analyses:
                            zip_buffer = create_project_zip(project)
                            st.download_button(
                                "📥 Download All Files (ZIP)",
                                zip_buffer,
                                file_name=f"project_{project.id}_{project.name}.zip",
                                mime="application/zip",
                                key=f"zip_{project.id}"
                            )
                    with col2:
                        if project.extractions or project.analyses:
                            project_json = create_project_json(project)
                            st.download_button(
                                "📥 Download All (JSON)",
                                json.dumps(project_json, indent=2),
                                file_name=f"project_{project.id}_{project.name}.json",
                                mime="application/json",
                                key=f"json_{project.id}"
                            )
                    
                    # Select project button
                    if st.button("Select Project", key=f"select_{project.id}"):
                        st.session_state.current_project_id = project.id
                        st.session_state.extracted_files = [
                            {
                                "file_name": extraction.file_name,
                                "content": extraction.content,
                                "extraction_id": extraction.id
                            }
                            for extraction in project.extractions
                        ]
                        st.session_state.instructions = [
                            {
                                "title": instruction["title"],
                                "data_type": instruction["data_type"],
                                "description": instruction["description"]
                            }
                            for analysis in project.analyses
                            for instruction in analysis.instructions
                        ]
                        st.session_state.stage = "upload"
                        st.experimental_rerun()
                    
                    # Files section
                    if project.extractions:
                        st.markdown("### Files")
                        for extraction in project.extractions:
                            with st.expander(f"📄 {extraction.file_name}"):
                                st.markdown(f"**Status:** {extraction.processing_status}")
                                
                                if extraction.content:
                                    st.download_button(
                                        "Download Content",
                                        extraction.content,
                                        file_name=f"{extraction.file_name}_content.txt",
                                        mime="text/plain",
                                        key=f"dl_{extraction.id}"
                                    )
                                    
                                    with st.expander("Content Preview"):
                                        preview_length = 300
                                        preview = extraction.content[:preview_length]
                                        if len(extraction.content) > preview_length:
                                            preview += "..."
                                        st.markdown(preview)
                    
                    # Analysis section
                    if project.analyses:
                        st.markdown("### Analyses")
                        for analysis in project.analyses:
                            with st.expander(f"🔍 Analysis {analysis.id}"):
                                # Instructions
                                if analysis.instructions:
                                    st.markdown("#### Instructions")
                                    for instr in analysis.instructions:
                                        st.markdown(f"""
                                            - **{instr['title']}**
                                            - Type: {instr.get('data_type', 'N/A')}
                                            - Description: {instr.get('description', 'N/A')}
                                        """)
                                
                                # Results
                                if analysis.results:
                                    st.markdown("#### Results")
                                    if analysis.analysis_type == "batch":
                                        results_df = pd.DataFrame([
                                            {'File': res['file_name'], **res['results']}
                                            for res in analysis.results['batch_results']
                                        ])
                                        st.dataframe(results_df)
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.download_button(
                                                "Download CSV",
                                                results_df.to_csv(index=False),
                                                file_name=f"analysis_{analysis.id}_results.csv",
                                                key=f"{uuid.uuid4()}"
                                            )
                                        with col2:
                                            st.download_button(
                                                "Download JSON",
                                                json.dumps(analysis.results, indent=2),
                                                file_name=f"analysis_{analysis.id}_results.json",
                                                key=f"{uuid.uuid4()}"
                                            )
    
    finally:
        session.close()

@login_required
def upload_page():
    """Render file upload page with session handling"""
    st.title("Upload Files")
    
    if "current_project_id" not in st.session_state:
        st.session_state.stage = "project"
        st.experimental_rerun()
    
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
                    for uploaded_file in uploaded_files:
                        input_file = input_dir / uploaded_file.name
                        with open(input_file, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        extracted_text = process_files(input_file)
                        extraction = Extraction(
                            user_id=st.session_state.user_id,
                            project_id=st.session_state.current_project_id,
                            file_name=uploaded_file.name,
                            content=extracted_text,
                            processing_status="completed"
                        )
                        session.add(extraction)
                        session.commit()
                        
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
    """Render analysis page with normalized data handling"""
    st.title("Analysis Results")
    
    start_time = time.time()
    analyses_data = []
    
    session = db_session()
    try:
        with st.spinner("Analyzing documents..."):
            for file_data in st.session_state.extracted_files:
                response = run_inference_on_document(
                    file_data["content"],
                    st.session_state.instructions
                )
                
                # Normalize the response data
                normalized_response = {}
                for instruction in st.session_state.instructions:
                    title = instruction["title"]
                    formatted_title = title.lower().replace(" ", "_")
                    
                    # Get the value from response, or None if not found
                    value = response.get(formatted_title)
                    
                    # Convert lists to string representation if needed
                    if isinstance(value, list):
                        value = '; '.join(str(item) for item in value)
                    # Convert dictionaries to string representation if needed
                    elif isinstance(value, dict):
                        value = str(value)
                    # Ensure other values are string or numeric
                    elif value is not None:
                        if not isinstance(value, (str, int, float)):
                            value = str(value)
                    
                    normalized_response[formatted_title] = value
                
                analyses_data.append({
                    "file_name": file_data["file_name"],
                    "extraction_id": file_data["extraction_id"],
                    "results": normalized_response
                })
            
            # Save batch analysis
            batch_analysis = save_batch_analysis(
                session,
                st.session_state.user_id,
                analyses_data,
                st.session_state.instructions
            )
        
        # Create DataFrame with normalized data
        df_data = []
        column_types = {}  # Track consistent column types
        
        # First pass: determine column types
        for analysis in analyses_data:
            for instruction in st.session_state.instructions:
                title = instruction["title"]
                formatted_title = title.lower().replace(" ", "_")
                value = analysis["results"].get(formatted_title)
                
                if value is not None:
                    if isinstance(value, (int, float)):
                        column_types[formatted_title] = 'numeric'
                    else:
                        column_types[formatted_title] = 'string'
        
        # Second pass: create normalized rows
        for analysis in analyses_data:
            row = {"File Name": analysis["file_name"]}
            
            for instruction in st.session_state.instructions:
                title = instruction["title"]
                formatted_title = title.lower().replace(" ", "_")
                value = analysis["results"].get(formatted_title)
                
                # Convert value based on determined column type
                if column_types.get(formatted_title) == 'numeric':
                    try:
                        row[title] = float(value) if value is not None else None
                    except (ValueError, TypeError):
                        row[title] = None
                else:
                    row[title] = str(value) if value is not None else None
            
            df_data.append(row)
        
        if df_data:
            st.markdown("### Results")
            st.markdown(f"Processing time: {time.time() - start_time:.2f} seconds")
            
            # Create DataFrame with explicit dtypes
            df = pd.DataFrame(df_data)
            
            # Convert columns to appropriate types
            for col in df.columns:
                if col != "File Name" and col in [instr["title"] for instr in st.session_state.instructions]:
                    if column_types.get(col.lower().replace(" ", "_")) == 'numeric':
                        df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Display the DataFrame
            st.dataframe(df)
            
            # Download options
            csv = df.to_csv(index=False)
            st.download_button(
                "Download Results as CSV",
                csv,
                file_name=f"batch_analysis_{batch_analysis.id}_results.csv"
            )
            
            # Display summary statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
            if len(numeric_cols) > 0:
                st.markdown("### Summary Statistics")
                st.dataframe(df[numeric_cols].describe())
            
            # Option to download raw analysis data
            if st.button("Download Raw Analysis Data"):
                raw_data = {
                    'batch_id': batch_analysis.id,
                    'instructions': st.session_state.instructions,
                    'analyses': analyses_data,
                    'summary': {
                        'processing_time': time.time() - start_time,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
                st.download_button(
                    "Download Raw JSON",
                    data=json.dumps(raw_data, default=str),
                    file_name=f"batch_analysis_{batch_analysis.id}_raw.json"
                )
    except Exception as e:
        st.error(f"An error occurred during analysis: {str(e)}")
        st.exception(e)
    finally:
        session.close()


# Main app routing
def main():
    render_sidebar()
    
    if st.session_state.stage == "login":
        login_page()
    elif st.session_state.stage == "projects":
        project_page()
    elif st.session_state.stage == "upload":
        upload_page()
    elif st.session_state.stage == "show_text":
        show_text_page()
    elif st.session_state.stage == "add_instructions":
        add_instructions_page()
    elif st.session_state.stage == "analyze":
        analyze_page()

if __name__ == "__main__":
    main()