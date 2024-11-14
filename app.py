import os
import streamlit as st
from pathlib import Path
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from sqlalchemy import desc
import json
import zipfile
from io import BytesIO
from auth import login_required, role_required
from models import init_db, User, Extraction, Analysis, Project, Conversation
from ollama_setup import run_inference_on_document, summarize_image, chat_with_document
import time
import uuid
import asyncio
from utils.file_type.csv import process_csv
from utils.file_type.doc import process_docx
from utils.file_type.pdf import process_pdf
from utils.result_handler import (construct_tables_content, construct_images_content)
from dotenv import load_dotenv

# this is important to be able to nest expanders for a cleaner UI
import streamlit_nested_layout      # DO NOT REMOVE


load_dotenv()

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
        "current_project_id": None,
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
                st.rerun()
        
        st.markdown("---")
        st.markdown("### Navigation")
        stages = ["projects", "upload", "show_text", "add_instructions", "analyze", "chat"]
        # if st.session_state.get("user_role") == "advanced":
        #     stages.extend(["add_instructions", "analyze", "chat"])
        
        for stage in stages:
            if st.button(stage.replace("_", " ").title(), key=f"nav_{stage}"):
                st.session_state.stage = stage
                st.rerun()

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
                    st.rerun()
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
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Projects", len(projects))
        with col2:
            total_files = sum(len(project.extractions) for project in projects)
            st.metric("Total Files Processed", total_files)
        with col3:
            total_analyses = sum(len(project.analyses) for project in projects)
            st.metric("Total Analyses", total_analyses)
        with col4:
            total_conversations = sum(session.query(Conversation).filter_by(project_id=project.id).count() for project in projects)
            st.metric("Total Conversations", total_conversations)
        
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
                    
                    # Display last chat response
                    last_convo = session.query(Conversation).filter_by(project_id=project.id).order_by(desc(Conversation.timestamp)).first()
                    if last_convo:
                        st.markdown(f"**Last Chat Response:** {last_convo.response}")
                    
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
        st.rerun()

    uploaded_file = st.file_uploader("Upload a file", type=["pdf", "docx", "csv"])

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        process_file(uploaded_file, file_type)


def process_file(uploaded_file, file_type):
    """Handles file processing for different types (PDF, DOC, DOCX, CSV)"""
    session = db_session()
    extracted_files = []

    try:
        if file_type == "pdf":
            handle_pdf_extraction(uploaded_file, extracted_files)
        elif file_type == "docx" or file_type == "doc":
            handle_docx_extraction(uploaded_file, extracted_files)
        elif file_type == "csv":
            handle_csv_extraction(uploaded_file, extracted_files)
    finally:
        session.close()


def handle_pdf_extraction(uploaded_file, extracted_files,):
    """Handles PDF file processing and extraction"""
    extraction_category = st.selectbox("Select extraction category", ["Text", "Tables", "Images"])
    page_range_str = st.text_input("Enter page range (e.g., 1-3,5):")

    if st.button("Process PDF"):
        with st.spinner("Processing PDF... Please wait."):
            result = asyncio.run(process_pdf(uploaded_file, page_range_str, extraction_category))
            if "error" in result:
                st.error(result["error"])
                return
            st.success(result["message"])

            content = handle_extraction_content(extraction_category, result)
            extracted_files.append(save_extraction_content(uploaded_file, content, extraction_category))
            if extracted_files:
                st.session_state.extracted_files = extracted_files
                st.session_state.stage = f"show_{extraction_category.lower()}"
                st.rerun()


def handle_docx_extraction(uploaded_file, extracted_files):
    """Handles DOCX file processing and text extraction"""
    st.write("Processing File...")
    with st.spinner("Processing DOCX... Please wait."):
        text = process_docx(uploaded_file)
        extracted_files.append(save_extraction_content(uploaded_file, text, 'Text'))
        if extracted_files:
            st.session_state.extracted_files = extracted_files
            st.session_state.stage = "show_text"
            st.rerun()


def handle_csv_extraction(uploaded_file, extracted_files):
    """Handles CSV file processing and text extraction"""
    st.write("Processing CSV...")
    with st.spinner("Processing CSV... Please wait."):
        text = process_csv(uploaded_file)
        extracted_files.append(save_extraction_content(uploaded_file, text, 'Text'))
        if extracted_files:
            st.session_state.extracted_files = extracted_files
            st.session_state.stage = "show_text"
            st.rerun()


def handle_extraction_content(extraction_category, result):
    """Determines content structure based on extraction category"""
    if extraction_category == "Images":
        return construct_images_content(result)
    elif extraction_category == "Tables":
        return construct_tables_content(result)
    return result["data"]


def save_extraction_content(uploaded_file, content, category):
    """Saves extraction data to the database and returns extraction details"""
    session = db_session()
    extraction = Extraction(
        user_id=st.session_state.user_id,
        project_id=st.session_state.current_project_id,
        file_name=uploaded_file.name,
        content=json.dumps(content) if category != "Images" else "construct_images_content(result)", #update this to appropriate database content for images
        processing_status="completed"
    )
    session.add(extraction)
    session.commit()
    return {"file_name": uploaded_file.name, "content": content, "extraction_id": extraction.id}


@login_required
def show_text_page():
    """Render extracted text page"""
    display_extracted_content("Extracted Text", "text")


@login_required
def show_tables_page():
    """Render extracted tables page"""
    display_extracted_content("Extracted Tables", "tables")


@login_required
def show_images_page():
    """Render extracted images page"""
    display_extracted_content("Extracted Images", "images")


def display_extracted_content(title, content_type):
    """Generic function to render extracted content based on type"""
    st.title(title)

    for file_data in st.session_state.extracted_files:
        with st.expander(f"{file_data['file_name']} - Extracted {content_type.capitalize()}"):
            if content_type == "text":
                st.markdown(file_data["content"])
                st.download_button(
                    "Download Extracted Text",
                    file_data["content"],
                    file_name=f"{Path(file_data['file_name']).stem}_extracted.md"
                )
            elif content_type == "tables":
                display_table_content(file_data["content"])
            elif content_type == "images":
                display_image_content(file_data["content"])

    if st.session_state.user_role == "advanced" and content_type == "text":
        if st.button("Proceed to Analysis", key="to_analysis_btn"):
            st.session_state.stage = "add_instructions"
            st.rerun()


def display_table_content(table_data):
    """Displays table content extracted from the file"""
    for table_info in table_data:
        if "warning" in table_info:
            st.warning(table_info["warning"])
        else:
            st.write(f"### Table {table_info['table_index']}")
            st.markdown(f"**Context:** {table_info['context']}")
            st.write("Parsing Report:")
            st.json(json.loads(table_info["parsing_report"]))
            st.dataframe(pd.DataFrame.from_dict(table_info["table_data"]))


def display_image_content(image_data):
    """Displays image content with prompt interaction"""
    for data in image_data:
        col1, col2 = st.columns([2, 3])
        with col1:
            st.image(data["image_url"], caption=f"Image {data['image_index']}", use_container_width=True)
        with col2:
            prompt_key = f"prompt_{data['image_index'] - 1}"
            prompt = st.text_input(
                f"Ask a question about Image {data['image_index']}:",
                key=prompt_key,
                placeholder="Enter your question here"
            )
            if st.button("Submit", key=f"submit_{data['image_index'] - 1}"):
                if prompt:
                    st.write(summarize_image(data["image_url"], prompt))
                else:
                    st.warning("Please enter a question before submitting.")


@login_required
# @role_required("advanced")
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
            st.rerun()

@login_required
# @role_required("advanced")
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
        
        
@login_required
def chat_page():
    """Render chat page for interacting with documents"""
    st.title("Chat with Document")
    
    if "current_project_id" not in st.session_state:
        st.session_state.stage = "projects"
        st.experimental_rerun()
    
    session = db_session()
    try:
        # Fetch extracted files for the current project
        extractions = session.query(Extraction).filter_by(project_id=st.session_state.current_project_id).all()
        
        if not extractions:
            st.warning("No extracted files found for this project.")
            return
        
        # Select documents to chat with
        document_options = {extraction.file_name: extraction.id for extraction in extractions}
        selected_documents = st.multiselect("Select Documents", list(document_options.keys()))
        document_ids = [document_options[doc] for doc in selected_documents]
        
        # Combine contents with identifiers
        document_contents = [
            f"file name: {doc_name}\ncontent:\n{session.query(Extraction).filter_by(id=doc_id).first().content}\n{'-'*10}"
            for doc_name, doc_id in zip(selected_documents, document_ids)
        ]
        combined_content = "\n\n".join(document_contents)
                
        # Display conversation history
        conversation_history = []
        for doc_id in document_ids:
            conversation_history.extend(session.query(Conversation).filter_by(document_id=doc_id).order_by(Conversation.timestamp).all())
        
        for convo in conversation_history:
            st.markdown(
                f"""
                <div style='border-radius: 10px; padding: 10px; margin: 10px 0;'>
                    <div style='text-align: right; font-weight: bold'><b>User:</b> {convo.user_input}</div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            st.markdown(
                f"""
                <div style='border-radius: 10px; padding: 10px; margin: 10px 0;'>
                    <div style='text-align: left; font-weight: bold'><b>Response:</b> {convo.response}</div>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        # User input for chat
        user_input = st.text_input("Your message")
        if st.button("Send"):
            response = chat_with_document(combined_content, user_input, conversation_history)
            
            # Save conversation to database
            for doc_id in document_ids:
                new_convo = Conversation(
                    user_id=st.session_state.user_id,
                    project_id=st.session_state.current_project_id,
                    document_id=doc_id,
                    user_input=user_input,
                    response=response
                )
                session.add(new_convo)
            session.commit()
            
            # Clear user input box
            st.session_state["user_input"] = ""
            
            # Refresh the page to display the new conversation
            st.experimental_rerun()
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
    elif st.session_state.stage == "show_tables":
        show_tables_page()
    elif st.session_state.stage == "show_images":
        show_images_page()
    elif st.session_state.stage == "add_instructions":
        add_instructions_page()
    elif st.session_state.stage == "analyze":
        analyze_page()
    elif st.session_state.stage == "chat":
        chat_page()

if __name__ == "__main__":
    main()