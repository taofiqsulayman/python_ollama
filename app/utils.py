import os
import subprocess
import pandas as pd
from vllm import LLM, SamplingParams
from doctr.models import ocr_predictor
from doctr.io import DocumentFile

import fitz  # PyMuPDF
import pymupdf4llm
from docx import Document

from huggingface_hub import login

hf_api_token = os.getenv("HF_TOKEN")
login(hf_api_token)

os.environ['USE_TORCH'] = '1'

image_llm = LLM(
        model="microsoft/Phi-3.5-vision-instruct",
        trust_remote_code=True,
        max_num_seqs=5,
        mm_processor_kwargs={"num_crops": 16},
        dtype="half",
    )
# image_llm = LLM(model="meta-llama/Llama-3.2-11B-Vision-Instruct")

file_llm = LLM(
    model="meta-llama/Llama-3.1-8B-Instruct", 
    trust_remote_code=True, 
    dtype="half",
)
# file_llm = LLM(model="meta-llama/Llama-3.2-3B-Instruct")

# Load a pre-trained model for ocr
ocr_model = ocr_predictor(pretrained=True)

def extract_json_from_response(response):
    # Extract the "response" field from the response object
    response_text = response.get("response", "")

    # Find the starting position of the JSON-like string in the response
    start_pos = response_text.find("{")
    # Find the ending position of the JSON-like string in the response
    end_pos = response_text.rfind("}") + 1

    # Extract the JSON-like string from the response text
    json_like_str = response_text[start_pos:end_pos]

    # Convert the JSON-like string to a dictionary
    try:
        extracted_info = eval(json_like_str)
    except SyntaxError as e:
        print(f"Error parsing JSON-like string: {e}")
        extracted_info = {}

    return extracted_info

def get_files_response(data: str, instructions: list):
    # Ensure unique titles in a case-insensitive manner
    seen_titles = set()
    unique_instructions = []
    for instruction in instructions:
        title = instruction["title"].strip().lower().replace(" ", "_")
        if title not in seen_titles:
            seen_titles.add(title)
            unique_instructions.append(
                {
                    "title": title,
                    "data_type": instruction["data_type"],
                    "description": instruction["description"],
                }
            )

    response_format = (
        "{\n"
        + ",\n".join([f'  "{instr["title"]}": ""' for instr in unique_instructions])
        + "\n}"
    )

    prompt = f"""You are a professional Data Analyst / Data Miner and your job is to extract detailed information from documents.
    If a particular field is not found in the document, please return 'not found' for that field. Return the response as a JSON based on the instructions below;
    Here are the fields to extract: {unique_instructions},
    Also, return response in this format: {response_format}
    The document is as follows: {data}
    """
    
    
    sampling_params = SamplingParams(temperature=0.8, top_p=0.95)
    response = file_llm.generate(
        prompt, sampling_params
    )
    refined_response = extract_json_from_response(response.outputs[0].text)

    return refined_response

def get_images_response(image, text_input: str):
    # Load the image using PIL.Image
    # image = Image.open(image_file)
        
    user_prompt = '<|user|>\n'
    assistant_prompt = '<|assistant|>\n'
    prompt_suffix = "<|end|>\n"
    
    prompt = prompt = f"{user_prompt}<|image_1|>\n{text_input}{prompt_suffix}{assistant_prompt}"

    # Single prompt inference
    output = image_llm.generate({
        "prompt": prompt,
        "multi_modal_data": {"image": image},
    })

    return output.outputs[0].text

def process_doctr_output(doctr_output):
    text = ""
    for page in doctr_output.pages:
        for block in page.blocks:
            for line in block.lines:
                line_text = " ".join([word.value for word in line.words])
                text += line_text + " "
    return text

def extract_text_with_ocr(image_file):
    image = DocumentFile.from_images(image_file)
    text = ocr_model(image)
    extracted_text = process_doctr_output(text)
    return extracted_text

def process_pdf(file_path):
    extracted_text = ''
    doc = fitz.open(file_path)
    
    for i in range(doc.page_count):
        page = doc.load_page(i)
        check_text = page.get_text("text")
        if not check_text.strip():
            image_file = page.get_pixmap()
            extracted_text += extract_text_with_ocr(image_file)
        else:
            extracted_text += pymupdf4llm.to_markdown(file_path, pages=[i])
    return extracted_text

def convert_table_to_markdown(df):
    """Convert pandas DataFrame to Markdown table."""
    return df.to_markdown(index=False) + "\n\n"

def process_csv_xlsx_tsv(file_path):
    """Process CSV, XLSX, and TSV files and convert to Markdown."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        df = pd.read_csv(file_path)
    elif ext == ".tsv":
        df = pd.read_csv(file_path, sep="\t")
    elif ext == ".xlsx":
        df = pd.read_excel(file_path)

    return convert_table_to_markdown(df)

def process_word_docs(file_path):
    if file_path.suffix == ".doc":
        # Convert .doc to plain text using antiword
        result = subprocess.run(["antiword", file_path], capture_output=True, text=True)
        plain_text = result.stdout
    elif file_path.suffix == ".docx":
        # Load .docx file
        doc = Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        plain_text = "\n".join(full_text)
    else:
        raise ValueError("Unsupported file format. Please use a .doc or .docx file.")

    return plain_text

def process_txt_file(file_path):
    with open(file_path, "r") as f:
        text = f.read()
    return text

def process_files(file_path):

    if file_path.suffix in [".pdf", ".PDF"]:
        return process_pdf(file_path)
    elif file_path.suffix in [".csv", ".CSV", ".tsv", ".TSV", ".xlsx", ".XLSX"]:
        return process_csv_xlsx_tsv(file_path)
    elif file_path.suffix in [".doc", ".docx"]:
        return process_word_docs(file_path)
    elif file_path.suffix in [".txt", ".TXT"]:
        return process_txt_file(file_path)
    else:
        raise ValueError("Unsupported file format. Please use a supported file format.")