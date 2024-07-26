import streamlit as st
import ollama
import fitz
import os
import json
import pandas as pd
import pytesseract
from PIL import Image
import io
from ollama_setup import get_ollama_response

import time

start_time = time.time()

def extract_text_from_images(images) -> str:
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    return text

def extract_data(text: str, instructions: list, model) -> dict:
    response = get_ollama_response(text, instructions, model)
    return response;


st.set_page_config(page_title="Data Extraction with Local LLMs", page_icon="🔍")
st.title('Run Open source LLMs Locally')
st.markdown('This is a simple Streamlit app that allows you to run Open source LLMs locally. ')

# Initialize session state for instructions
if "instructions" not in st.session_state:
    st.session_state["instructions"] = []

# Section for adding extraction instructions
st.subheader("Extraction Instructions")
st.markdown(
    "Add instructions for extracting information from the document. The title should be unique."
)

if "model" not in st.session_state:
    st.session_state['model'] = ''

models = [model['name'] for model in ollama.list()['models']]
st.session_state['model'] = st.selectbox('Select Model', models)

# Section for adding extraction instructions
st.subheader("Extraction Instructions")
st.markdown(
    "Add instructions for extracting information from the document. The title should be unique."
)

with st.form(key="instruction_form"):
    title = st.text_input("Title")
    data_type = st.selectbox("Data Type", ["string", "number"])
    description = st.text_area("Description")
    add_button = st.form_submit_button("Add")

    if add_button and title and data_type and description:
        st.session_state["instructions"].append(
            {"title": title, "data_type": data_type, "description": description}
        )

# Define a CSS style for the card
card_style = """
<style>
.card {
    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
    transition: 0.3s;
    padding: 10px;
    margin-bottom: 10px; /* Space between cards */
}
.card:hover {
    box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
}
</style>
"""

st.markdown(card_style, unsafe_allow_html=True)

if st.session_state["instructions"]:
    st.subheader("Added Instructions")
    for instruction in st.session_state["instructions"]:
        st.markdown(
            f"<div class='card' style='display: flex; align-items: center;'><div style='flex-grow: 1;' title='{instruction['description']} ({instruction['data_type']})'>{instruction['title']}</div></div>",
            unsafe_allow_html=True,
        )

# File uploader and submit button
with st.form(key="resume_form"):
    files = st.file_uploader(
        "Add file(s) in PDF or CSV format:",
        type=["pdf", "csv"],
        accept_multiple_files=True,
    )
    submitted = st.form_submit_button("Submit")

if files:
    extracted_texts = []
    for file in files:
        if file.type == "application/pdf":
            pdf = fitz.open(stream=file.read(), filetype="pdf")
            text = ""
            for page in pdf:
                text += page.get_text()
                images = page.get_images(full=True)
                for img in images:
                    xref = img[0]
                    base_image = pdf.extract_image(xref)
                    image_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(image_bytes))
                    text += extract_text_from_images([image])
            extracted_texts.append(text)
        elif file.type == "text/csv":
            df = pd.read_csv(file)
            for index, row in df.iterrows():
                name = row["Name"]
                resume = row["Resume"]
                extracted_texts.append(f"{name}\n{resume}")

    responses = []
    for text in extracted_texts:
        file_data = extract_data(text, st.session_state["instructions"], st.session_state['model'])
        responses.append(file_data)

    # Convert responses to CSV
    csv_data = []
    for idx, data in enumerate(responses):
        if data:
            row = {}
            for instruction in st.session_state["instructions"]:
                title = instruction["title"]
                formatted_title = title.lower().replace(" ", "_")
                row[title] = data.get(formatted_title)
            csv_data.append(row)

    # Display summary of the CSV data
    if csv_data:
        st.subheader("CSV Summary")
        st.write(pd.DataFrame(csv_data))
    else:
        st.markdown("No data extracted")

end_time = time.time()
execution_time = end_time - start_time
st.write(f"Execution time: {execution_time:.2f} seconds")
