import os
from dataclasses import dataclass, field
from typing import TypedDict # Add this import
from dotenv import load_dotenv

# from models.image_models import ImageModel # Remove this import

load_dotenv(override=True)


# Define ImageModel here
class ImageModel(TypedDict):
    """Defines Models For Image Generation."""

    display: str
    model_name: str


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
    LYRIA_MODEL_VERSION: str = os.environ.get("LYRIA_MODEL_VERSION", "lyria-base-001")
    LYRIA_PROJECT_ID: str = os.environ.get("LYRIA_PROJECT_ID")
    MEDIA_BUCKET: str = os.environ.get("MEDIA_BUCKET", f"{PROJECT_ID}-assets")
    
    # Imagen
    MODEL_IMAGEN2 = "imagegeneration@006"
    MODEL_IMAGEN_NANO = "imagegeneration@004"
    MODEL_IMAGEN3_FAST = "imagen-3.0-fast-generate-001"
    MODEL_IMAGEN3 = "imagen-3.0-generate-002"
    
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
    
    display_image_models: list[ImageModel] = field( # Uncomment this field
        default_factory=lambda: [
            {"display": "Imagen 3 Fast", "model_name": Default.MODEL_IMAGEN3_FAST},
            {"display": "Imagen 3", "model_name": Default.MODEL_IMAGEN3},
        ]
    )



WELCOME_PAGE = [
    {"id": 0, "display": "Home", "icon": "home", "route": "/"},
    {"id": 6, "display": "Imagen", "icon": "image", "route": "/imagen", "group": "foundation"},
    {
        "id": 10,
        "display": "Veo",
        "icon": "movie_filter",
        "route": "/veo",
        "group": "foundation",
    },
    {"id": 15, "display": "Chirp 3 HD", "icon": "graphic_eq", "group": "foundation"},
]

if Default.LYRIA_PROJECT_ID is not None:
    WELCOME_PAGE.append(
        {
            "id": 20,
            "display": "Lyria",
            "icon": "music_note",
            "route": "/lyria",
            "group": "foundation",
        }
    )
else:
    WELCOME_PAGE.append(
        {"id": 30, "display": "Lyria", "icon": "music_note", "group": "foundation"}
    )

WELCOME_PAGE.append(
    {
        "id": 40,
        "display": "Motion Portraits",
        "icon": "portrait",
        "route": "/motion_portraits",
        "group": "workflows",
    }
)

WELCOME_PAGE.extend(
    [
        # {"id": 3, "display": "Imagen", "icon": "image", "route": "/imagen"}, # This ID might conflict if Lyria is also 3
        {
            "id": 50,
            "display": "Library",
            "icon": "perm_media",
            "route": "/library",
            "group": "app",
        },
        {
            "id": 100,
            "display": "Settings",
            "icon": "settings",
            "route": "/config",
            "align": "bottom",
            "group": "app",
        },
    ]
)
