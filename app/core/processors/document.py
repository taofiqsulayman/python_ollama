from pathlib import Path
import fitz
import pymupdf4llm
from docx import Document
import subprocess
from .base import FileProcessor
import tempfile
import os
from utils.utils import extract_text_with_ocr

class DocumentProcessor(FileProcessor):
    def process(self, file_path: Path) -> str:
        extension = file_path.suffix.lower()
        
        if extension == ".pdf":
            return self._process_pdf(file_path)
        elif extension == ".docx":
            return self._process_docx(file_path)
        elif extension == ".doc":
            return self._process_doc(file_path)
        elif extension == ".txt":
            return self._process_txt(file_path)
        else:
            raise ValueError(f"Unsupported document format: {extension}")

    def _process_pdf(self, file_path: Path) -> str:
        doc = fitz.open(str(file_path))
        text = ""
        
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            if not page.get_text().strip():
                pixmap = page.get_pixmap()
            
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img_file:
                    pixmap.save(temp_img_file.name)
                    text += extract_text_with_ocr(temp_img_file.name)
                    os.remove(temp_img_file.name)  
            else:
                text += pymupdf4llm.to_markdown(str(file_path), pages=[page_num])
        
        return text

    def _process_docx(self, file_path: Path) -> str:
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)

    def _process_doc(self, file_path: Path) -> str:
        result = subprocess.run(["antiword", str(file_path)], capture_output=True, text=True)
        return result.stdout

    def _process_txt(self, file_path: Path) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
