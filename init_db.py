from models import init_db
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL")
    init_db(db_url)
    print("Database initialized successfully!")