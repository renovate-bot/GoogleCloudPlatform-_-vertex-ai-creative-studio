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

import json
from google.genai import types

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from google.cloud.aiplatform import telemetry

from models.model_setup import (
    ImagenModelSetup,
)

""" Image Models type definitions """
from typing import TypedDict


class ImageModel(TypedDict):
    """Defines Models For Image Generation."""

    display: str
    model_name: str

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
            model='imagen-3.0-generate-002',
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
