from pathlib import Path
import pandas as pd
from .base import FileProcessor

class SpreadsheetProcessor(FileProcessor):
    def process(self, file_path: Path) -> str:
        extension = file_path.suffix.lower()
        
        if extension == ".csv":
            df = pd.read_csv(file_path)
        elif extension == ".xlsx":
            df = pd.read_excel(file_path)
        elif extension == ".tsv":
            df = pd.read_csv(file_path, sep="\t")
        else:
            raise ValueError(f"Unsupported spreadsheet format: {extension}")
        
        return self._convert_to_markdown(df)

    def _convert_to_markdown(self, df: pd.DataFrame) -> str:
        return df.to_markdown(index=False) + "\n\n"