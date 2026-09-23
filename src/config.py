import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

QDRANT_STORAGE_PATH = str(ROOT_DIR / "qdrant_storage")
COLLECTION_NAME = "nyayaDocs"

# Qdrant Cloud settings (optional - falls back to local storage if not provided)
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
