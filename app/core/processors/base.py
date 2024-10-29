import abc
from pathlib import Path
from config.settings import settings
from .document import DocumentProcessor
from .spreadsheet import SpreadsheetProcessor
from .image import ImageProcessor
class FileProcessor(abc.ABC):
    @abc.abstractmethod
    def process(self, file_path):
        pass
    
    @classmethod
    def get_processor(cls, file_path: Path) -> 'FileProcessor':
        extension = file_path.suffix.lower()
        if extension in settings.SUPPORTED_EXTENSIONS["document"]:
            return DocumentProcessor()
        elif extension in settings.SUPPORTED_EXTENSIONS["spreadsheet"]:
            return SpreadsheetProcessor()
        elif extension in settings.SUPPORTED_EXTENSIONS["image"]:
            return ImageProcessor()
        raise ValueError(f"Unsupported file format: {extension}")
