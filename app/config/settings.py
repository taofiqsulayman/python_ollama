from pathlib import Path
import os

class Settings:
    # App settings
    DEBUG = os.getenv("DEBUG", "False") == "True"
    APP_TITLE = "File Processor"
    APP_ICON = "📄"
    
    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Auth settings
    KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
    KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
    KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")
    
    # File processing
    SUPPORTED_EXTENSIONS = {
        "document": [".pdf", ".doc", ".docx", ".txt"],
        "spreadsheet": [".xlsx", ".csv", ".tsv"],
        "image": [".jpg", ".jpeg", ".png"]
    }
    TEMP_DIR = Path("temp")

settings = Settings()
