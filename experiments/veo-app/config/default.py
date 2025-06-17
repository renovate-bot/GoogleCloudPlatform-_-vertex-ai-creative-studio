import os
from dataclasses import dataclass, field
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict

# from models.image_models import ImageModel # Remove this import

load_dotenv(override=True)


# Define ImageModel here
class ImageModel(TypedDict):
    """Defines Models For Image Generation."""

    display: str
    model_name: str

class NavItem(BaseModel):
    id: int
    display: str
    icon: str
    route: Optional[str] = None
    group: Optional[str] = None
    align: Optional[str] = None
    feature_flag: Optional[str] = None
    feature_flag_not: Optional[str] = None

class NavConfig(BaseModel):
    pages: List[NavItem]


@dataclass
class Default:
    """Defaults class"""

    # Gemini
    PROJECT_ID: str = os.environ.get("PROJECT_ID")
    LOCATION: str = os.environ.get("LOCATION", "us-central1")
    MODEL_ID: str = os.environ.get("MODEL_ID", "gemini-2.0-flash")
    INIT_VERTEX: bool = True

    # Collections
    GENMEDIA_FIREBASE_DB: str = os.environ.get("GENMEDIA_FIREBASE_DB", "(default)")
    GENMEDIA_COLLECTION_NAME: str = os.environ.get(
        "GENMEDIA_COLLECTION_NAME", "genmedia"
    )

    # storage
    GENMEDIA_BUCKET: str = os.environ.get("GENMEDIA_BUCKET", f"{PROJECT_ID}-assets")
    VIDEO_BUCKET: str = os.environ.get("VIDEO_BUCKET", f"{PROJECT_ID}-assets/videos")
    IMAGE_BUCKET: str = os.environ.get("IMAGE_BUCKET", f"{PROJECT_ID}-assets/images")

    # Veo
    VEO_MODEL_ID: str = os.environ.get("VEO_MODEL_ID", "veo-2.0-generate-001")
    VEO_PROJECT_ID: str = os.environ.get("VEO_PROJECT_ID", PROJECT_ID)

    VEO_EXP_MODEL_ID: str = os.environ.get("VEO_EXP_MODEL_ID", "veo-3.0-generate-preview")
    VEO_EXP_PROJECT_ID: str = os.environ.get("VEO_EXP_PROJECT_ID", PROJECT_ID)
    
    # Lyria
    LYRIA_MODEL_VERSION: str = os.environ.get("LYRIA_MODEL_VERSION", "lyria-002")
    LYRIA_PROJECT_ID: str = os.environ.get("LYRIA_PROJECT_ID")
    MEDIA_BUCKET: str = os.environ.get("MEDIA_BUCKET", f"{PROJECT_ID}-assets")
    
    # Imagen
    MODEL_IMAGEN2 = "imagegeneration@006"
    MODEL_IMAGEN_NANO = "imagegeneration@004"
    MODEL_IMAGEN_FAST = "imagen-3.0-fast-generate-001"
    MODEL_IMAGEN = "imagen-3.0-generate-002"
    MODEL_IMAGEN4 = "imagen-4.0-generate-preview-06-06"
    MODEL_IMAGEN4_FAST = "imagen-4.0-fast-generate-preview-06-06"
    MODEL_IMAGEN4_ULTRA = "imagen-4.0-ultra-generate-preview-06-06"
    MODEL_IMAGEN_EDITING = "imagen-3.0-capability-001"
    
    IMAGEN_PROMPTS_JSON = "prompts/imagen_prompts.json"
    
    image_modifiers: list[str] = field(
        default_factory=lambda: [
            "aspect_ratio",
            "content_type",
            "color_tone",
            "lighting",
            "composition",
        ]
    )
    
    display_image_models: list[ImageModel] = field(
        default_factory=lambda: Default._get_display_image_models()
    )

    @staticmethod
    def _get_display_image_models() -> list[ImageModel]:
        imagen_models_override_str = os.environ.get("IMAGEN_MODELS")
        if imagen_models_override_str:
            try:
                parsed_models = json.loads(imagen_models_override_str)
                if isinstance(parsed_models, list) and all(
                    isinstance(item, dict) and "display" in item and "model_name" in item
                    for item in parsed_models
                ):
                    print(f"Using IMAGEN_MODELS override from environment: {parsed_models}")
                    return parsed_models # type: ignore
                else:
                    print(
                        "Warning: IMAGEN_MODELS environment variable has invalid format. "
                        "Expected a JSON list of {'display': str, 'model_name': str}. "
                        "Falling back to default models."
                    )
            except json.JSONDecodeError:
                print(
                    "Warning: IMAGEN_MODELS environment variable is not valid JSON. "
                    "Falling back to default models."
                )
            except Exception as e:
                print(
                    f"Warning: Error processing IMAGEN_MODELS environment variable: {e}. "
                    "Falling back to default models."
                )
        
        # Default models if override is not present or invalid
        return [
            {"display": "Imagen 3 Fast", "model_name": Default.MODEL_IMAGEN_FAST},
            {"display": "Imagen 3", "model_name": Default.MODEL_IMAGEN},
            {"display": "Imagen 4 Fast (preview)", "model_name": Default.MODEL_IMAGEN4_FAST},
            {"display": "Imagen 4 (preview)", "model_name": Default.MODEL_IMAGEN4},
            {"display": "Imagen 4 Ultra (preview)", "model_name": Default.MODEL_IMAGEN4_ULTRA},
            # Example: to include Nano by default if not overridden:
            # {"display": "Imagen Nano", "model_name": Default.MODEL_IMAGEN_NANO},
        ]


def load_welcome_page_config():
    with open('config/navigation.json', 'r') as f:
        data = json.load(f)

    # This will raise a validation error if the JSON is malformed
    config = NavConfig(**data)

    def is_feature_enabled(page: NavItem):
        if page.feature_flag:
            return bool(getattr(Default, page.feature_flag, False))
        if page.feature_flag_not:
            return not bool(getattr(Default, page.feature_flag_not, False))
        return True

    filtered_pages = [page.model_dump(exclude_none=True) for page in config.pages if is_feature_enabled(page)]

    return sorted(filtered_pages, key=lambda x: x['id'])

WELCOME_PAGE = load_welcome_page_config()
