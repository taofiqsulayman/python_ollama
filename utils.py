import os
import subprocess
import pandas as pd
from doctr.models import ocr_predictor
from doctr.io import DocumentFile

import fitz  # PyMuPDF
import pymupdf4llm
from docx import Document
import tempfile

os.environ['USE_TORCH'] = '1'
ocr_model = ocr_predictor(pretrained=True)

def process_doctr_output(doctr_output):
    text = ""
    for page in doctr_output.pages:
        for block in page.blocks:
            for line in block.lines:
                line_text = " ".join([word.value for word in line.words])
                text += line_text + " "
    return text

def extract_text_with_ocr(image_path):
    image = DocumentFile.from_images([image_path])
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
            pixmap = page.get_pixmap()
            
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img_file:
                pixmap.save(temp_img_file.name)
                extracted_text += extract_text_with_ocr(temp_img_file.name)
                os.remove(temp_img_file.name)  
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
    elif file_path.suffix in [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]:
        return extract_text_with_ocr(file_path)
    else:
        raise ValueError("Unsupported file format. Please use a supported file format.")
