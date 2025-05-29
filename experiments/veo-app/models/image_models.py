# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#import json

#from google.cloud.aiplatform import telemetry
# from typing import TypedDict # Remove if not used elsewhere in this file

from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

#from models.model_setup import (
#    ImagenModelSetup,
#)


from typing import Optional
from dotenv import load_dotenv
from google import genai
from config.default import Default


# class ImageModel(TypedDict): # Remove this definition
#     """Defines Models For Image Generation."""
# 
#     display: str
#     model_name: str


class ImagenModelSetup:
    """Imagen model setup"""
    @staticmethod
    def init(
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """Init method"""
        config = Default()
        if not project_id:
            project_id = config.PROJECT_ID
        if not location:
            location = config.LOCATION
        if not model_id:
            model_id = config.MODEL_ID
        if None in [project_id, location, model_id]:
            raise ValueError("All parameters must be set.")
        print(f"initiating genai client with {project_id} in {location}")
        client = genai.Client(
            vertexai=config.INIT_VERTEX,
            project=project_id,
            location=location,
        )
        return client

@retry(
    wait=wait_exponential(
        multiplier=1, min=1, max=10
    ),  # Exponential backoff (1s, 2s, 4s... up to 10s)
    stop=stop_after_attempt(3),  # Stop after 3 attempts
    retry=retry_if_exception_type(Exception),  # Retry on all exceptions for robustness
    reraise=True,  # re-raise the last exception if all retries fail
)
def generate_images(model: str, prompt: str):
    """Imagen image generation with Google GenAI client"""
    
    client  = ImagenModelSetup.init(model_id=model)
    
    try:
        response = client.models.generate_images(
            model=model,  # Use the 'model' parameter passed to the function
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=3,
                include_rai_reason=True,
                output_mime_type='image/jpeg',
            ),
        )
        return response
    except Exception as e:
        print(f"Image generation error: {e}")
        raise
