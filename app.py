import streamlit as st
import tempfile
from pathlib import Path
from PIL import Image
import pandas as pd
import torch
from transformers import MllamaForConditionalGeneration, AutoProcessor, AutoModelForCausalLM, AutoTokenizer
import json
from utils import process_files

SYSTEM_INSTRUCTION = """You are an image interpreter. Your task is to analyze the provided image, identify key elements, and provide a clear interpretation. Based on your analysis, generate a detailed summary that includes an explanation of what you see, any notable features, and potential implications or insights. Ensure your output is structured and easily understandable."""

@st.cache_resource
def load_llama_vision():
    model = MllamaForConditionalGeneration.from_pretrained(
        "meta-llama/Llama-3.2-11B-Vision-Instruct",
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained("meta-llama/Llama-3.2-11B-Vision-Instruct")
    return model, processor

@st.cache_resource
def load_llama():
    model = AutoModelForCausalLM.from_pretrained("meta-llama/Meta-Llama-3.1-8B-Instruct")
    tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3.1-8B-Instruct")
    return model, tokenizer

def extract_assistant_reply(input_string):
    start_tag = "<|start_header_id|>assistant<|end_header_id|>"
    start_index = input_string.find(start_tag)
    if start_index == -1:
        return "Assistant's reply not found."
    start_index += len(start_tag)
    assistant_reply = input_string[start_index:].strip()
    return assistant_reply

def process_image(image, text_input, model, processor, history):
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": f"Image context: {history}\nNew question: {text_input}"}
        ]}
    ]
    input_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(image, input_text, return_tensors="pt").to(model.device)
    
    output = model.generate(**inputs, max_new_tokens=500)
    markdown_text = processor.decode(output[0])
    
    response = extract_assistant_reply(markdown_text)
    # html_output = markdown.markdown(response)
    # return html_output
    
    return response
    

def process_document(text, instructions, model, tokenizer):
    instruction_text = ", ".join([f"{i['title']} ({i['data_type']}): {i['description']}" for i in instructions])
    prompt = f"""You are a professional Data Analyst. Extract the following information from the document: {instruction_text}
    If a particular field is not found in the document, return 'not found' for that field.
    Your response should be only the specified fields and information extracted from the document in JSON format.
    Document: {text}
    Extracted information (JSON format):"""
    
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    outputs = model.generate(**inputs, max_new_tokens=200)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    try:
        json_response = json.loads(response)
    except json.JSONDecodeError:
        json_response = {"error": "Failed to parse JSON", "raw_response": response}
    
    return json_response

def image_processor(vision_model, vision_processor):
    st.title("Image Processor")
    st.write("Upload an image and ask questions about it. You can continue the conversation until you upload a new image.")
    
    if 'image' not in st.session_state:
        st.session_state.image = None
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    image_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    
    if image_file:
        new_image = Image.open(image_file).convert("RGB")
        if st.session_state.image != new_image:
            st.session_state.image = new_image
            st.session_state.conversation_history = []
    
    if st.session_state.image:
        st.image(st.session_state.image, caption="Uploaded Image", use_column_width=True)
        
        prompt = st.text_input("Ask a question about the image:")
        
        if prompt:
            with st.spinner("Processing..."):
                response = process_image(st.session_state.image, prompt, vision_model, vision_processor, 
                                         "\n".join(st.session_state.conversation_history))
            
            st.session_state.conversation_history.append(f"Q: {prompt}\nA: {response}")
            
            with st.expander("Conversation History", expanded=True):
                for entry in st.session_state.conversation_history:
                    st.markdown(entry, unsafe_allow_html=True)
                    st.write("---")

def file_processor(text_model, text_tokenizer):
    st.title("File Processor")
    
    uploaded_files = st.file_uploader("Upload supported files", accept_multiple_files=True, type=["pdf", "xlsx", "csv", "tsv", "docx", "doc", "txt"])
    
    if "instructions" not in st.session_state:
        st.session_state["instructions"] = []

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

    if st.session_state["instructions"]:
        st.markdown("### Added Instructions")
        for instruction in st.session_state["instructions"]:
            with st.expander(instruction["title"]):
                st.markdown(f"{instruction['description']} (Type: {instruction['data_type']})")
    
    if st.button("Generate Output"):
        if uploaded_files and st.session_state["instructions"]:
            with st.spinner("Processing files..."):
                results = []
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as temp_file:
                        temp_file.write(uploaded_file.getvalue())
                        temp_file_path = Path(temp_file.name)
                    
                    extracted_text = process_files(temp_file_path)
                    processed_data = process_document(extracted_text, st.session_state["instructions"], text_model, text_tokenizer)
                    results.append({
                        "filename": uploaded_file.name,
                        "extracted_data": processed_data
                    })
                    
                    temp_file_path.unlink()  # Delete the temporary file
                
                df = pd.DataFrame([r['extracted_data'] for r in results])
                df['filename'] = [r['filename'] for r in results]
                
                st.write("Processed Data:")
                st.dataframe(df)
                
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download data as CSV",
                    data=csv,
                    file_name="processed_data.csv",
                    mime="text/csv",
                )

def main():
    vision_model, vision_processor = load_llama_vision()
    text_model, text_tokenizer = load_llama()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Image Processor", "File Processor"])

    if page == "Image Processor":
        image_processor(vision_model, vision_processor)
    elif page == "File Processor":
        file_processor(text_model, text_tokenizer)

if __name__ == "__main__":
    main()