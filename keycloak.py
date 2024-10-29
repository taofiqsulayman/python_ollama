import os
from urllib.parse import urlencode

import streamlit as st
from streamlit.runtime import Runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx

from streamlit_keycloak import login
import streamlit as st
import tempfile
from pathlib import Path
import pandas as pd
from db_operations import create_table, insert_employee, fetch_employees

create_table()
# insert_employee(1, 'John Doe', 30, 50000)
# insert_employee(2, 'Jane Smith', 28, 60000)

# Fetch and print all employees
# fetch_employees()
st.title("File Extractions")


def _get_session_id():
    context = get_script_run_ctx()
    if not context:
        return
    return context.session_id


def _get_current_request():
    session_id = _get_session_id()
    if not session_id:
        return None
    runtime = Runtime._instance
    if not runtime:
        return
    client = runtime.get_client(session_id)
    if not client:
        return
    return client.request


# def get_web_origin():
#     request = _get_current_request()
#     return request.headers["Origin"] if request else os.getenv("WEB_BASE", "")


keycloak_endpoint = "http://localhost:8080/"
keycloak_realm = "myrealm"
st.markdown("""
        <style>
               .st-emotion-cache-13ln4jf {
                
                    max-width: 70rem;
                }
        </style>
        """, unsafe_allow_html=True)

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


# if not st.session_state.get("keycloak_user_info"):
    # keycloak = login(
    #     url=keycloak_endpoint,
    #     realm=keycloak_realm,
    #     client_id="textextraction",
    #     init_options={
    #       "checkLoginIframe": False
    #       },
    # )
# if keycloak.authenticated:
            # Two-column layoutSS
left_col, right_col = st.columns(2)

if st.session_state["stage"] == "upload":
    with left_col:
        st.markdown("### Upload Files")
        uploaded_files = st.file_uploader("Upload supported files", accept_multiple_files=True,
                                            type=["pdf", "xlsx", "csv", "tsv", "docx", "doc", "txt", "jpg", "jpeg", "png"])

    if st.button("Extract Text", key="extract_text_btn") and uploaded_files:
        st.session_state["uploaded_files"] = uploaded_files
        extracted_files = []
        with st.spinner("Extracting text..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                input_dir = Path(temp_dir) / "input"
                input_dir.mkdir()

                # Process uploaded files
                for uploaded_file in uploaded_files:
                    input_file = input_dir / uploaded_file.name
                    with open(input_file, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    extracted_text = process_files(input_file)
                    extracted_files.append({"file_name": uploaded_file.name, "content": extracted_text})

            st.session_state["extracted_files"] = extracted_files
            st.session_state["stage"] = "show_text"

if st.session_state["stage"] == "show_text":
    with left_col:
        st.markdown("View the extracted text from the uploaded files")

    with right_col:
        st.markdown("### Extracted Text")
        for idx, file_data in enumerate(st.session_state["extracted_files"]):
            file_name = file_data["file_name"]
            content = file_data["content"]
            with st.expander(f"{file_name} - Extracted Text"):
                st.markdown(content)
                st.download_button("Download Extracted Text", content, file_name=f"{Path(file_name).stem}_extracted.md")

        if st.button("Perform AI Inferencing", key="perform_ai_btn"):
            st.session_state["stage"] = "add_instructions"

    with left_col:
        if st.button("Back", key="back_to_upload_btn"):
            go_back("upload")

if st.session_state["stage"] == "add_instructions":
    with left_col:
        st.markdown("### Extraction Instructions")
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
                    st.write(f"Time taken: {end_time - start_time:.2f} seconds")
                    st.write(pd.DataFrame(csv_data))
            else:
                st.warning("No data extracted from the files.")
                st.write(f"Time taken: {end_time - start_time:.2f} seconds")

    with left_col:
        if st.button("Back", key="back_to_add_instructions_btn"):
            go_back("add_instructions")



if st.session_state.get("keycloak_user_info"):
    params = urlencode(
        {
            "post_logout_redirect_uri": get_web_origin(),
            "id_token_hint": st.session_state.keycloak_id_token,
        }
    )
    st.json(st.session_state.keycloak_user_info)
    st.markdown(
        f'Switch account by <a target="_self" href="{keycloak_endpoint}/realms/{keycloak_realm}/protocol/openid-connect/logout?{params}">Logout</a>',
        unsafe_allow_html=True,
    )





