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
import io
from dataclasses import dataclass
from PIL import Image

from common.analytics import track_model_call
from common.storage import download_from_gcs, store_to_gcs
from config.default import Default as cfg
from models.gemini import generate_image_from_prompt_and_images, generate_text
from models.veo import generate_video, VideoGenerationRequest
from models.requests import APIReferenceImage
from models.video_processing import process_videos
from workflows.retro_games.retro_games_config import RetroGameConfig

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class RetroGameWorkflowState:
    workflow_id: str
    user_email: str
    theme: str 
    
    # Inputs
    player1_image_uri: str
    player2_image_uri: str | None = None
    
    # Configuration
    theme_context: str = ""
    include_bumper: bool = True
    model_version: str = "veo-3.1-preview"
    duration: int = 8
    
    # Step 1 outputs (8-bit)
    player1_8bit_uri: str | None = None
    player2_8bit_uri: str | None = None
    
    # Step 2 outputs (Character Sheets)
    player1_sheet_uri: str | None = None
    player2_sheet_uri: str | None = None
    
    # Step 3 outputs
    scene_direction: str | None = None
    raw_video_uri: str | None = None
    
    # Step 4 outputs
    final_video_uri: str | None = None
    
    status: str = "initialized"
    error_message: str | None = None

def initialize_workflow(
    user_email: str, 
    theme: str, 
    player1_image_uri: str,
    player2_image_uri: str | None = None,
    theme_context: str = "",
    include_bumper: bool = True,
    model_version: str = "veo-3.1-preview",
    duration: int = 8
) -> RetroGameWorkflowState:
    return RetroGameWorkflowState(
        workflow_id=str(uuid.uuid4()),
        user_email=user_email,
        theme=theme,
        player1_image_uri=player1_image_uri,
        player2_image_uri=player2_image_uri,
        theme_context=theme_context,
        include_bumper=include_bumper,
        model_version=model_version,
        duration=duration
    )

def step_1_generate_8bit(state: RetroGameWorkflowState) -> RetroGameWorkflowState:
    """Generates 8-bit versions of the input images based on the theme."""
    state.status = "generating_8bit"
    
    config = RetroGameConfig()
    theme_prompt_part = config.get_theme_prompt(state.theme)
    base_prompt = config.get_prompt("8bit_generation")
    
    full_prompt = base_prompt.format(theme_prompt=theme_prompt_part)
    
    if not theme_prompt_part:
        state.status = "error"
        state.error_message = f"Theme '{state.theme}' not found in configuration."
        return state
    
    # Helper to generate for one image
    def _gen_one(input_uri, folder):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                gcs_uris, _, _, _ = generate_image_from_prompt_and_images(
                    prompt=full_prompt,
                    images=[input_uri],
                    aspect_ratio="1:1",
                    gcs_folder=folder,
                )
                if gcs_uris: return gcs_uris[0]
            except Exception as e:
                logger.warning(f"Workflow {state.workflow_id}: 8-bit gen attempt {attempt + 1} failed: {e}")
                time.sleep(1)
        return None

    # Player 1
    logger.info(f"Workflow {state.workflow_id}: Generating P1 8-bit...")
    p1_uri = _gen_one(state.player1_image_uri, "retro_games_8bit_p1")
    if not p1_uri:
        state.status = "error"
        state.error_message = "Failed to generate Player 1 8-bit image."
        return state
    state.player1_8bit_uri = p1_uri

    # Player 2 (Optional)
    if state.player2_image_uri:
        logger.info(f"Workflow {state.workflow_id}: Generating P2 8-bit...")
        p2_uri = _gen_one(state.player2_image_uri, "retro_games_8bit_p2")
        if not p2_uri:
            state.status = "error"
            state.error_message = "Failed to generate Player 2 8-bit image."
            return state
        state.player2_8bit_uri = p2_uri

    state.status = "8bit_generated"
    return state

def step_2_generate_character_sheet(state: RetroGameWorkflowState) -> RetroGameWorkflowState:
    """Generates character sheets from the 8-bit images."""
    if not state.player1_8bit_uri:
        state.status = "error"
        state.error_message = "Cannot start Step 2: P1 8-bit image missing."
        return state
        
    state.status = "generating_char_sheet"
    logger.info(f"Workflow {state.workflow_id}: Starting Step 2 (Character Sheets)")
    
    config = RetroGameConfig()
    prompt = config.get_prompt("character_sheet")
    
    def _gen_sheet(input_uri, folder):
        try:
            gcs_uris, _, _, _ = generate_image_from_prompt_and_images(
                prompt=prompt,
                images=[input_uri],
                aspect_ratio="1:1",
                gcs_folder=folder,
            )
            if gcs_uris: return gcs_uris[0]
        except Exception as e:
            logger.error(f"Workflow {state.workflow_id} Step 2 gen failed: {e}")
        return None

    # Player 1
    p1_sheet = _gen_sheet(state.player1_8bit_uri, "retro_games_charsheets_p1")
    if not p1_sheet:
        state.status = "error"
        state.error_message = "Failed to generate P1 character sheet."
        return state
    state.player1_sheet_uri = p1_sheet

    # Player 2
    if state.player2_8bit_uri:
        p2_sheet = _gen_sheet(state.player2_8bit_uri, "retro_games_charsheets_p2")
        if not p2_sheet:
            state.status = "error"
            state.error_message = "Failed to generate P2 character sheet."
            return state
        state.player2_sheet_uri = p2_sheet

    state.status = "char_sheet_generated"
    return state

def create_composite_image(image1_uri: str, image2_uri: str) -> str | None:
    """Combines two images side-by-side."""
    try:
        img1_bytes = download_from_gcs(image1_uri)
        img2_bytes = download_from_gcs(image2_uri)
        
        img1 = Image.open(io.BytesIO(img1_bytes))
        img2 = Image.open(io.BytesIO(img2_bytes))
        
        # Resize to match height
        target_height = max(img1.height, img2.height)
        if img1.height != target_height:
            ratio = target_height / img1.height
            img1 = img1.resize((int(img1.width * ratio), target_height))
        if img2.height != target_height:
            ratio = target_height / img2.height
            img2 = img2.resize((int(img2.width * ratio), target_height))
            
        # Combine
        total_width = img1.width + img2.width
        new_img = Image.new('RGB', (total_width, target_height))
        new_img.paste(img1, (0, 0))
        new_img.paste(img2, (img1.width, 0))
        
        # Save
        output_bytes = io.BytesIO()
        new_img.save(output_bytes, format='PNG')
        return store_to_gcs("retro_games_composites", f"composite_{uuid.uuid4()}.png", "image/png", output_bytes.getvalue())
    except Exception as e:
        logger.error(f"Composite creation failed: {e}")
        return None

def step_3_generate_video(state: RetroGameWorkflowState) -> RetroGameWorkflowState:
    """Generates a video using Veo, guided by a Gemini-generated scene direction."""
    if not state.player1_8bit_uri:
         state.status = "error"
         state.error_message = "Cannot start Step 3: P1 8-bit image missing."
         return state
    if not state.player1_sheet_uri:
         state.status = "error"
         state.error_message = "Cannot start Step 3: P1 Character sheet missing."
         return state

    state.status = "generating_scene_direction"
    logger.info(f"Workflow {state.workflow_id}: Starting Step 3 (Scene Direction)")
    
    # Sub-step 3a: Generate Scene Direction
    config = RetroGameConfig()
    base_direction_prompt = config.get_prompt("scene_direction")
    
    # Inject theme context if provided
    context_str = f" The scene should be set {state.theme_context}." if state.theme_context else ""
    
    # Update prompt for two players
    char_desc = "this character"
    if state.player2_8bit_uri:
        char_desc = "these two characters interacting or fighting"
    
    # We might need a better prompt template for 2 players, but let's hack it for now or update prompts.json
    # Ideally, prompts.json should have 'scene_direction_single' and 'scene_direction_multi'.
    # For now, I'll rely on the generic 'featuring this character' being adaptable or update the string logic.
    # Let's update the injection.
    
    direction_prompt = base_direction_prompt.format(duration=state.duration, theme_context=context_str).replace("this character", char_desc)
    
    try:
        input_images = [state.player1_8bit_uri]
        if state.player2_8bit_uri:
            input_images.append(state.player2_8bit_uri)

        scene_direction, _ = generate_text(
            prompt=direction_prompt,
            images=input_images
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
        theme_logo_uri = config.get_theme_8bit_logo(state.theme)
        
        if not theme_logo_uri:
             state.status = "error"
             state.error_message = f"8-bit logo for theme '{state.theme}' not found."
             return state

        # Determine Reference Images
        r2v_references = []
        
        if state.player2_8bit_uri and state.player2_sheet_uri:
            # Two Player Mode: Use Composite Images to save slots
            # Limit is 3. Logo takes 1. We have 2 slots left.
            # Slot 1: P1 Composite. Slot 2: P2 Composite.
            logger.info(f"Workflow {state.workflow_id}: Creating composites for 2-player mode")
            
            p1_composite = create_composite_image(state.player1_8bit_uri, state.player1_sheet_uri)
            p2_composite = create_composite_image(state.player2_8bit_uri, state.player2_sheet_uri)
            
            if not p1_composite or not p2_composite:
                state.status = "error"
                state.error_message = "Failed to create composite images for 2-player mode."
                return state
                
            r2v_references = [
                APIReferenceImage(gcs_uri=p1_composite, mime_type="image/png"),
                APIReferenceImage(gcs_uri=p2_composite, mime_type="image/png"),
                APIReferenceImage(gcs_uri=theme_logo_uri, mime_type="image/png")
            ]
        else:
            # Single Player Mode: Standard Refs
            r2v_references = [
                APIReferenceImage(gcs_uri=state.player1_8bit_uri, mime_type="image/png"),
                APIReferenceImage(gcs_uri=state.player1_sheet_uri, mime_type="image/png"),
                APIReferenceImage(gcs_uri=theme_logo_uri, mime_type="image/png")
            ]

        # Use R2V with configured duration and model
        request = VideoGenerationRequest(
            prompt=state.scene_direction,
            r2v_references=r2v_references,
            duration_seconds=state.duration,
            aspect_ratio="16:9",
            model_version_id=state.model_version,
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
        
    # Check if bumper is requested
    if not state.include_bumper:
        logger.info(f"Workflow {state.workflow_id}: Bumper skipped by user request.")
        state.final_video_uri = state.raw_video_uri
        state.status = "completed"
        return state

    state.status = "appending_bumper"
    logger.info(f"Workflow {state.workflow_id}: Starting Step 4 (Appending Bumper)")
    
    try:
        config = RetroGameConfig()
        bumper_uri = config.get_random_bumper()
        
        if not bumper_uri:
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
