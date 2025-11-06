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

import datetime
import logging

from common.metadata import MediaItem, add_media_item_to_firestore, get_media_item_by_id
from models.requests import VideoGenerationRequest
from models.veo import generate_video
from config.veo_models import get_veo_model_config

logger = logging.getLogger(__name__)

def process_veo_generation_task(
    job_id: str, request_data: VideoGenerationRequest, user_email: str
):
    """
    Background task to process Veo video generation.
    Updates Firestore with status changes.
    """
    logger.info(f"Starting background task for job {job_id}")

    try:
        # 1. Update status to 'processing'
        _update_job_status(job_id, "processing")

        # 2. Perform the actual heavy lifting (synchronous call)
        video_uris, resolution = generate_video(request_data)

        # 3. Success! Update Firestore with results.
        _complete_job(job_id, video_uris, resolution)
        logger.info(f"Background task for job {job_id} completed successfully.")

    except Exception as e:
        logger.error(f"Background task for job {job_id} failed: {e}")
        _fail_job(job_id, str(e))


def _update_job_status(job_id: str, status: str):
    """Helper to update just the status of a job."""
    item = get_media_item_by_id(job_id)
    if item:
        item.status = status
        add_media_item_to_firestore(item)


def _complete_job(job_id: str, video_uris: list[str], resolution: str):
    """Helper to mark a job as complete with results."""
    item = get_media_item_by_id(job_id)
    if item:
        item.status = "complete"
        item.gcs_uris = video_uris
        item.gcsuri = video_uris[0] if video_uris else None
        item.resolution = resolution
        # Calculate generation time if possible, or just use now - timestamp
        if item.timestamp:
             # Ensure both are offset-aware or both are offset-naive.
             # Firestore timestamps are usually UTC.
             now = datetime.datetime.now(datetime.timezone.utc)
             # Handle potential string timestamp from legacy data if not fully parsed
             start_time = item.timestamp
             if isinstance(start_time, str):
                 try:
                     start_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                 except ValueError:
                     start_time = now # Fallback

             item.generation_time = (now - start_time).total_seconds()

        add_media_item_to_firestore(item)


def _fail_job(job_id: str, error_message: str):
    """Helper to mark a job as failed."""
    item = get_media_item_by_id(job_id)
    if item:
        item.status = "failed"
        item.error_message = error_message
        add_media_item_to_firestore(item)


def create_initial_job(request: VideoGenerationRequest, user_email: str) -> str:
    """Creates the initial 'pending' MediaItem in Firestore and returns its ID."""
    model_config = get_veo_model_config(request.model_version_id)
    model_name = model_config.model_name if model_config else request.model_version_id

    item = MediaItem(
        user_email=user_email,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        status="pending",
        prompt=request.prompt,
        model=model_name,
        mime_type="video/mp4",
        # We might not know the final mode here if it was inferred,
        # but we can try to guess based on inputs or pass it in.
        # For simplicity, let's leave it generic or pass it if available.
        # mode=request.mode, # Request doesn't have mode directly, it's inferred.
        aspect=request.aspect_ratio,
        duration=float(request.duration_seconds),
        reference_image=request.reference_image_gcs,
        last_reference_image=request.last_reference_image_gcs,
        negative_prompt=request.negative_prompt,
        enhanced_prompt_used=request.enhance_prompt,
    )
    add_media_item_to_firestore(item)
    return item.id
