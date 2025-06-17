from dataclasses import dataclass, field

import mesop as me

from config.default import (
    Default,
    ImageModel,
)

app_config_instance = Default()

def _get_default_image_models() -> list[ImageModel]:
    """Helper function for PageState default_factory."""
    # Ensure app_config_instance.display_image_models provides a list of ImageModel compatible dicts or objects
    return app_config_instance.display_image_models.copy()


@dataclass
@me.stateclass
class PageState:
    """Local Page State"""

    # Image generation model selection and output
    image_models: list[ImageModel] = field(default_factory=_get_default_image_models)
    image_output: list[str] = field(default_factory=list)
    image_commentary: str = ""
    image_model_name: str = app_config_instance.MODEL_IMAGEN4_FAST

    # General UI state
    is_loading: bool = False
    show_advanced: bool = False
    error_message: str = ""
    show_dialog: bool = False
    dialog_message: str = ""

    # Image prompt and related settings
    image_prompt_input: str = ""
    image_prompt_placeholder: str = ""
    image_textarea_key: int = 0  # Used as str(key) for component

    image_negative_prompt_input: str = ""
    image_negative_prompt_placeholder: str = ""
    image_negative_prompt_key: int = 0  # Used as str(key) for component

    # Image generation parameters
    imagen_watermark: bool = True  # SynthID notice implies watermark is active
    imagen_seed: int = 0
    imagen_image_count: int = 4

    # Image style modifiers
    image_content_type: str = "Photo"
    image_color_tone: str = "Cool tone"
    image_lighting: str = "Golden hour"
    image_composition: str = "Wide angle"
    image_aspect_ratio: str = "1:1"

    timing: str = ""  # For displaying generation time
