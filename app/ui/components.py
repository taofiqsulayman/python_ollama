import streamlit as st
from ui.state import SessionState
from typing import List, Dict, Any
from config.settings import settings
from pathlib import Path
import pandas as pd

def render_sidebar():
    with st.sidebar:
        st.title("File Processor")
        
        if st.session_state.get("username"):
            st.markdown(f"### Welcome, {st.session_state.username}")
            st.markdown(f"Role: {st.session_state.user_role}")
            
            if st.button("Logout", key="logout_btn"):
                SessionState.reset()
                st.experimental_rerun()
        
        st.markdown("---")
        st.markdown("### Navigation")
        
        stages = ["upload", "show_text"]
        if st.session_state.get("user_role") == "advanced":
            stages.extend(["add_instructions", "analyze"])
        
        for stage in stages:
            if st.button(stage.replace("_", " ").title(), key=f"nav_{stage}"):
                SessionState.update({"stage": stage})
                st.experimental_rerun()


def render_file_uploader():
    return st.file_uploader(
        "Upload supported files",
        accept_multiple_files=True,
        type=list(sum(settings.SUPPORTED_EXTENSIONS.values(), []))
    )


def show_extracted_text(extracted_files: List[Dict[str, Any]]):
    for file_data in extracted_files:
        with st.expander(f"{file_data['file_name']} - Extracted Text"):
            st.markdown(file_data["content"])
            st.download_button(
                "Download Extracted Text",
                file_data["content"],
                file_name=f"{Path(file_data['file_name']).stem}_extracted.md"
            )

def show_analysis_results(
    responses: List[Dict[str, Any]],
    instructions: List[Dict[str, Any]],
    processing_time: float
):
    df_data = []
    for response in responses:
        row = {"File Name": response["file_name"]}
        data = response["data"]
        if data:
            for instruction in instructions:
                title = instruction["title"]
                formatted_title = title.lower().replace(" ", "_")
                row[title] = data.get(formatted_title)
        df_data.append(row)
    
    if df_data:
        st.markdown("### Results")
        st.markdown(f"Processing time: {processing_time:.2f} seconds")
        st.dataframe(pd.DataFrame(df_data))
        
        csv = pd.DataFrame(df_data).to_csv(index=False)
        st.download_button(
            "Download Results as CSV",
            csv,
            file_name="analysis_results.csv"
        )
            
def render_instruction_form():
    with st.form("instruction_form"):
        title = st.text_input("Title")
        data_type = st.selectbox("Data Type", ["string", "number"])
        description = st.text_area("Description")
        submitted = st.form_submit_button("Add Instruction")
    
    if submitted and title and description:
        return {
            "title": title,
            "data_type": data_type,
            "description": description
        }
    return None