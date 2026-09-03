import os
from pathlib import Path
import cv2  # type: ignore

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
HEATMAP_DIR = DATA_DIR / "heatmaps"
ASSETS_DIR = BASE_DIR / "app" / "core" / "assets"
FACE_CASCADE_PATH = ASSETS_DIR / "haarcascade_frontalface_default.xml"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# System & Inference Metadata
PIPELINE_VERSION = "2.0.0"
AI_INFERENCE_MODE = "LOCAL / OFFLINE"

# Database & Security
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'sih_screening.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "sih2026-ssb-secure-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12 # 12 hours for checkpoint duty shift

# Upload Security Constraints
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# Configurable Risk Scoring Constants
RISK_LOW_THRESHOLD = float(os.getenv("RISK_LOW_THRESHOLD", "30.0"))
RISK_HIGH_THRESHOLD = float(os.getenv("RISK_HIGH_THRESHOLD", "65.0"))
TAMPERING_WEIGHT = float(os.getenv("TAMPERING_WEIGHT", "0.40"))
FACE_WEIGHT = float(os.getenv("FACE_WEIGHT", "0.35"))
VALIDATION_WEIGHT = float(os.getenv("VALIDATION_WEIGHT", "0.25"))
DUPLICATE_FACE_THRESHOLD = float(os.getenv("DUPLICATE_FACE_THRESHOLD", "82.0"))

def get_face_cascade() -> cv2.CascadeClassifier:
    """Safely loads frontal face cascade classifier from local asset or cv2.data."""
    if FACE_CASCADE_PATH.exists():
        cascade = cv2.CascadeClassifier(str(FACE_CASCADE_PATH))
        if not cascade.empty():
            return cascade
    
    if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
        default_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if os.path.exists(default_path):
            cascade = cv2.CascadeClassifier(default_path)
            if not cascade.empty():
                return cascade
                
    return cv2.CascadeClassifier()
