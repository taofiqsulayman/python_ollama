import streamlit as st
import tempfile
from pathlib import Path
import pandas as pd
from ollama_setup import run_inference_on_document
from utils import process_files
import time
from dataclasses import asdict
from streamlit_keycloak import login


# Authentication with Keycloak
auth_status, auth_user = login(
    keycloak_url="http://localhost:8080/auth",
    realm_name="text-extraction",
    client_id="text-extraction-realm"
)
http://localhost:8080/realms/text-extraction/account

# Show login screen if not authenticated
if not auth_status:
    st.warning("Please log in to access this page.")
    st.stop()

st.set_page_config(layout="wide", page_title="File Processor", page_icon="📄")
st.title("File Processor")


def extract_data_from_document(text: str, instructions: list) -> dict:
    response = run_inference_on_document(text, instructions)
    return response


def reset_state():
    st.session_state["stage"] = "upload"
    st.session_state["extracted_files"] = []
    st.session_state["instructions"] = []
    st.session_state["uploaded_files"] = []

if "stage" not in st.session_state:
    reset_state()

def go_back(target_stage):
    if target_stage == "upload":
        reset_state()
    elif target_stage == "show_text":
        st.session_state["stage"] = "show_text"
        st.session_state["instructions"] = [] 
    elif target_stage == "add_instructions":
        st.session_state["stage"] = "add_instructions"

# Two-column layout
left_col, right_col = st.columns(2)

if st.session_state["stage"] == "upload":
    with left_col:
        st.markdown("### Upload Files")
        uploaded_files = st.file_uploader("Upload a supported file", accept_multiple_files=True, type=["pdf", "xlsx", "csv", "tsv", "docx", "doc", "txt", "jpg", "jpeg", "png"])

        if st.button("Extract Text", key="extract_text_btn") and uploaded_files:
            st.session_state["uploaded_files"] = uploaded_files
            extracted_files = []
            with st.spinner("Extracting text..."):
                with tempfile.TemporaryDirectory() as temp_dir:
                    input_dir = Path(temp_dir) / "input"
                    input_dir.mkdir()

                    for uploaded_file in uploaded_files:
                        # Save uploaded file to temporary directory
                        input_file = input_dir / uploaded_file.name
                        with open(input_file, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        extracted_text = process_files(input_file)
                        extracted_files.append({"file_name": uploaded_file.name, "content": extracted_text})

                st.session_state["extracted_files"] = extracted_files
                st.session_state["stage"] = "show_text"

if st.session_state["stage"] == "show_text":
    with left_col:
        st.markdown("view the extracted text from the uploaded files")

    with right_col:
        st.markdown("### Extracted Text")
        for idx, file_data in enumerate(st.session_state["extracted_files"]):
            file_name = file_data["file_name"]
            content = file_data["content"]
            with st.expander(f"{file_name} - Extracted Text"):
                st.markdown(content)
                st.download_button(
                    "Download Extracted Text",
                    content,
                    file_name=f"{Path(file_name).stem}_extracted.md"
                )

        if st.button("Perform AI Inferencing", key="perform_ai_btn"):
            st.session_state["stage"] = "add_instructions"

    with left_col:
        if st.button("Back", key="back_to_upload_btn"):
            go_back("upload")

if st.session_state["stage"] == "add_instructions":
    with left_col:
        st.markdown("### Extraction Instructions")
        st.markdown("Add instructions for extracting information from the document. The title should be unique.")
        
        with st.form(key="instruction_form"):
            title = st.text_input("Title")
            data_type = st.selectbox("Data Type", ["string", "number"])
            description = st.text_area("Description")
            add_button = st.form_submit_button("Add")

            if add_button and title and data_type and description:
                st.session_state["instructions"].append(
                    {"title": title, "data_type": data_type, "description": description}
                )

    with right_col:
        st.markdown("### View Instructions")
        if st.session_state["instructions"]:
            st.markdown("### Added Instructions")
            for instruction in st.session_state["instructions"]:
                with st.expander(instruction["title"]):
                    st.markdown(instruction["description"])
                    st.markdown(f"Data Type: {instruction['data_type']}")

        if st.button("Analyze", key="analyze_btn"):
            st.session_state["stage"] = "analyze"

    with left_col:
        if st.button("Back", key="back_to_show_text_btn"):
            go_back("show_text")

if st.session_state["stage"] == "analyze":
    with left_col:
        st.markdown("### Analyzing Extracted Data")

    with right_col:
        st.markdown("### Output")
        start_time = time.time()
        responses = []
        if st.session_state["extracted_files"] and st.session_state["instructions"]:
            with st.spinner("Analyzing extracted text..."):
                for file_data in st.session_state["extracted_files"]:
                    file_name = file_data["file_name"]
                    content = file_data["content"]
                    file_response = extract_data_from_document(content, st.session_state["instructions"])
                    responses.append({"file_name": file_name, "data": file_response})
                
                csv_data = []
                for response in responses:
                    row = {"File Name": response["file_name"]}
                    data = response["data"]
                    if data:
                        for instruction in st.session_state["instructions"]:
                            title = instruction["title"]
                            formatted_title = title.lower().replace(" ", "_")
                            row[title] = data.get(formatted_title)
                    csv_data.append(row)

                end_time = time.time()

                if csv_data:
                    with st.expander("Output"):
                        st.write("Time taken: {:.2f} seconds".format(end_time - start_time))
                        st.write(pd.DataFrame(csv_data))
                else:
                    st.warning("No data extracted from the files.")
                    st.write("Time taken: {:.2f} seconds".format(end_time - start_time))

    with left_col:
        if st.button("Back", key="back_to_add_instructions_btn"):
            go_back("add_instructions")
