import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.vto import generate_vto_image

PERSON_IMAGE = os.environ.get("PERSON_IMAGE", "gs://genai-blackbelt-fishfooding-assets/vto_person_images/vto_model_001.png")
PRODUCT_IMAGE = os.environ.get("PRODUCT_IMAGE", "gs://genai-blackbelt-fishfooding-assets/vto_product_images/product_boho_blouse.png")

def test_generate_vto_image_aiplatform():
    """Tests the generate_vto_image function using the aiplatform client."""
    # The original function expects base_steps as an argument.
    # We will use a default value of 50 for this test.
    gcs_uris = generate_vto_image(PERSON_IMAGE, PRODUCT_IMAGE, 1, 50)
    assert len(gcs_uris) == 1
    for uri in gcs_uris:
        assert uri.startswith("gs://")

    print(f"Generated {len(gcs_uris)} images:")
    for uri in gcs_uris:
        print(uri)
