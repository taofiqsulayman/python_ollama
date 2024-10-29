from pathlib import Path
import tempfile
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from .base import FileProcessor

class ImageProcessor(FileProcessor):
    def __init__(self):
        self.ocr_model = ocr_predictor(pretrained=True)

    def process(self, file_path: Path) -> str:
        image = DocumentFile.from_images([str(file_path)])
        result = self.ocr_model(image)
        return self._process_ocr_output(result)

    def _process_ocr_output(self, ocr_output):
        text = []
        for page in ocr_output.pages:
            page_text = []
            for block in page.blocks:
                for line in block.lines:
                    line_text = " ".join(word.value for word in line.words)
                    page_text.append(line_text)
            text.append("\n".join(page_text))
        return "\n\n".join(text)