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

import uuid
import time
import logging
from dataclasses import dataclass

from common.analytics import track_model_call
from config.default import Default as cfg
from models.gemini import generate_image_from_prompt_and_images, generate_text
from models.veo import generate_video, VideoGenerationRequest
from models.requests import APIReferenceImage
from models.video_processing import process_videos
from workflows.retro_games_config import RetroGameConfig

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class RetroGameWorkflowState:
    workflow_id: str
    user_email: str
    theme: str 
    input_image_uri: str
    
    # Step 1 outputs
    eight_bit_image_uri: str | None = None
    
    # Step 2 outputs
    character_sheet_uri: str | None = None
    
    # Step 3 outputs
    scene_direction: str | None = None
    raw_video_uri: str | None = None
    
    # Step 4 outputs
    final_video_uri: str | None = None
    
    status: str = "initialized"
    error_message: str | None = None

def initialize_workflow(user_email: str, theme: str, input_image_uri: str) -> RetroGameWorkflowState:
    return RetroGameWorkflowState(
        workflow_id=str(uuid.uuid4()),
        user_email=user_email,
        theme=theme,
        input_image_uri=input_image_uri,
    )

def step_1_generate_8bit(state: RetroGameWorkflowState) -> RetroGameWorkflowState:
    """Generates an 8-bit version of the input image based on the theme."""
    state.status = "generating_8bit"
    
    config = RetroGameConfig()
    full_prompt = config.get_theme_prompt(state.theme)
    
    if not full_prompt:
        state.status = "error"
        state.error_message = f"Theme '{state.theme}' not found in configuration."
        return state
    
    max_retries = 3
    for attempt in range(max_retries):
        logger.info(f"Workflow {state.workflow_id}: Step 1 (8-bit generation) attempt {attempt + 1}/{max_retries}")
        try:
            gcs_uris, _, _, _ = generate_image_from_prompt_and_images(
                prompt=full_prompt,
                images=[state.input_image_uri],
                aspect_ratio="1:1", # Assuming 1:1 for now, could be made dynamic
                gcs_folder="retro_games_8bit",
            )
            
            if gcs_uris:
                state.eight_bit_image_uri = gcs_uris[0]
                state.status = "8bit_generated"
                return state
            else:
                logger.warning(f"Workflow {state.workflow_id}: Step 1 attempt {attempt + 1} returned no images.")
                
        except Exception as e:
            logger.warning(f"Workflow {state.workflow_id}: Step 1 attempt {attempt + 1} failed: {e}")
            time.sleep(1) # Wait a bit before retry

    state.status = "error"
    state.error_message = "Failed to generate 8-bit image after multiple attempts."
    logger.error(f"Workflow {state.workflow_id} Step 1 failed after {max_retries} attempts.")
    return state

def step_2_generate_character_sheet(state: RetroGameWorkflowState) -> RetroGameWorkflowState:
    """Generates a character sheet from the 8-bit image."""
    if not state.eight_bit_image_uri:
        state.status = "error"
        state.error_message = "Cannot start Step 2: 8-bit image missing."
        return state
        
    state.status = "generating_char_sheet"
    logger.info(f"Workflow {state.workflow_id}: Starting Step 2 (Character Sheet)")
    
    prompt = "Create a retro game character sheet for this character. Include front, side, and back views, and a few action poses (idle, walk, jump). Pixel art style matching the input."
    
    try:
        gcs_uris, _, _, _ = generate_image_from_prompt_and_images(
            prompt=prompt,
            images=[state.eight_bit_image_uri],
            aspect_ratio="1:1", # Character sheets are often square-ish
            gcs_folder="retro_games_charsheets",
        )
        
        if gcs_uris:
            state.character_sheet_uri = gcs_uris[0]
            state.status = "char_sheet_generated"
        else:
            state.status = "error"
            state.error_message = "Failed to generate character sheet."
            
    except Exception as e:
        state.status = "error"
        state.error_message = f"Error in Step 2: {str(e)}"
        logger.error(f"Workflow {state.workflow_id} Step 2 failed: {e}")
        
    return state

def step_3_generate_video(state: RetroGameWorkflowState) -> RetroGameWorkflowState:
    """Generates a video using Veo, guided by a Gemini-generated scene direction."""
    if not state.eight_bit_image_uri:
         state.status = "error"
         state.error_message = "Cannot start Step 3: 8-bit image missing."
         return state
    if not state.character_sheet_uri:
         state.status = "error"
         state.error_message = "Cannot start Step 3: Character sheet missing."
         return state

    state.status = "generating_scene_direction"
    logger.info(f"Workflow {state.workflow_id}: Starting Step 3 (Scene Direction)")
    
    # Sub-step 3a: Generate Scene Direction
    direction_prompt = "Write a short, exciting scene direction for an 8-second retro video game clip featuring this character. Describe the action, the environment, and the retro game 'feel'. Mention that the game's logo should be visible in the environment (e.g., on a wall, a flag, or as a UI element). Keep it under 150 words."
    
    try:
        scene_direction, _ = generate_text(
            prompt=direction_prompt,
            images=[state.eight_bit_image_uri]
        )
        state.scene_direction = scene_direction
        logger.info(f"Workflow {state.workflow_id}: Scene Direction generated: {scene_direction}")
        
    except Exception as e:
        state.status = "error"
        state.error_message = f"Error in Step 3a (Scene Direction): {str(e)}"
        logger.error(f"Workflow {state.workflow_id} Step 3a failed: {e}")
        return state

    # Sub-step 3b: Generate Video with Veo
    state.status = "generating_video"
    logger.info(f"Workflow {state.workflow_id}: Starting Step 3b (Veo Video)")
    
    try:
        config = RetroGameConfig()
        theme_logo_uri = config.get_theme_8bit_logo(state.theme)
        
        if not theme_logo_uri:
             state.status = "error"
             state.error_message = f"8-bit logo for theme '{state.theme}' not found."
             return state

        # Use R2V for Veo 3.1 Preview with 8s duration and 3 reference images
        request = VideoGenerationRequest(
            prompt=state.scene_direction,
            r2v_references=[
                APIReferenceImage(gcs_uri=state.eight_bit_image_uri, mime_type="image/png"),
                APIReferenceImage(gcs_uri=state.character_sheet_uri, mime_type="image/png"),
                APIReferenceImage(gcs_uri=theme_logo_uri, mime_type="image/png")
            ],
            duration_seconds=8,
            aspect_ratio="16:9",
            model_version_id="3.1-preview",
            video_count=1,
            resolution="720p",
            enhance_prompt=True,
            person_generation="allow_all"
        )
        
        video_uris, _ = generate_video(request)
        
        if video_uris:
            state.raw_video_uri = video_uris[0]
            state.status = "video_generated"
        else:
            state.status = "error"
            state.error_message = "Failed to generate video."
            
    except Exception as e:
        state.status = "error"
        state.error_message = f"Error in Step 3b (Veo): {str(e)}"
        logger.error(f"Workflow {state.workflow_id} Step 3b failed: {e}")
        
    return state

def step_4_append_bumper(state: RetroGameWorkflowState) -> RetroGameWorkflowState:
    """Appends a bumper video to the generated video."""
    if not state.raw_video_uri:
        state.status = "error"
        state.error_message = "Cannot start Step 4: Raw video missing."
        return state
        
    state.status = "appending_bumper"
    logger.info(f"Workflow {state.workflow_id}: Starting Step 4 (Appending Bumper)")
    
    try:
        config = RetroGameConfig()
        bumper_uri = config.get_random_bumper()
        
        if not bumper_uri:
             # If no bumper is configured, just use the raw video? 
             # Or fail? Let's log a warning and skip appending.
             logger.warning(f"Workflow {state.workflow_id}: No bumper videos configured. Skipping append.")
             state.final_video_uri = state.raw_video_uri
             state.status = "completed"
             return state

        logger.info(f"Workflow {state.workflow_id}: Selected bumper: {bumper_uri}")
        
        final_video_uri = process_videos(
            video_gcs_uris=[state.raw_video_uri, bumper_uri],
            transition="concat"
        )
        
        state.final_video_uri = final_video_uri
        state.status = "completed"
        
    except Exception as e:
        state.status = "error"
        state.error_message = f"Error in Step 4 (Bumper): {str(e)}"
        logger.error(f"Workflow {state.workflow_id} Step 4 failed: {e}")
        
    return state

def run_full_workflow(user_email: str, theme: str, input_image_uri: str) -> RetroGameWorkflowState:
    """Runs the full workflow synchronously (blocking)."""
    state = initialize_workflow(user_email, theme, input_image_uri)
    
    state = step_1_generate_8bit(state)
    if state.status == "error": return state
    
    state = step_2_generate_character_sheet(state)
    if state.status == "error": return state
    
    state = step_3_generate_video(state)
    if state.status == "error": return state
    
    state = step_4_append_bumper(state)
    
    return state
