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
"""Gemini methods"""

import json
import time
import uuid
from typing import Dict, Optional

import requests
from google.cloud.aiplatform import telemetry
from google.genai import types
from models.shop_the_look_models import (
    GeneratedImageAccuracyWrapper,
    CatalogRecord,
    ArticleDescriptionWrapper,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from common.error_handling import GenerationError
from common.storage import store_to_gcs
from config.default import Default  # Import Default for cfg
from config.rewriters import MAGAZINE_EDITOR_PROMPT, REWRITER_PROMPT
from models.character_consistency_models import (
    BestImage,
    FacialCompositeProfile,
    GeneratedPrompts,
)
from models.model_setup import (
    GeminiModelSetup,
)
from models.shop_the_look_models import (
    BestImageAccuracy,
)
from pydantic import BaseModel, Field


class Transformation(BaseModel):
    title: str = Field(
        ...,
        description="""A short, three-word maximum title for the transformation
        button.""",
    )
    prompt: str = Field(
        ..., description="The detailed prompt to be used for image generation."
    )


class TransformationPrompts(BaseModel):
    transformations: list[Transformation] = Field(
        ...,
        description="A list of three interesting transformation instructions.",
        min_length=3,
        max_length=3,
    )


class Room(BaseModel):
    room_name: str = Field(..., description="The name of a room identified in the floor plan, e.g., 'Living Room' or 'Bedroom 1'.")

class RoomList(BaseModel):
    rooms: list[Room] = Field(..., description="A list of rooms identified in the floor plan.")


# Initialize client and default model ID for rewriter
client = GeminiModelSetup.init()
cfg = Default()  # Instantiate config
REWRITER_MODEL_ID = cfg.MODEL_ID  # Use default model from config for rewriter


def generate_image_from_prompt_and_images(
    prompt: str,
    images: list[str],
    aspect_ratio: str,
    gcs_folder: str = "generated_images",
    file_prefix: str = "image",
    candidate_count: int = 1,
) -> tuple[list[str], float]:
    """Generates images from a prompt and a list of images."""
    start_time = time.time()
    model_name = cfg.GEMINI_IMAGE_GEN_MODEL

    parts = [types.Part.from_text(text=prompt)]
    for image_uri in images:
        parts.append(types.Part.from_uri(file_uri=image_uri, mime_type="image/png"))

    contents = [types.Content(role="user", parts=parts)]

    client = GeminiModelSetup.init(
        location=cfg.GEMINI_IMAGE_GEN_LOCATION,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
            ),
            #candiate_count=candidate_count,
        ),
    )
    
    end_time = time.time()
    execution_time = end_time - start_time

    gcs_uris = []
    if (
        response.candidates
        and response.candidates[0].content
        and response.candidates[0].content.parts
    ):
        print(
            f"generate_image_from_prompt_and_images: {len(response.candidates[0].content.parts)} parts"
        )
        for i, part in enumerate(response.candidates[0].content.parts):
            if hasattr(part, "text"):
                print(f"generate_image_from_prompt_and_images (text): {part.text}")
            if hasattr(part, "inline_data") and part.inline_data:
                # Default to "image/png" if mime_type is missing
                mime_type = "image/png"
                if (
                    hasattr(part.inline_data, "mime_type")
                    and part.inline_data.mime_type
                ):
                    mime_type = part.inline_data.mime_type
                gcs_uri = store_to_gcs(
                    folder=gcs_folder,
                    file_name=f"{file_prefix}_{uuid.uuid4()}_{i}.png",
                    mime_type=mime_type,
                    contents=part.inline_data.data,
                )
                gcs_uris.append(gcs_uri)
    else:
        print("generate_image_from_prompt_and_images: no images")
    return gcs_uris, execution_time


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def extract_room_names_from_image(image_uri: str) -> list[str]:
    """Analyzes a floor plan image and extracts the names of the rooms."""
    model_name = cfg.MODEL_ID # Use a fast model for this analysis task

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RoomList.model_json_schema(),
        temperature=0.1, # Low temperature for factual extraction
    )

    prompt_text = "Analyze this floor plan image and identify all the labeled rooms. Return a JSON list of the room names."
    
    prompt_parts = [
        prompt_text,
        types.Part.from_uri(file_uri=image_uri, mime_type="image/png"),
    ]

    response = client.models.generate_content(
        model=model_name, contents=prompt_parts, config=config
    )
    
    room_list_obj = RoomList.model_validate_json(response.text)
    
    return [room.room_name for room in room_list_obj.rooms]



@retry(
    wait=wait_exponential(
        multiplier=1, min=1, max=10
    ),  # Exponential backoff (1s, 2s, 4s... up to 10s)
    stop=stop_after_attempt(3),  # Stop after 3 attempts
    retry=retry_if_exception_type(Exception),  # Retry on all exceptions for robustness
    reraise=True,  # re-raise the last exception if all retries fail
)
def rewriter(original_prompt: str, rewriter_prompt: str) -> str:
    """A Gemini rewriter.

    Args:
        original_prompt: The original prompt to be rewritten.
        rewriter_prompt: The rewriter prompt.

    Returns:
        The rewritten prompt text.
    """

    full_prompt = f"{rewriter_prompt} {original_prompt}"
    print(f"Rewriter: '{full_prompt}' with model {REWRITER_MODEL_ID}")
    try:
        response = client.models.generate_content(
            model=REWRITER_MODEL_ID,  # Explicitly use the configured model
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
            ),
        )
        print(f"Rewriter success! {response.text}")
        return response.text
    except Exception as e:
        print(f"Rewriter error: {e}")
        raise


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def analyze_audio_with_gemini(
    audio_uri: str, music_generation_prompt: str
) -> Optional[Dict[str, any]]:
    """
    Analyzes a given audio file URI against an original music generation prompt using Gemini.

    Args:
        audio_uri: The GCS URI (gs://bucket/object) of the audio file to analyze.
        music_generation_prompt: The original prompt used to generate the music.

    Returns:
        A dictionary containing the structured analysis from Gemini, or None if an error occurs.
    """
    print(
        f"Starting audio analysis for URI: {audio_uri} with prompt: '{music_generation_prompt}'"
    )

    # Use configured model for audio analysis
    analysis_model_id = cfg.GEMINI_AUDIO_ANALYSIS_MODEL_ID

    # Prepare the audio part using from_uri
    try:
        audio_part = types.Part.from_uri(file_uri=audio_uri, mime_type="audio/wav")
        print(f"Audio part created from URI: {audio_uri}")
    except Exception as e:
        print(f"Failed to create audio Part from URI '{audio_uri}': {e}")
        raise  # Re-raise to be caught by tenacity or calling function

    # Prepare the text part, incorporating the dynamic music_generation_prompt
    text_prompt_for_analysis = f"""Describe this musical clip ("audio-analysis"), then suggest a list of genres and qualities.

The original prompt was the following:

"{music_generation_prompt}"

Then, review the original prompt with your description.

Output this as JSON.

"""

    text_part = types.Part.from_text(text=text_prompt_for_analysis)

    # System instruction
    system_instruction_text = """You're a music producer and critic with a keen ear for describing musical qualities and soundscapes. If you're given audio, describe it. If you're given an idea or a scenario, describe the music that would represent that. Aim for a single paragraph description of musical direction and optionally any explanation of your direction. As a rule, don't refer to any particular artist, but instead describe their style."""
    # system_instruction_part = types.Part.from_text(text=system_instruction_text) # API expects a Part or list of Parts

    safety_settings_list = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]

    schema_json = {  # This is the schema from your sample
        # "$schema": "http://json-schema.org/draft-07/schema#", # Schema for schema, optional here
        "title": "Music Analysis and Alignment Response",
        "description": "Schema for describing audio analysis, suggested genres/qualities, and alignment with an initial prompt.",
        "type": "OBJECT",
        "properties": {
            "audio-analysis": {
                "description": "A single-paragraph description of the provided audio or suggested musical direction.",
                "type": "STRING",
            },
            "genre-quality": {
                "description": "A list of suggested genres and descriptive musical qualities.",
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "minItems": 1,
            },
            "prompt-alignment": {
                "description": "An evaluation of how well the audio or generated description aligns with the original prompt's requirements.",
                "type": "STRING",
            },
        },
        "required": ["audio-analysis", "genre-quality", "prompt-alignment"],
        # "additionalProperties": False, # This can be strict; ensure model adheres or remove
    }
    generation_config_params = types.GenerateContentConfig(
        system_instruction=system_instruction_text,
        safety_settings=safety_settings_list,
        # temperature=1.0,  # Corrected: float value
        # top_p=1.0,  # Corrected: float value
        # temperature=1.0,  # Corrected: float value
        # top_p=1.0,  # Corrected: float value
        # seed=0, # Seed might not be available in all models or SDK versions, or might be int
        # max_output_tokens=8192,  # Max for Flash is 8192. 65535 is too high.
        # max_output_tokens=8192,  # Max for Flash is 8192. 65535 is too high.
        response_mime_type="application/json",  # This is key for JSON output
        response_schema=schema_json,
    )

    # Construct the contents for the API call
    contents_for_api = [
        types.Content(role="user", parts=[audio_part, text_part]),
    ]

    try:
        print(f"Sending request to Gemini model: {analysis_model_id}")

        response = client.models.generate_content(  # Or client.generate_content if client is a model instance
            model=analysis_model_id,
            contents=contents_for_api,
            config=generation_config_params,
        )

        print("Received response from Gemini.")
        print(f"{response}")

        # Assuming the response.text contains the JSON string due to response_mime_type
        if response.text:
            parsed_json = json.loads(response.text)
            print(f"Successfully parsed analysis JSON: {parsed_json}")
            return parsed_json
            # return response.text
        else:
            # Handle cases where response.text might be empty or parts are structured differently
            # This part might need adjustment based on actual API response structure for JSON
            if response.parts:
                # Try to assemble from parts if text is empty but parts exist (less common for JSON)
                json_text_from_parts = "".join(
                    part.text for part in response.parts if hasattr(part, "text")
                )
                if json_text_from_parts:
                    parsed_json = json.loads(json_text_from_parts)
                    print(
                        f"Successfully parsed analysis JSON from parts: {parsed_json}"
                    )
                    return parsed_json
            print("Warning: Gemini response text was empty.")
            return None  # Or raise an error

    except Exception as e:
        print(f"Error during Gemini API call for audio analysis: {e}")
        # The retry decorator will handle re-raising if all attempts fail.
        # If not using retry, you'd raise e here.
        raise  # Re-raise for tenacity or the caller


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def image_critique(original_prompt: str, img_uris: list[str]) -> str:
    """Image critic

    Args:
        img_uris (list[str]): a list of GCS URIs of images to critique

    Returns:
        str: critique of images
    """

    critic_prompt = MAGAZINE_EDITOR_PROMPT.format(original_prompt)

    prompt_parts = [critic_prompt]

    for img_uri in img_uris:
        prompt_parts.append(
            types.Part.from_uri(file_uri=img_uri, mime_type="image/png")
        )

    safety_settings_list = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]
    # prompt_parts is already a list of Part-like objects (str, Part).
    # The SDK will form a single Content message from this list.
    # No need to wrap it in types.Content manually here if it's for a single turn.
    # contents_payload = [types.Content(role="user", parts=prompt_parts)] # This would be for multi-turn history

    # For a single user message with multiple parts:
    contents_payload = prompt_parts

    # The telemetry.tool_context_manager is from the Vertex AI SDK,
    # client here is from google-genai, so this context manager might not apply or could cause issues.
    # If it's not needed or causes errors, it should be removed.
    # Assuming it's a no-op or handled if telemetry is not configured for google-genai.
    with telemetry.tool_context_manager("creative-studio"):
        try:
            # Use default model from config for critique, unless a specific one is configured
            critique_model_id = (
                cfg.MODEL_ID
            )  # Or a specific cfg.GEMINI_CRITIQUE_MODEL_ID
            print(
                f"Sending critique request to Gemini model: {critique_model_id} with {len(contents_payload)} parts."
            )

            response = client.models.generate_content(
                model=critique_model_id,
                contents=contents_payload,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                    safety_settings=safety_settings_list,
                    max_output_tokens=8192,
                ),
            )

            print("Received critique response from Gemini.")

            if response.text:
                print(
                    f"Critique generated (truncated): {response.text[:200]}..."
                )  # Log a snippet
                return response.text  # Return the text directly
            # Fallback for safety reasons, though .text should be populated for text responses
            elif (
                response.candidates
                and response.candidates[0].content.parts
                and response.candidates[0].content.parts[0].text
            ):
                text_response = response.candidates[0].content.parts[0].text
                print(f"Critique generated (truncated): {text_response[:200]}...")
                return text_response
            else:
                print(
                    "Warning: Gemini critique response text was empty or response structure unexpected."
                )
                return "Critique could not be generated (empty or unexpected response)."

        except Exception as e:
            print(f"Error during Gemini API call for image critique: {e}")
            raise


def rewrite_prompt_with_gemini(original_prompt: str) -> str:
    """
    Outputs a rewritten prompt using the Gemini model.
    Args:
        original_prompt (str): The user's original prompt.
    Returns:
        str: The rewritten prompt.
    Raises:
        Exception: If the rewriter service fails.
    """
    try:
        rewritten_text = rewriter(original_prompt, REWRITER_PROMPT)
        if not rewritten_text:
            print("Warning: Rewriter returned an empty prompt.")
            return original_prompt
        return rewritten_text
    except Exception as e:
        print(f"Gemini rewriter failed: {e}")
        raise


def generate_compliment(generation_instruction: str, image_output):
    """
    Generates a Gemini-powered critique/commentary for the generated images.
    Updates PageState.image_commentary and PageState.error_message directly.
    """
    start_time = time.time()
    critique_text = ""
    error_for_this_op = ""

    print(
        f"Generating critique for instruction: '{generation_instruction}' and {len(image_output)} images."
    )
    try:
        # Assuming image_critique is a blocking call to your Gemini model for critique
        critique_text = image_critique(generation_instruction, image_output)
        if not critique_text:
            print("Warning: Image critique returned empty.")
            # critique_text = "No critique available for these images." # Optional default

    except requests.exceptions.HTTPError as err_http:
        print(f"HTTPError during image critique: {err_http}")
        error_for_this_op = f"Network error during critique: {err_http.response.status_code if err_http.response else 'Unknown'}"
    except ValueError as err_value:
        print(f"ValueError during image critique: {err_value}")
        error_for_this_op = f"Input error for critique: {str(err_value)}"
    except Exception as err_generic:
        print(
            f"Generic Exception during image critique: {type(err_generic).__name__}: {err_generic}"
        )
        error_for_this_op = f"Unexpected error during critique: {str(err_generic)}"
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        timing = f"Critique generation time: {execution_time:.2f} seconds"  # More precise timing
        print(timing)

        if error_for_this_op:  # If an error occurred specifically in this operation
            raise GenerationError(error_for_this_op)

    print("Critique generation function finished.")
    return critique_text


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def get_facial_composite_profile(image_bytes: bytes) -> FacialCompositeProfile:
    """Analyzes an image and returns a structured facial profile."""
    model_name = cfg.CHARACTER_CONSISTENCY_GEMINI_MODEL

    profile_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=FacialCompositeProfile.model_json_schema(),
        temperature=cfg.TEMP_FORENSIC_ANALYSIS,
    )
    profile_prompt_parts = [
        "You are a forensic analyst. Analyze the following image and extract a detailed, structured facial profile.",
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
    ]
    response = client.models.generate_content(
        model=model_name, contents=profile_prompt_parts, config=profile_config
    )
    return FacialCompositeProfile.model_validate_json(response.text)


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def get_natural_language_description(profile: FacialCompositeProfile) -> str:
    """Generates a natural language description from a facial profile."""
    model_name = cfg.CHARACTER_CONSISTENCY_GEMINI_MODEL

    description_config = types.GenerateContentConfig(
        temperature=cfg.TEMP_DESCRIPTION_TRANSLATION
    )
    description_prompt = f"""
    Based on the following structured JSON data of a person's facial features, write a concise, natural language description suitable for an image generation model. Focus on key physical traits.

    JSON Profile:
    {profile.model_dump_json(indent=2)}
    """
    response = client.models.generate_content(
        model=model_name, contents=[description_prompt], config=description_config
    )
    return response.text.strip()


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def generate_final_scene_prompt(
    base_description: str, user_prompt: str
) -> GeneratedPrompts:
    """
    Generates a detailed, photorealistic prompt to place a described person
    in a novel scene.
    """
    model_name = cfg.CHARACTER_CONSISTENCY_GEMINI_MODEL
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GeneratedPrompts.model_json_schema(),
        temperature=cfg.TEMP_SCENE_GENERATION,
    )

    meta_prompt = f"""
    You are an expert prompt engineer for a text-to-image generation model.
    Your task is to create a detailed, photorealistic prompt that places a specific person into a new scene.

    **Person Description:**
    {base_description}

    **User's Desired Scene:**
    {user_prompt}

    **Instructions:**
    1.  Combine the person's description with the user's scene to create a single, coherent, and highly detailed prompt.
    2.  The final image should be photorealistic. Add photography keywords like lens type (e.g., 85mm), lighting (e.g., cinematic lighting, soft light), and composition.
    3.  Ensure the final prompt clearly describes the person performing the action or being in the scene requested by the user.
    4.  Generate a standard negative prompt to avoid common artistic flaws.
    """

    response = client.models.generate_content(
        model=model_name, contents=[meta_prompt], config=config
    )
    return GeneratedPrompts.model_validate_json(response.text)


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def select_best_image(
    real_image_bytes_list: list[bytes],
    generated_image_bytes_list: list[bytes],
    generated_image_gcs_uris: list[str],
) -> BestImage:
    """Selects the best generated image by comparing it against a set of real
    images.
    """
    model = cfg.CHARACTER_CONSISTENCY_GEMINI_MODEL
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        response_mime_type="application/json",
        response_schema=BestImage.model_json_schema(),
        temperature=cfg.TEMP_BEST_IMAGE_SELECTION,
    )

    prompt_parts = [
        "Please analyze the following images. The first set of images are real photos of a person. The second set of images are AI-generated.",
        "Your task is to select the generated image that best represents the person from the real photos, focusing on facial and physical traits, not clothing or style.",
        "Provide the path of the best image and your reasoning.",
        "\n--- REAL IMAGES ---",
    ]

    for image_bytes in real_image_bytes_list:
        prompt_parts.append(
            types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        )

    prompt_parts.append("\n--- GENERATED IMAGES ---")

    for i, image_bytes in enumerate(generated_image_bytes_list):
        prompt_parts.append(f"Image path: {generated_image_gcs_uris[i]}")
        prompt_parts.append(
            types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        )

    response = client.models.generate_content(
        model=model, contents=prompt_parts, config=config
    )
    return BestImage.model_validate_json(response.text)


def select_best_image_with_description(
    real_image_bytes_list: list[bytes],
    generated_image_bytes_list: list[bytes],
    generated_image_gcs_uris: list[str],
    real_photo_description: str,
    ai_photo_description: str,
) -> BestImageAccuracy:
    """Selects the best generated image by comparing it against a set of real
    images.
    """
    model = cfg.CHARACTER_CONSISTENCY_GEMINI_MODEL
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        response_mime_type="application/json",
        response_schema=BestImageAccuracy.model_json_schema(),
        temperature=cfg.TEMP_BEST_IMAGE_SELECTION,
    )

    prompt_parts = [
        "Please analyze the following images. The first set of images are photos of {}. The second set of images are AI-generated images of a model wearing the articles of clothing.".format(
            real_photo_description
        ),
        "Your task is to select the generated image that best represents the {} from the real photos.".format(
            ai_photo_description
        ),
        "For each generated image, provide the analysis of True or False indicating if the generated image is accurate with overall reasoning. The single image you choose as the best should set best_image value to True.",
        "\n--- REAL IMAGES ---",
    ]

    for image_bytes in real_image_bytes_list:
        prompt_parts.append(
            types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        )

    prompt_parts.append("\n--- GENERATED IMAGES ---")

    for i, image_bytes in enumerate(generated_image_bytes_list):
        prompt_parts.append(f"Image path: {generated_image_gcs_uris[i]}")
        prompt_parts.append(
            types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        )

    response = client.models.generate_content(
        model=model, contents=prompt_parts, config=config
    )
    return BestImageAccuracy.model_validate_json(response.text)


def final_image_critic(
    article_image_bytes_list: list[bytes],
    article_image_gcs_uris: list[str],
    generated_image_bytes_list: list[bytes],
) -> GeneratedImageAccuracyWrapper:
    """Selects the best generated image by comparing it against a set of real
    images. Provide feedback on accuracy.
    """
    model = cfg.CHARACTER_CONSISTENCY_GEMINI_MODEL
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        response_mime_type="application/json",
        response_schema=GeneratedImageAccuracyWrapper.model_json_schema(),
        temperature=cfg.TEMP_BEST_IMAGE_SELECTION,
    )

    prompt_parts = [
        "The first set of images are photos of apparel items. The generated image is AI-generated image of a model wearing the apparel items.",
        "Your task is to determine if the AI-generated image reaslistically depicts all apparel items from the real photos.",
        "Provide the analysis of True or False, indicating if the generated image is accurate with overall reasoning. In addition provide detailed reasoning for each apparel item.",
        "\n--- APAREL IMAGES ---",
    ]

    for i, image_bytes in enumerate(article_image_bytes_list):
        prompt_parts.append(f"Image path: {article_image_gcs_uris[i]}")
        prompt_parts.append(
            types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        )

    prompt_parts.append("\n--- GENERATED IMAGE ---")

    for i, image_bytes in enumerate(generated_image_bytes_list):
        prompt_parts.append(
            types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        )

    response = client.models.generate_content(
        model=model, contents=prompt_parts, config=config
    )
    return GeneratedImageAccuracyWrapper.model_validate_json(response.text)


def describe_images_and_look(
    look_articles: list[CatalogRecord],
) -> ArticleDescriptionWrapper:
    """Describe the overall aestetic of an outfit in addition to describing
    each article seperately.
    """
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        response_mime_type="application/json",
        response_schema=ArticleDescriptionWrapper.model_json_schema(),
        temperature=cfg.TEMP_BEST_IMAGE_SELECTION,
    )
    model = cfg.CHARACTER_CONSISTENCY_GEMINI_MODEL

    prompt_parts = [
        "The following images of {} are articles of clothing to be worn as an outfit.".format(
            ",".join(i.article_type for i in look_articles)
        ),
        "Your task is describe each article of clothing in a style of a product catalog, within 3 sentences each.",
        "Also, you also should generate a description of the entire outfit as look_description when all articles are worn together as an outfit.",
        "\n--- ARTICLE IMAGES ---",
    ]

    for a in look_articles:
        prompt_parts.append(f"Article Image Path {a.clothing_image}")
        prompt_parts.append(
            types.Part.from_uri(file_uri=a.clothing_image, mime_type="image/png")
        )

    response = client.models.generate_content(
        model=model, contents=prompt_parts, config=config
    )

    return ArticleDescriptionWrapper.model_validate_json(response.text)


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def generate_transformation_prompts(image_uris: list[str]) -> list[Transformation]:
    """Generate three transformation prompts for a given image."""
    model_name = cfg.MODEL_ID
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TransformationPrompts.model_json_schema(),
        temperature=0.8,
    )

    prompt_text = """Analyze these images and come up with 3 interesting transformations.
    
    For each transformation, provide a short title (max 3 words) and a detailed prompt for the image generation model.
    
    Some example prompts might be
    * paper portrait: transform this image as if it were created with 3d paper overlays, with a modern color pallete
    * hologram: identify the main object in the scene and transform it into a hologram.
    * steampunk: Draw an ornate, glowing copper-colored outline with subtle gear motifs around the object 
    * enamel pinL turn the primary subject into an enamel pin
    * felt ornament: turn the primary subject into a felt ornament suitable for a holiday tree
    * mini snack food: Create a high-resolution image of a minimalist, realistic-looking miniature snack food. The snack should be held between a person's thumb and index finger. The style should be on a clean and white background with studio lighting, soft shadows, and shallow depth of field. The snack should appear extremely small but hyper-detailed and appear to be a professional-grade product image.
    * linkedin pop-out: A photorealistic portrait is presented within a #FFFFFF white circular frame. The image inside the circle captures the subject from the chest up. The subject is leaning his chin on his crossed arms, in a casual, relaxed style, as if looking out of a window. The subject's arms extend out of the circular boundary, overlapping the boundary. These arms, complete with hands, breach the edge of the white circle creating a compelling 3D pop-out effect. The arm MUST cross the boundary of the crop. The lighting is soft and even.
    
    """

    prompt_parts = [prompt_text]
    for uri in image_uris:
        prompt_parts.append(types.Part.from_uri(file_uri=uri, mime_type="image/png"))

    response = client.models.generate_content(
        model=model_name, contents=prompt_parts, config=config
    )

    prompts = TransformationPrompts.model_validate_json(response.text)
    return prompts.transformations


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def describe_image(image_uri: str) -> str:
    """Generates a two-sentence description for a given image."""
    model_name = cfg.MODEL_ID
    config = types.GenerateContentConfig(temperature=0.2)
    prompt_parts = [
        "Describe this image in two sentences.",
        types.Part.from_uri(file_uri=image_uri, mime_type="image/png"),
    ]
    response = client.models.generate_content(
        model=model_name, contents=prompt_parts, config=config
    )
    return response.text.strip()


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def describe_video(video_uri: str) -> str:
    """Generates a two-sentence description for a given video."""
    model_name = cfg.MODEL_ID
    config = types.GenerateContentConfig(temperature=0.2)
    prompt_parts = [
        "Describe this video in two sentences, focusing on the main subject, action, and overall visual style.",
        types.Part.from_uri(file_uri=video_uri, mime_type="video/mp4"),
    ]
    response = client.models.generate_content(
        model=model_name, contents=prompt_parts, config=config
    )
    return response.text.strip()


class QuestionAnswer(BaseModel):
    question: str
    answer: bool = Field(..., description="True for 'yes', False for 'no'.")


class EvaluationResult(BaseModel):
    answers: list[QuestionAnswer]


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def evaluate_media_with_questions(media_uri: str, mime_type: str, questions: list[str]) -> EvaluationResult:
    """Evaluates a media file against a list of yes/no questions."""
    model_name = cfg.MODEL_ID
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=EvaluationResult.model_json_schema(),
        temperature=0.1,
    )

    prompt = "For the following media, answer each of the following questions with a simple 'yes' or 'no'. Return the answers as a structured JSON list of question and answer pairs.\n\n"
    for q in questions:
        prompt += f"- {q}\n"

    prompt_parts = [
        prompt,
        types.Part.from_uri(file_uri=media_uri, mime_type=mime_type),
    ]

    response = client.models.generate_content(
        model=model_name, contents=prompt_parts, config=config
    )

    return EvaluationResult.model_validate_json(response.text)


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def evaluate_image_with_questions(image_uri: str, questions: list[str]) -> EvaluationResult:
    """Evaluates an image against a list of yes/no questions."""
    model_name = cfg.MODEL_ID
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=EvaluationResult.model_json_schema(),
        temperature=0.1,
    )

    prompt = "For the following image, answer each of the following questions with a simple 'yes' or 'no'. Return the answers as a structured JSON list of question and answer pairs.\n\n"
    for q in questions:
        prompt += f"- {q}\n"

    prompt_parts = [
        prompt,
        types.Part.from_uri(file_uri=image_uri, mime_type="image/png"),
    ]

    response = client.models.generate_content(
        model=model_name, contents=prompt_parts, config=config
    )

    return EvaluationResult.model_validate_json(response.text)


class CritiqueQuestion(BaseModel):
    question: str = Field(..., description="A yes/no question to evaluate an image.")

class CritiqueQuestionList(BaseModel):
    questions: list[CritiqueQuestion] = Field(..., max_length=5, min_length=5)


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def generate_critique_questions(prompt: str, image_descriptions: list[str]) -> list[str]:
    """Generates 5 yes/no questions based on a prompt and image descriptions."""
    model_name = cfg.MODEL_ID
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=CritiqueQuestionList.model_json_schema(),
        temperature=0.5,
    )

    meta_prompt = "Using the following prompt and the description of each image, come up with 5 yes/no questions that we could ask of the resulting image that would identify whether the generated images meets the intent of the user based upon the following:\n\n"
    meta_prompt += f"Prompt: {prompt}\n\n"

    for i, desc in enumerate(image_descriptions):
        meta_prompt += f"Image {i+1} description: {desc}\n"
    
    response = client.models.generate_content(
        model=model_name, contents=[meta_prompt], config=config
    )

    question_list = CritiqueQuestionList.model_validate_json(response.text)
    return [q.question for q in question_list.questions]


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def generate_text(prompt: str, images: list[str]) -> tuple[str, float]:
    """Generates text from a prompt and a list of media files."""
    print(f"Entering generate_text with prompt: {prompt} and {len(images)} images.")
    start_time = time.time()
    model_name = cfg.MODEL_ID

    parts = [types.Part.from_text(text=prompt)]
    for image_uri in images:
        # More robust mime type detection
        if any(image_uri.lower().endswith(ext) for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]):
            mime_type = "video/mp4" # General video type
        elif any(image_uri.lower().endswith(ext) for ext in [".wav", ".mp3", ".flac"]):
            mime_type = "audio/wav" # General audio type
        elif any(image_uri.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
            mime_type = "image/png" # General image type
        elif image_uri.lower().endswith(".pdf"):
            mime_type = "application/pdf"
        else:
            # Fallback for unknown types, though this may still cause errors
            mime_type = "application/octet-stream"
        
        parts.append(types.Part.from_uri(file_uri=image_uri, mime_type=mime_type))
    
    print(f"Constructed parts for Gemini API: {parts}")

    contents = [types.Content(role="user", parts=parts)]

    client = GeminiModelSetup.init(
        location=cfg.LOCATION,
    )

    print(f"Sending request to model: {model_name}")
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
    )
    print(f"Received raw response from model: {response}")
    
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Returning text: {response.text}, execution_time: {execution_time}")
    return response.text, execution_time
