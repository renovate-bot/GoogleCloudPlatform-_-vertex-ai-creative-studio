# Copyright 2026 Google LLC
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

import pytest
import os
import sys
import time
from unittest.mock import patch, MagicMock

# Setup sys.path to allow imports from the parent directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.veo import generate_video
from models.requests import VideoGenerationRequest, APIReferenceImage
from config.default import Default

config = Default()

@pytest.fixture
def r2v_request():
    """Provides a base R2V request for tests."""
    return VideoGenerationRequest(
        prompt="a cinematic video of a futuristic city",
        duration_seconds=8,
        video_count=1,
        aspect_ratio="16:9",
        resolution="1080p",
        enhance_prompt=True,
        model_version_id="3.1-fast",
        person_generation="Allow (All ages)",
        r2v_references=[
            APIReferenceImage(
                gcs_uri="gs://cloud-samples-data/generative-ai/image/flowers.png",
                mime_type="image/png"
            )
        ],
        rewriter_type=None
    )

@pytest.mark.integration
def test_veo_31_r2v_9_16(r2v_request):
    """Tests R2V with the new 9:16 aspect ratio."""
    r2v_request.aspect_ratio = "9:16"
    r2v_request.model_version_id = "3.1-fast"
    
    video_uris, resolution = generate_video(r2v_request)
    
    assert video_uris
    assert len(video_uris) > 0
    assert video_uris[0].startswith("gs://")
    assert resolution == "1080p"
    print(f"Generated 9:16 R2V video: {video_uris[0]}")

@pytest.mark.integration
def test_veo_31_4k_upscaler(r2v_request):
    """Tests the new 4K resolution upscaler."""
    r2v_request.resolution = "4k"
    r2v_request.model_version_id = "3.1"
    r2v_request.r2v_references = None # Standard T2V
    
    video_uris, resolution = generate_video(r2v_request)
    
    assert video_uris
    assert len(video_uris) > 0
    assert video_uris[0].startswith("gs://")
    assert resolution == "4k"
    print(f"Generated 4K video: {video_uris[0]}")

@pytest.mark.integration
def test_veo_31_social_rewriter(r2v_request):
    """Tests the new Social Rewriter feature for R2V."""
    r2v_request.rewriter_type = "social"
    r2v_request.model_version_id = "3.1-fast"
    
    # This test will also validate if 'prompt_rewriter': 'social' is accepted by the API
    video_uris, resolution = generate_video(r2v_request)
    
    assert video_uris
    assert len(video_uris) > 0
    assert video_uris[0].startswith("gs://")
    print(f"Generated Social Rewriter video: {video_uris[0]}")

if __name__ == "__main__":
    # If run directly, execute the tests
    pytest.main([__file__, "-m", "integration", "-s"])
