import os
import subprocess
import pandas as pd
from doctr.models import ocr_predictor
from doctr.io import DocumentFile

import fitz  # PyMuPDF
import pymupdf4llm
from docx import Document
import tempfile
from pathlib import Path
from typing import Dict, Tuple

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
                try:
                    # Save the pixmap to a temporary image file
                    pixmap.save(temp_img_file.name)
                    temp_img_file.close()  # Explicitly close the file before processing
                    extracted_text += extract_text_with_ocr(temp_img_file.name)
                except Exception as e:
                    print(f"Error processing page {i} with OCR: {e}")
                finally:
                    # Remove the temporary file manually after use
                    if Path(temp_img_file.name).exists():
                        os.remove(temp_img_file.name)
                        print(f"Removed temporary file: {temp_img_file.name}")
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

def create_analysis_tables(json_data: Dict) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convert JSON response into two dataframes: results table and confidence level table.
    
    Args:
        json_data (dict): JSON response containing per_document analysis results
    
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (results_df, confidence_df)
        - results_df columns: File Name, Instruction1, Instruction2, ...
        - confidence_df columns: File Name, Instruction1, Instruction2, ...
    """
    # Get the per_document data
    per_document = json_data.get('per_document', {})
    
    # Initialize lists to store rows for both tables
    results_rows = []
    confidence_rows = []
    
    # Get all unique instructions (columns) from the data
    instructions = set()
    for doc_data in per_document.values():
        instructions.update(doc_data.keys())
    instructions = sorted(list(instructions))  # Sort for consistent column order
    
    # Create column names
    columns = ['File Name'] + instructions
    
    # Process each document
    for filename, doc_data in per_document.items():
        # Initialize rows with filename
        result_row = {'File Name': filename}
        confidence_row = {'File Name': filename}
        
        # Process each instruction
        for instruction in instructions:
            if instruction in doc_data:
                # Extract value and confidence
                value = doc_data[instruction].get('value', '')
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value)
                confidence = doc_data[instruction].get('confidence', '')
                
                result_row[instruction] = value
                confidence_row[instruction] = confidence
            else:
                # Handle missing instructions
                result_row[instruction] = ''
                confidence_row[instruction] = ''
        
        results_rows.append(result_row)
        confidence_rows.append(confidence_row)
    
    # Create DataFrames
    results_df = pd.DataFrame(results_rows, columns=columns)
    confidence_df = pd.DataFrame(confidence_rows, columns=columns)
    
    return results_df, confidence_df

async def process_files(upload_file):
    """Handle FastAPI UploadFile object"""
    # Get file extension
    file_extension = Path(upload_file.filename).suffix.lower()

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        # Write uploaded file content to temporary file
        content = await upload_file.read()
        temp_file.write(content)
        temp_path = Path(temp_file.name)  # Get the path of the temp file

    try:
        # Process the temporary file based on its extension
        if file_extension in [".pdf", ".PDF"]:
            return process_pdf(temp_path)
        elif file_extension in [".csv", ".CSV", ".tsv", ".TSV", ".xlsx", ".XLSX"]:
            return process_csv_xlsx_tsv(temp_path)
        elif file_extension in [".doc", ".docx"]:
            return process_word_docs(temp_path)
        elif file_extension in [".txt", ".TXT"]:
            return process_txt_file(temp_path)
        elif file_extension in [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]:
            return extract_text_with_ocr(temp_path)
        else:
            raise ValueError("Unsupported file format. Please use a supported file format.")
    finally:
        # Clean up the temporary file
        if temp_path.exists():
            try:
                os.unlink(temp_path)
            except PermissionError as e:
                print(f"Error deleting file: {e}")