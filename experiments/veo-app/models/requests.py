from typing import Optional

from pydantic import BaseModel, Field


class VideoGenerationRequest(BaseModel):
    """
    Defines the contract for a video generation request.
    This schema is used by the UI to call the model layer and will be
    the schema for the future FastAPI endpoint.
    """

    prompt: str
    duration_seconds: int = Field(..., gt=0)
    aspect_ratio: str
    resolution: str
    enhance_prompt: bool
    model_version_id: str
    reference_image_gcs: Optional[str] = None
    last_reference_image_gcs: Optional[str] = None
    reference_image_mime_type: Optional[str] = None
    last_reference_image_mime_type: Optional[str] = None
