# Copyright 2025 Google LLC
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

import time
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from common.error_handling import GenerationError
from config.default import Default
from config.veo_models import get_veo_model_config

config = Default()


load_dotenv(override=True)

client = genai.Client(
    vertexai=True, project=config.VEO_PROJECT_ID, location=config.LOCATION
)

def generate_video(state):
    """
    Generates a video based on the current state using the genai SDK.
    This function handles text-to-video, image-to-video, and interpolation by
    using the correct types.Image constructor with the gcs_uri parameter.
    """
    model_config = get_veo_model_config(state.veo_model)
    if not model_config:
        raise GenerationError(f"Unsupported VEO model version: {state.veo_model}")

    # --- Prepare Generation Configuration ---
    enhance_prompt = (
        True if state.veo_model.startswith("3.") else state.auto_enhance_prompt
    )

    gen_config_args = {
        "aspect_ratio": state.aspect_ratio,
        "number_of_videos": 1,
        "duration_seconds": state.video_length,
        "enhance_prompt": enhance_prompt,
        "output_gcs_uri": f"gs://{config.VIDEO_BUCKET}",
    }

    # --- Prepare Image and Video Inputs ---
    image_input = None
    # Check for interpolation (first and last frame)
    if getattr(state, "reference_image_gcs", None) and getattr(
        state, "last_reference_image_gcs", None
    ):
        print("Mode: Interpolation")
        image_input = types.Image(
            gcs_uri=state.reference_image_gcs,
            mime_type=state.reference_image_mime_type,
        )
        gen_config_args["last_frame"] = types.Image(
            gcs_uri=state.last_reference_image_gcs,
            mime_type=state.last_reference_image_mime_type,
        )

    # Check for standard image-to-video
    elif getattr(state, "reference_image_gcs", None):
        print("Mode: Image-to-Video")
        image_input = types.Image(
            gcs_uri=state.reference_image_gcs,
            mime_type=state.reference_image_mime_type,
        )
    else:
        print("Mode: Text-to-Video")

    gen_config = types.GenerateVideosConfig(**gen_config_args)

    # --- Call the API ---
    try:
        operation = client.models.generate_videos(
            model=model_config.model_name,
            prompt=state.veo_prompt_input,
            config=gen_config,
            image=image_input,
        )

        print("Polling video generation operation...")
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)
            print(f"Operation in progress: {operation.name}")

        if operation.error:
            error_details = str(operation.error)
            print(f"Video generation failed with error: {error_details}")
            raise GenerationError(f"API Error: {error_details}")

        if operation.response:
            if (
                hasattr(operation.result, "rai_media_filtered_count")
                and operation.result.rai_media_filtered_count > 0
            ):
                filter_reason = operation.result.rai_media_filtered_reasons[0]
                raise GenerationError(f"Content Filtered: {filter_reason}")

            if (
                hasattr(operation.result, "generated_videos")
                and operation.result.generated_videos
            ):
                video_uri = operation.result.generated_videos[0].video.uri
                print(f"Successfully generated video: {video_uri}")
                return video_uri
            else:
                raise GenerationError(
                    "API reported success but no video URI was found in the response."
                )
        else:
            raise GenerationError(
                "Unexpected API response structure or operation not done."
            )

    except Exception as e:
        print(f"An unexpected error occurred in generate_video: {e}")
        raise GenerationError(f"An unexpected error occurred: {e}") from e