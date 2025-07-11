

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pages.portraits import generate_scene_direction

# Use an existing test image for consistency


def test_generate_scene_direction(gcs_bucket_for_tests):
    """Tests the generate_scene_direction function."""
    prompt = "A close-up shot of a person smiling."
    image_uri = f"{gcs_bucket_for_tests}/vto_person_images/vto_model_001.png"
    mime_type = "image/png"

    scene_direction = generate_scene_direction(prompt, image_uri, mime_type)

    assert isinstance(scene_direction, str)
    assert len(scene_direction) > 0
    print(f"Successfully generated scene direction:\n{scene_direction}")

