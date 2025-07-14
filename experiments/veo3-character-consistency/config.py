import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
GEMINI_LOCATION = os.getenv("GEMINI_LOCATION")
IMAGEN_LOCATION = os.getenv("IMAGEN_LOCATION")
VEO_LOCATION = os.getenv("VEO_LOCATION")
INPUT_DIR = os.getenv("INPUT_DIR")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

MULTIMODAL_MODEL_NAME = "gemini-2.5-pro"
VEO_MODEL_NAME = "veo-3.0-generate-preview"
IMAGEN_MODEL_NAME = "imagen-3.0-capability-001"
