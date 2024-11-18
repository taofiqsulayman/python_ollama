import streamlit as st
import requests
import json
from PIL import Image
import base64
import pandas as pd

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
    key = "file_uploader_" + str(st.session_state.get('upload_counter', 0))
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        accept_multiple_files=True,
        type=["txt", "pdf", "docx"],
        key=key
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
                    # Increment counter to reset file uploader
                    st.session_state.upload_counter = st.session_state.get('upload_counter', 0) + 1
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
                    
                    # Create DataFrame from nested results
                    try:
                        # Initialize data dictionary
                        data = {}
                        confidence_data = {}
                        sources_data = {}
                        
                        # Extract data from nested structure
                        for field, field_data in results.items():
                            if isinstance(field_data, list):
                                # Handle array of results
                                for item in field_data:
                                    data[field] = item.get("value")
                                    confidence_data[field] = item.get("confidence", "unknown")
                                    sources_data[field] = item.get("source", "unknown")
                            else:
                                # Handle single result
                                data[field] = field_data.get("value")
                                confidence_data[field] = field_data.get("confidence", "unknown")
                                sources_data[field] = field_data.get("source", "unknown")
                        
                        # Create DataFrames
                        results_df = pd.DataFrame([data])
                        confidence_df = pd.DataFrame([confidence_data])
                        sources_df = pd.DataFrame([sources_data])
                        
                        # Display results
                        st.markdown("#### Extracted Values")
                        st.dataframe(
                            results_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Display confidence levels
                        st.markdown("#### Confidence Levels")
                        st.dataframe(
                            confidence_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Display sources
                        st.markdown("#### Sources")
                        st.dataframe(
                            sources_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Raw results in expandable section
                        with st.expander("🔍 View Raw Results"):
                            st.json(results)
                        
                        # Download options
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                "📥 Download CSV",
                                results_df.to_csv(index=False),
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
                            
                    except Exception as e:
                        st.error(f"Error formatting results: {str(e)}")
                        st.json(results)  # Fallback to raw JSON display

def chat_page():
    """Document chat interface"""
    st.title("💬 Chat with Documents")
    
    if "current_project_id" not in st.session_state:
        st.session_state.stage = "projects"
        st.rerun()
    
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Get chat history from API
    history = api_request(
        "GET", 
        f"projects/{st.session_state.current_project_id}/chat-history",
        params={"chat_type": "document"}  # Filter by document type
    )
    
    if history and "history" in history:
        st.session_state.chat_messages = [
            {"role": "user", "content": msg["prompt"]}
            for msg in history["history"]
        ] + [
            {"role": "assistant", "content": msg["response"]}
            for msg in history["history"]
        ]

    # Show available documents
    st.sidebar.markdown("### Available Documents")
    files = api_request("GET", f"projects/{st.session_state.current_project_id}/files")
    if not files:
        st.info("⚠️ No documents available. Please upload some files first.")
        return
    
    # Display document list in sidebar
    doc_names = [f"📄 {f['file_name']}" for f in files]
    st.sidebar.write("\n".join(doc_names))
    
    # Chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about your documents..."):
        # Show user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Add to history
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # Get AI response
        with st.spinner("Thinking..."):
            response = api_request(
                "POST",
                f"projects/{st.session_state.current_project_id}/chat",
                json={
                    "prompt": prompt,
                    "chat_type": "document"
                }
            )
            
            if response and "response" in response:
                # Show AI response
                with st.chat_message("assistant"):
                    st.markdown(response["response"])
                # Add to history
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": response["response"]}
                )
                st.rerun()

def chat_with_image_page():
    """Image chat interface"""
    st.title("🖼️ Chat with Image")
    
    if "current_project_id" not in st.session_state:
        st.session_state.stage = "projects"
        st.rerun()
    
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Get chat history from API filtered by image type
    history = api_request(
        "GET", 
        f"projects/{st.session_state.current_project_id}/chat-history",
        params={"chat_type": "image"}  # Filter by image type
    )
    
    if history and "history" in history:
        st.session_state.chat_messages = [
            {"role": "user", "content": msg["prompt"]}
            for msg in history["history"]
        ] + [
            {"role": "assistant", "content": msg["response"]}
            for msg in history["history"]
        ]

    # Image upload
    uploaded_file = st.file_uploader(
        "Upload an image to discuss",
        type=["png", "jpg", "jpeg"],
        help="Supported formats: PNG, JPG, JPEG"
    )
    
    if uploaded_file:
        # Display image in sidebar
        st.sidebar.markdown("### Current Image")
        image = Image.open(uploaded_file)
        st.sidebar.image(image, use_column_width=True)
        
        # Main chat area
        chat_container = st.container()
        
        # Display chat history
        with chat_container:
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask about the image..."):
            # Show user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Add to history
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            
            # Get AI response
            with st.spinner("Analyzing image..."):
                response = api_request(
                    "POST",
                    f"projects/{st.session_state.current_project_id}/chat",
                    json={
                        "prompt": prompt,
                        "chat_type": "image",
                        "image_data": base64.b64encode(uploaded_file.getvalue()).decode()
                    }
                )
                
                if response and "response" in response:
                    # Show AI response
                    with st.chat_message("assistant"):
                        st.markdown(response["response"])
                    # Add to history
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": response["response"]}
                    )
                    st.rerun()
    else:
        st.info("⚠️ Please upload an image to start chatting")

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