import tempfile
from pathlib import Path
from typing import List
import streamlit as st

def save_uploaded_files(uploaded_files: List[st.UploadedFile]) -> List[Path]:
    saved_files = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        for uploaded_file in uploaded_files:
            file_path = temp_path / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            saved_files.append(file_path)
    return saved_files
