import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed"
REPORTS_DIR = BASE_DIR / "reports"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Server Config
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8088
FRONTEND_PORT = 5188

# OCR & Processing Config
OCR_CONFIDENCE_THRESHOLD = 0.60
FUZZY_MATCH_THRESHOLD = 72  # Rapidfuzz ratio out of 100
MAX_IMAGE_SIZE_MB = 15
MAX_URL_FETCH_TIMEOUT_SEC = 12

# Supported file formats
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".pdf"}
