import streamlit as st
from PIL import Image
import time
import tempfile
from pathlib import Path
import os
from huggingface_hub import login
from utils import get_images_response 
# get_files_response, process_files

hf_api_token = os.getenv("HF_TOKEN")
login(hf_api_token)




# Page 1: Image Processor
def image_processor():
    st.title("Image Processor")
    st.write("Upload an image and enter a prompt to generate output.")
    
    # Upload image
    image_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    prompt = st.text_area("Enter your prompt here:")
    
    if st.button("Generate Output"):
        start_time = time.time()
        if image_file and prompt:
            # Load image
            # image = Image.open(image_file)
            image = Image.fromarray(image_file).convert("RGB")

            st.image(image, caption="Uploaded Image", use_column_width=True)

            # Generate output
            response = get_images_response(image, prompt)
            
            end_time = time.time()
            with st.expander("Output"):
                st.write("Time taken: {:.2f} seconds".format(end_time - start_time))
                st.write(response)
        

# Page 2: File Processor
def file_processor():
    st.title("File Processor")
    
    uploaded_files = st.file_uploader("Upload a supported file", accept_multiple_files=True, type=["pdf", "xlsx", "csv", "tsv", "docx", "doc", "txt"])
    
    if "instructions" not in st.session_state:
        st.session_state["instructions"] = []

    # Section for adding extraction instructions
    st.markdown("## Extraction Instructions")
    st.markdown(
        "Add instructions for extracting information from the document. The title should be unique."
    )

    # with st.form(key="instruction_form"):
    #     title = st.text_input("Title")
    #     data_type = st.selectbox("Data Type", ["string", "number"])
    #     description = st.text_area("Description")
    #     add_button = st.form_submit_button("Add")

    #     if add_button and title and data_type and description:
    #         st.session_state["instructions"].append(
    #             {"title": title, "data_type": data_type, "description": description}
    #         )

    # if st.session_state["instructions"]:
    #     st.markdown("### Added Instructions")
    #     for instruction in st.session_state["instructions"]:
    #         with st.expander(instruction["title"]):
    #             st.markdown(instruction["description"] + " data type:" + " (" + instruction["data_type"] + ")")
    
    # if st.button("Generate Output"):
    #     start_time = time.time()                    
    #     if uploaded_files and st.session_state["instructions"]:
    #         with st.spinner("Processing files..."):
    #             start_time = time.time()
    #             extracted_texts = []

    #             # Create temporary directory for input
    #             with tempfile.TemporaryDirectory() as temp_dir:
    #                 input_dir = Path(temp_dir) / "input"
    #                 input_dir.mkdir()

    #                 for uploaded_file in st.session_state.uploaded_files:
    #                     # Save uploaded file to temporary directory
    #                     input_file = input_dir / uploaded_file.name
    #                     with open(input_file, "wb") as f:
    #                         f.write(uploaded_file.getbuffer())

    #                     extracted_text = process_files(input_file)
    #                     extracted_texts.append(extracted_text)
                
    #             responses = []
    #             for text in extracted_texts:
    #                 file_data = get_files_response(text, st.session_state["instructions"])
    #                 responses.append(file_data)
                    
    #             # Convert responses to CSV
    #             csv_data = []
    #             for idx, data in enumerate(responses):
    #                 if data:
    #                     row = {}
    #                     for instruction in st.session_state["instructions"]:
    #                         title = instruction["title"]
    #                         formatted_title = title.lower().replace(" ", "_")
    #                         row[title] = data.get(formatted_title)
    #                     csv_data.append(row)

    #             end_time = time.time()
    #             st.write("Time taken: {:.2f} seconds".format(end_time - start_time))
    #             st.markdown(csv_data)

# Main App
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Image Processor", "File Processor"])

if page == "Image Processor":
    image_processor()
elif page == "File Processor":
    file_processor()
