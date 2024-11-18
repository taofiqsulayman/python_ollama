import streamlit as st
import requests
import json
from PIL import Image
import base64
import pandas as pd  # Add this import

# Page config
st.set_page_config(
    layout="wide",
    page_title="Document Analysis Assistant",
    page_icon="📄",
    initial_sidebar_state="expanded"
)

# Session state initialization
def init_session_state():
    """Initialize session state with only essential data"""
    default_state = {
        "current_project_id": None,
        "stage": "projects",  # projects, upload, analyze, chat, chat_image
        "analysis_instructions": [],
    }
    
    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

API_BASE_URL = "http://localhost:8000/api/v1"

def api_request(method, endpoint, **kwargs):
    """Wrapper for API requests with error handling"""
    try:
        response = requests.request(method, f"{API_BASE_URL}/{endpoint}", **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def render_sidebar():
    """Render navigation sidebar"""
    with st.sidebar:
        st.title("Document Analysis Assistant")
        
        # Project selection if we're not on projects page
        if st.session_state.current_project_id:
            st.markdown("### Current Project")
            projects = api_request("GET", "projects")
            if projects:
                current_project = next(
                    (p for p in projects if p["id"] == st.session_state.current_project_id),
                    None
                )
                if current_project:
                    st.info(f"📁 {current_project['name']}")
        
        st.markdown("### Navigation")
        
        if st.button("🏠 Projects", use_container_width=True):
            st.session_state.stage = "projects"
            st.rerun()
            
        if st.session_state.current_project_id:
            if st.button("📤 Upload Files", use_container_width=True):
                st.session_state.stage = "upload"
                st.rerun()
                
            if st.button("🔍 Analyze", use_container_width=True):
                st.session_state.stage = "analyze"
                st.rerun()
                
            if st.button("💬 Document Chat", use_container_width=True):
                st.session_state.stage = "chat"
                st.rerun()
                
            if st.button("🖼️ Image Chat", use_container_width=True):
                st.session_state.stage = "chat_image"
                st.rerun()

def project_page():
    """Project management page"""
    st.title("Projects")
    
    with st.expander("➕ Create New Project", expanded=True):
        with st.form("create_project"):
            name = st.text_input("Project Name")
            description = st.text_area("Description")
            if st.form_submit_button("Create Project"):
                if name:
                    result = api_request("POST", "projects", json={
                        "name": name,
                        "description": description
                    })
                    if result:
                        st.session_state.current_project_id = result["id"]
                        st.success("Project created successfully!")
                        st.rerun()
                else:
                    st.warning("Please enter a project name")
    
    st.markdown("### Existing Projects")
    projects = api_request("GET", "projects")
    
    if not projects:
        st.info("No projects found. Create one to get started!")
        return
        
    for project in projects:
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"#### 📁 {project['name']}")
                if project['description']:
                    st.markdown(f"_{project['description']}_")
                st.caption(f"Created: {project['created_at']}")
            with col2:
                if st.button("Select", key=f"select_{project['id']}", use_container_width=True):
                    st.session_state.current_project_id = project['id']
                    st.session_state.stage = "upload"
                    st.rerun()

def upload_page():
    """File upload and management page"""
    st.title("Upload Files")
    
    # Show existing files
    files = api_request("GET", f"projects/{st.session_state.current_project_id}/files")
    if files:
        st.markdown("### Existing Files")
        for file in files:
            with st.expander(f"📄 {file['file_name']}"):
                st.text_area(
                    "Content Preview",
                    value=file['content'][:500] + "..." if len(file['content']) > 500 else file['content'],
                    height=100,
                    disabled=True
                )
    
    st.markdown("### Upload New Files")
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        accept_multiple_files=True,
        type=["txt", "pdf", "docx"]
    )
    
    if uploaded_files:
        if st.button("Process Files", type="primary"):
            with st.spinner("Processing files..."):
                files = [
                    ("files", (file.name, file.getvalue(), file.type))
                    for file in uploaded_files
                ]
                
                result = api_request(
                    "POST",
                    f"projects/{st.session_state.current_project_id}/files",
                    files=files
                )
                
                if result:
                    st.success(f"Successfully processed {len(result['files'])} files!")
                    st.rerun()

def analyze_page():
    """Document analysis page"""
    st.title("Document Analysis")
    
    if "current_project_id" not in st.session_state:
        st.session_state.stage = "projects"
        st.rerun()

    if "instructions" not in st.session_state:
        st.session_state.instructions = []

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Add Instructions")
        with st.form("instruction_form"):
            title = st.text_input("Title")
            data_type = st.selectbox("Data Type", ["string", "number", "date", "list"])
            description = st.text_area("Description")
            submitted = st.form_submit_button("Add Instruction")
            
            if submitted and title and description:
                instruction = {
                    "title": title,
                    "description": description,
                    "data_type": data_type
                }
                st.session_state.instructions.append(instruction)
                st.rerun()

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
                result = api_request(
                    "POST",
                    f"projects/{st.session_state.current_project_id}/analyze",
                    json={"instructions": st.session_state.instructions}
                )
                
                if result and "results" in result:
                    results = result["results"]
                    
                    # Create DataFrame from results
                    try:
                        # Extract values from nested result structure
                        data = {}
                        for field, details in results.items():
                            data[field] = details.get("value", None)
                        
                        # Create DataFrame with single row
                        df = pd.DataFrame([data])
                        
                        # Display the table
                        st.markdown("#### Results Table")
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Display raw results in expandable section
                        with st.expander("🔍 View Detailed Results"):
                            st.json(results)
                        
                        # Download options
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                "📥 Download CSV",
                                df.to_csv(index=False),
                                file_name="analysis_results.csv",
                                mime="text/csv"
                            )
                        with col2:
                            st.download_button(
                                "📥 Download JSON",
                                data=json.dumps(results, indent=2),
                                file_name="analysis_results.json",
                                mime="application/json"
                            )
                        
                        # Show confidence levels
                        st.markdown("#### Confidence Levels")
                        confidence_data = {
                            field: details.get("confidence", "unknown")
                            for field, details in results.items()
                        }
                        confidence_df = pd.DataFrame([confidence_data])
                        st.dataframe(
                            confidence_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                    except Exception as e:
                        st.error(f"Error formatting results: {str(e)}")
                        st.json(results)  # Fallback to raw JSON display

def render_chat_interface(session_id: int, session_type: str = "document", current_image=None):
    """Shared chat interface component for both document and image chat"""
    # Create a main container for all chat components
    main_container = st.container()
    
    # Create containers but don't write to them yet
    with main_container:
        messages_area = st.container()
        # Add some space between messages and input
        st.markdown("<br>" * 2, unsafe_allow_html=True)
        # Processing and input at the bottom
        input_area = st.container()
        
        # Use columns to create a fixed bottom area
        col1, col2 = st.columns([6, 1])
        with col1:
            processing_placeholder = st.empty()
        with col2:
            # Optional: Add any controls like clear chat, etc.
            if st.button("Clear Chat"):
                st.session_state.message_history[session_id] = []
                st.rerun()

    # Fetch and display messages in the messages area
    with messages_area:
        if session_id not in st.session_state.message_history:
            messages_response = requests.get(
                f"{API_BASE_URL}/api/v1/chat-sessions/{session_id}/messages"
            )
            if messages_response.status_code == 200:
                st.session_state.message_history[session_id] = messages_response.json()["messages"]

        # Display messages
        for msg in st.session_state.message_history.get(session_id, []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                st.caption(f":clock2: {msg['timestamp']}")

    # Handle input and processing at the bottom
    with input_area:
        if prompt := st.chat_input("Type your message...", key=f"chat_input_{session_id}"):
            # Show user message immediately
            with messages_area:
                with st.chat_message("user"):
                    st.markdown(prompt)
                    st.caption(":clock2: Just now")
            
            # Add to session history immediately
            st.session_state.message_history[session_id] = st.session_state.message_history.get(session_id, []) + [
                {"role": "user", "content": prompt, "timestamp": "Just now"}
            ]

            # Show loading indicator
            with processing_placeholder:
                with st.spinner("Processing..."):
                    message_data = {
                        "content": prompt,
                        "additional_data": {
                            "image": base64.b64encode(current_image.getvalue()).decode()
                        } if session_type == "image" and current_image else None
                    }
                    
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/api/v1/chat-sessions/{session_id}/messages",
                            json=message_data
                        )
                        
                        if response.status_code == 200:
                            try:
                                response_data = response.json()
                                assistant_response = response_data["response"]
                                with messages_area:
                                    with st.chat_message("assistant"):
                                        st.markdown(assistant_response)
                                        st.caption(":clock2: Just now")
                                
                                # Add to history
                                st.session_state.message_history[session_id].append({
                                    "role": "assistant",
                                    "content": assistant_response,
                                    "timestamp": "Just now"
                                })
                            except (ValueError, KeyError) as e:
                                st.error(f"Invalid response format: {str(e)}")
                        else:
                            try:
                                error_detail = response.json().get('detail', 'Unknown error')
                            except ValueError:
                                error_detail = response.text or 'Unknown error'
                            st.error(f"Error {response.status_code}: {error_detail}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Request failed: {str(e)}")

            # Clear the processing indicator
            processing_placeholder.empty()

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
                        "name": "New Chat Session",  # Generic initial name
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
                    "name": "New Image Chat Session",  # Generic initial name
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
    
    # Add error handling around each page render
    try:
        if st.session_state.stage == "projects":
            project_page()
        elif st.session_state.stage == "upload":
            upload_page()
        elif st.session_state.stage == "analyze":
            analyze_page()
        elif st.session_state.stage == "chat":
            chat_page()
        elif st.session_state.stage == "chat_image":
            chat_with_image_page()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()