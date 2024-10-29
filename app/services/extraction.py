from core.processors.document import DocumentProcessor

class ExtractionService:
    def __init__(self):
        self.document_processor = DocumentProcessor()

    def extract_data(self, file_path):
        return self.document_processor.process(file_path)
