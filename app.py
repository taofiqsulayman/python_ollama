import streamlit as st
from langchain_community.document_loaders import (
    CSVLoader,
    UnstructuredFileLoader,
    PyMuPDFLoader,
)
from tika import parser
import os
import tempfile
from io import BytesIO
from PIL import Image
import pytesseract
import pypdfium2 as pdfium
import fitz


st.title("Text Extraction App")

# Allow the user to select a library for extraction
library = st.selectbox(
    "Select Library",
    ["Unstructured File Loader", "Tika", "PyMuPDF", "OCR Combo", "CSV Loader"],
)

# Allow the user to upload files
uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True)


# Define the extraction functions
def extract_text_unstructured(file_path):
    loader = UnstructuredFileLoader(file_path)
    return loader.load()[0].page_content


def extract_text_tika(file_path):
    parsed = parser.from_file(file_path)
    return parsed["content"]


def convert_pdf_to_images(file_path, scale=300 / 72):
    pdf_file = pdfium.PdfDocument(file_path)
    page_indices = [i for i in range(len(pdf_file))]

    renderer = pdf_file.render(
        pdfium.PdfBitmap.to_pil,
        page_indices=page_indices,
        scale=scale,
    )

    list_final_images = []

    for i, image in zip(page_indices, renderer):
        image_byte_array = BytesIO()
        image.save(image_byte_array, format="jpeg", optimize=True)
        image_byte_array = image_byte_array.getvalue()
        list_final_images.append(dict({i: image_byte_array}))

    return list_final_images


def extract_text_ocr_combo(file_path):
    # Convert PDF to images
    images = convert_pdf_to_images(file_path)

    extracted_text = []

    for image_dict in images:
        for page_number, image_bytes in image_dict.items():
            # Convert byte array back to an image
            image = Image.open(BytesIO(image_bytes))

            # Perform OCR using Tesseract
            text = pytesseract.image_to_string(image)
            extracted_text.append(f"Page {page_number + 1}:\n{text}")

    # Return the extracted text as a single string
    return "\n".join(extracted_text)


def extract_text_csv_loader(file_path):
    loader = CSVLoader(file_path)
    all_files = loader.load()
    docs = [doc.page_content for doc in all_files]
    return docs


def extract_text_pymupdf(file_path):
    with fitz.open(file_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text("text")

    return text


# def extract_text_and_tables_from_pdf(file_path):
#         text = ""
#         tables = []

#         with fitz.open(file_path) as doc:
#             for page in doc:
#                 text += page.get_text("text")
#                 tables_found = camelot.read_pdf(file_path, pages=str(page.number + 1))
#                 for table in tables_found:
#                     df = table.df
#                     cleaned_table = clean_up_table(df)
#                     if not cleaned_table.empty:
#                         tables.append(convert_table_to_json(cleaned_table))

#         return text, tables


# def convert_table_to_json(table):
#     return table.to_json(orient="split")


# def clean_up_table(df):
#     df = df.dropna(how="all").dropna(axis=1, how="all")
#     df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
#     df = df.replace("", pd.NA)
#     df = df.dropna(how="all").dropna(axis=1, how="all")
#     return df


# def extract_text_nougat(file_path):
#     output_dir = "./out"

#     # Ensure the output directory exists
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)

#     # Construct the command
#     output_file = os.path.join(
#         output_dir, os.path.basename(file_path).replace(".pdf", ".mmd")
#     )
#     cmd = f"nougat {file_path} -o {output_file}"

#     print(f"Executing command: {cmd}")  # Debug: Print the command
#     os.system(cmd)

#     # Check if the output file exists
#     if os.path.exists(output_file):
#         try:
#             with open(output_file, "r") as f:
#                 extracted_text = f.read()
#                 print(
#                     f"Extracted text: {extracted_text[:500]}..."
#                 )  # Print a preview of the extracted text
#             return extracted_text
#         except Exception as e:
#             print(f"Error reading the output file: {e}")
#             return None
#     else:
#         print(f"Error: Output file '{output_file}' not found.")
#         return None


# Add PyMuPDF and OCR Combo functions here

# Button to trigger extraction
if st.button("Extract"):
    if uploaded_files:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for file in uploaded_files:
                file_path = os.path.join(tmp_dir, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                if library == "Unstructured File Loader":
                    result = extract_text_unstructured(file_path)
                    st.write("Unstructured File Loader Extracted Text:")
                    st.write(result)
                elif library == "Tika":
                    result = extract_text_tika(file_path)
                    st.write("Tika Extracted Text:")
                    st.write(result)
                elif library == "OCR Combo":
                    result = extract_text_ocr_combo(file_path)
                    st.write("OCR Combo Extracted Text:")
                    st.write(result)
                elif library == "CSV Loader":
                    result = extract_text_csv_loader(file_path)
                    st.write("CSV Loader Extracted Text:")
                    st.write(result)
                elif library == "PyMuPDF":
                    result = extract_text_pymupdf(file_path)
                    st.write("PyMuPDF Extracted Text:")
                    st.write(result)
                elif library == "Nougat":
                    result = extract_text_nougat(file_path)
                    st.write("Nougat Extracted Text:")
                    st.write(result)
                elif library == "Text/Table Extractor":
                    text, tables = extract_text_and_tables_from_pdf(file_path)
                    st.write("Text Extracted Text:")
                    st.write(text)
                    st.write("Tables:")
                    for table in tables:
                        st.write(table)
                # Add handling for PyMuPDF and OCR Combo here
    else:
        st.error("Please upload files first")
