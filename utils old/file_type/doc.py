import subprocess
from docx import Document

def process_docx(file_path):
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
