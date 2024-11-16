from datetime import datetime
import streamlit as st
import requests
import json
from PIL import Image
import base64
import pandas as pd
import time

# Page config
st.set_page_config(
    layout="wide",
    page_title="File Processor",
    page_icon="📄",
    initial_sidebar_state="expanded"
)

# Session state initialization
def init_session_state():
    default_state = {
        "initialized": True,
        "stage": "projects",
        "current_project_id": None,
        "current_chat_session": None,  # Chat session ID
        "instructions": [],  # Analysis instructions
        # Chat history per session
        "chat_sessions": {},  # Dictionary to store chat sessions by ID
        "current_chat_name": None,  # Name of current chat session
        "current_chat_files": [],  # Files in current chat session
        "current_chat_type": None,  # 'document' or 'image'
        "message_history": {},  # Store message history by session ID
        "last_message_time": {},  # Track last message time for each session
        "auto_refresh": True,  # Toggle for auto-refresh
    }
    
    # Initialize each key if it doesn't exist
    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

API_BASE_URL = "http://localhost:8000"

# UI Components
def render_sidebar():
    """Render sidebar with navigation"""
    with st.sidebar:
        st.title("File Processor")
        st.markdown("### Navigation")
        stages = ["projects", "upload", "analyze", "chat", "chat_image"]
        
        for stage in stages:
            if st.button(stage.replace("_", " ").title(), key=f"nav_{stage}"):
                st.session_state.stage = stage
                st.rerun()

def project_page():
    """Render project page"""
    st.title("Projects")
    
    # Create Project section
    with st.expander("Create New Project"):
        with st.form("create_project_form"):
            name = st.text_input("Project Name")
            description = st.text_area("Project Description")
            submitted = st.form_submit_button("Create Project")
            
            if submitted and name:
                # Fix: Update endpoint to match backend
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/projects",  # Changed from /projects/
                    json={"name": name, "description": description}
                )
                if response.status_code == 200:
                    project_data = response.json()
                    st.session_state.current_project_id = project_data["id"]
                    st.session_state.stage = "upload"
                    st.rerun()
                else:
                    st.error(f"Error creating project: {response.json().get('detail', 'Unknown error')}")

    # Fix: Update endpoint to match backend
    response = requests.get(f"{API_BASE_URL}/api/v1/projects")  # Changed from /projects/
    if response.status_code == 200:
        projects = response.json()
        for project in projects:
            with st.expander(f"📁 {project['name']}"):
                st.markdown(f"**Description:** {project['description']}")
                if st.button("Select Project", key=f"select_{project['id']}"):
                    st.session_state.current_project_id = project['id']
                    st.session_state.stage = "upload"
                    st.rerun()

def upload_page():
    """Render file upload page"""
    st.title("Upload Files")

    if "current_project_id" not in st.session_state:
        st.session_state.stage = "projects"
        st.rerun()

    uploaded_files = st.file_uploader(
        "Upload files",
        type=["pdf", "docx", "csv"],
        accept_multiple_files=True  # Allow multiple file upload
    )
    
    if uploaded_files:
        with st.spinner("Uploading files..."):
            # Create list of tuples for files parameter
            files = [
                ("files", (file.name, file.getvalue(), file.type))
                for file in uploaded_files
            ]
            
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/projects/{st.session_state.current_project_id}/files",
                    files=files
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"Successfully uploaded {len(result['files'])} files!")
                    
                    # Display uploaded files and their content
                    for file_info in result['files']:
                        with st.expander(f"📄 {file_info['file_name']}"):
                            st.write("Content preview:")
                            st.markdown(file_info['content'][:500] + "..." if len(file_info['content']) > 500 else file_info['content'])
                else:
                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error uploading files: {str(e)}")

def analyze_page():
    """Combined analysis and instructions page"""
    st.title("Document Analysis")
    
    if "current_project_id" not in st.session_state:
        st.session_state.stage = "projects"
        st.rerun()

    # Split the page into two columns
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Add Instructions")
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

        # Show current instructions
        if st.session_state.instructions:
            st.markdown("### Current Instructions")
            for idx, instruction in enumerate(st.session_state.instructions):
                with st.expander(f"{idx + 1}. {instruction['title']}"):
                    st.markdown(f"**Description:** {instruction['description']}")
                    st.markdown(f"**Data Type:** {instruction['data_type']}")
                    if st.button("Remove", key=f"remove_{idx}"):
                        st.session_state.instructions.pop(idx)
                        st.rerun()

    with col2:
        st.markdown("### Analysis Results")
        if not st.session_state.instructions:
            st.info("Add instructions on the left to analyze documents")
            return
        
        if st.button("Run Analysis", type="primary"):
            with st.spinner("Analyzing documents..."):
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/projects/{st.session_state.current_project_id}/analyze/",
                    json={"instructions": st.session_state.instructions}
                )
                
                if response.status_code == 200:
                    results = response.json()["results"]
                    
                    # Create DataFrame from results
                    df_data = []
                    for analysis in results:
                        row = {"File": analysis["file_name"]}
                        row.update(analysis["results"])
                        df_data.append(row)
                    
                    df = pd.DataFrame(df_data)
                    
                    # Display results
                    st.dataframe(df)
                    
                    # Download options in columns
                    dl_col1, dl_col2 = st.columns(2)
                    with dl_col1:
                        st.download_button(
                            "Download CSV",
                            df.to_csv(index=False),
                            file_name="analysis_results.csv",
                            mime="text/csv"
                        )
                    
                    with dl_col2:
                        st.download_button(
                            "Download JSON",
                            json.dumps(results, indent=2),
                            file_name="analysis_results.json",
                            mime="application/json"
                        )
                    
                    # Display summary statistics for numeric columns
                    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
                    if len(numeric_cols) > 0:
                        with st.expander("View Summary Statistics"):
                            st.dataframe(df[numeric_cols].describe())
                else:
                    st.error(f"Error analyzing documents: {response.json()['detail']}")

def render_chat_interface(session_id: int, session_type: str = "document", current_image=None):
    """Shared chat interface component for both document and image chat"""
    # Message display container
    messages_container = st.container()
    processing_container = st.empty()  # Container for loading indicator
    input_container = st.container()  # Container for input

    # Fetch existing messages
    if session_id not in st.session_state.message_history:
        messages_response = requests.get(
            f"{API_BASE_URL}/api/v1/chat-sessions/{session_id}/messages"
        )
        if messages_response.status_code == 200:
            st.session_state.message_history[session_id] = messages_response.json()["messages"]

    # Display existing messages
    with messages_container:
        for msg in st.session_state.message_history.get(session_id, []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                st.caption(f":clock2: {msg['timestamp']}")
    
    # Chat input
    with input_container:
        if prompt := st.chat_input("Type your message..."):
            # Show user message immediately
            with st.chat_message("user"):
                st.markdown(prompt)
                st.caption(":clock2: Just now")
            
            # Add to session history immediately
            st.session_state.message_history[session_id] = st.session_state.message_history.get(session_id, []) + [
                {"role": "user", "content": prompt, "timestamp": "Just now"}
            ]

            # Show loading indicator in processing container
            with processing_container:
                with st.spinner("Processing..."):
                    # Prepare message data
                    message_data = {
                        "content": prompt,
                        "additional_data": {
                            "image": base64.b64encode(current_image.getvalue()).decode()
                        } if session_type == "image" and current_image else None
                    }
                    
                    # Send message to API
                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/chat-sessions/{session_id}/messages",
                        json=message_data
                    )
                    
                    if response.status_code == 200:
                        assistant_response = response.json()["response"]
                        # Add assistant response to history
                        st.session_state.message_history[session_id].append({
                            "role": "assistant",
                            "content": assistant_response,
                            "timestamp": "Just now"
                        })
                        
                        # Show assistant response
                        with st.chat_message("assistant"):
                            st.markdown(assistant_response)
                            st.caption(":clock2: Just now")
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

            # Clear the processing container after response
            processing_container.empty()

def chat_page():
    """Render chat page with session management"""
    st.title("Chat with Documents")
    
    if "current_project_id" not in st.session_state:
        st.session_state.stage = "projects"
        st.rerun()
    
    # Initialize chat session if needed
    if "current_chat_session" not in st.session_state:
        st.session_state.current_chat_session = None

    # Chat session management
    col1, col2 = st.columns([2, 1])
    with col1:
        # Get project files for new chat
        response = requests.get(f"{API_BASE_URL}/api/v1/projects/{st.session_state.current_project_id}/files")
        if response.status_code == 200:
            documents = response.json()
            selected_docs = st.multiselect(
                "Select documents for new chat",
                options=[(doc["id"], doc["file_name"]) for doc in documents],
                format_func=lambda x: x[1]
            )
            
            if st.button("Start New Chat") and selected_docs:
                try:
                    session_data = {
                        "name": f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        "file_ids": [doc[0] for doc in selected_docs],
                        "session_type": "document"
                    }
                    
                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/projects/{st.session_state.current_project_id}/chat-sessions",
                        json=session_data
                    )
                    
                    if response.status_code == 200:
                        # Debug the response
                        response_data = response.json()
                        st.write("Debug - Full Response:", response_data)
                        
                        if "id" in response_data:
                            st.session_state.current_chat_session = response_data["id"]
                            st.rerun()
                        else:
                            st.error(f"Invalid response format. Expected 'id' in response. Got: {response_data}")
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except Exception as e:
                    st.error(f"Error creating chat session: {str(e)}")
                    st.write("Response content:", response.text)

    with col2:
        # List existing chat sessions
        response = requests.get(
            f"{API_BASE_URL}/api/v1/projects/{st.session_state.current_project_id}/chat-sessions",
            params={"session_type": "document"}
        )
        if response.status_code == 200:
            sessions = response.json()
            session_names = {s["id"]: s["name"] for s in sessions}
            selected_session = st.selectbox(
                "Or select existing chat",
                options=list(session_names.keys()),
                format_func=lambda x: session_names[x],
                index=None
            )
            if selected_session:
                st.session_state.current_chat_session = selected_session

    # Render chat interface if session is selected
    if st.session_state.current_chat_session:
        st.markdown("---")
        render_chat_interface(st.session_state.current_chat_session, "document")

def chat_with_image_page():
    """Render image chat page"""
    st.title("Chat with Image")
    
    if "current_project_id" not in st.session_state:
        st.session_state.stage = "projects"
        st.rerun()
    
    # Initialize chat session if needed
    if "current_chat_session" not in st.session_state:
        st.session_state.current_chat_session = None

    # Session management for image chat
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("Start New Image Chat"):
            try:
                session_data = {
                    "name": f"Image Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    "file_ids": [],
                    "session_type": "image"
                }
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/projects/{st.session_state.current_project_id}/chat-sessions",
                    json=session_data
                )
                
                if response.status_code == 200:
                    session_data = response.json()
                    # Debug the response
                    st.write("Debug - Session Response:", session_data)
                    st.session_state.current_chat_session = session_data.get("id")
                    if st.session_state.current_chat_session:
                        st.rerun()
                    else:
                        st.error("Failed to get chat session ID from response")
                else:
                    st.error(f"Failed to create chat session: {response.text}")
            except Exception as e:
                st.error(f"Error creating chat session: {str(e)}")

    with col2:
        # List existing image chat sessions
        response = requests.get(
            f"{API_BASE_URL}/api/v1/projects/{st.session_state.current_project_id}/chat-sessions",
            params={"session_type": "image"}
        )
        if response.status_code == 200:
            sessions = response.json()
            session_names = {s["id"]: s["name"] for s in sessions}
            selected_session = st.selectbox(
                "Or select existing image chat",
                options=list(session_names.keys()),
                format_func=lambda x: session_names[x],
                index=None
            )
            if selected_session:
                st.session_state.current_chat_session = selected_session

    # Image upload and chat interface
    uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
    
    if uploaded_file and st.session_state.current_chat_session:
        image = Image.open(uploaded_file)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.image(image, caption="Uploaded Image", width=None)
        
        with col2:
            st.download_button(
                label="Download Original Image",
                data=uploaded_file,
                file_name=uploaded_file.name,
                mime=f"image/{uploaded_file.type.split('/')[-1]}"
            )
        
        st.markdown("---")
        render_chat_interface(
            st.session_state.current_chat_session,
            session_type="image",
            current_image=uploaded_file
        )

def main():
    render_sidebar()
    
    if st.session_state.stage == "projects":
        project_page()
    elif st.session_state.stage == "upload":
        upload_page()
    elif st.session_state.stage == "analyze":  # Single analyze page
        analyze_page()
    elif st.session_state.stage == "chat":
        chat_page()
    elif st.session_state.stage == "chat_image":
        chat_with_image_page()

if __name__ == "__main__":
    main()