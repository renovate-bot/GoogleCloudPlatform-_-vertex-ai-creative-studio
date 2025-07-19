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

import base64
import uuid

from google import genai
from google.api_core.exceptions import GoogleAPIError
from google.cloud import aiplatform

from common.storage import store_to_gcs
from config.default import Default
from models.model_setup import GeminiModelSetup

cfg = Default()


def generate_vto_image_genai(
    person_gcs_url: str, product_gcs_url: str, sample_count: int
) -> list[str]:
    """Generates a VTO image using the google.genai client."""
    client = GeminiModelSetup.init()
    model_name = f"publishers/google/models/{cfg.VTO_MODEL_ID}"

    person_image_part = genai.types.Part.from_uri(
        file_uri=person_gcs_url,
        mime_type="image/png",
    )
    product_image_part = genai.types.Part.from_uri(
        file_uri=product_gcs_url,
        mime_type="image/png",
    )

    # Call generate_content on the client's model endpoint, not a GenerativeModel instance
    response = client.models.generate_content(
        model=model_name,
        contents=[person_image_part, product_image_part],
    )

    gcs_uris = []
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if part.file_data:
                print(f"{part.file_data.uri}")
                gcs_uris.append(part.file_data.uri)

    return gcs_uris


def generate_vto_image(
    person_gcs_url: str, product_gcs_url: str, sample_count: int, base_steps: int
) -> list[str]:
    """Generates a VTO image."""

    try:
        client_options = {"api_endpoint": f"{cfg.LOCATION}-aiplatform.googleapis.com"}
        client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
    except Exception as client_err:
        print(f"Failed to create PredictionServiceClient: {client_err}")
        raise ValueError(
            f"Configuration error: Failed to initialize prediction client. Details: {str(client_err)}"
        ) from client_err

    model_endpoint = f"projects/{cfg.PROJECT_ID}/locations/{cfg.LOCATION}/publishers/google/models/{cfg.VTO_MODEL_ID}"

    instance = {
        "personImage": {
            "image": {
                "gcsUri": person_gcs_url.replace(
                    "https://storage.mtls.cloud.google.com/", "gs://"
                )
            }
        },
        "productImages": [
            {
                "image": {
                    "gcsUri": product_gcs_url.replace(
                        "https://storage.mtls.cloud.google.com/", "gs://"
                    )
                }
            }
        ],
    }

    parameters = {
        "sampleCount": sample_count,
        "baseSteps": base_steps,
    }

    try:
        response = client.predict(
            endpoint=model_endpoint, instances=[instance], parameters=parameters
        )

        if not response.predictions:
            raise ValueError(
                "VTO API returned an unexpected response (no predictions)."
            )

        gcs_uris = []
        unique_id = uuid.uuid4()
        for i, prediction in enumerate(response.predictions):
            if not prediction.get("bytesBase64Encoded"):
                raise ValueError("VTO API returned a prediction with no image data.")

            encoded_mask_string = prediction["bytesBase64Encoded"]
            mask_bytes = base64.b64decode(encoded_mask_string)

            gcs_uri = store_to_gcs(
                folder="vto_results",
                file_name=f"vto_result_{unique_id}-{i}_.png",
                mime_type="image/png",
                contents=mask_bytes,
                decode=False,
            )
            gcs_uris.append(gcs_uri)

        return gcs_uris

    except GoogleAPIError as e:
        error_message = f"VTO API Error: {str(e)}"
        print(error_message)
        raise ValueError(error_message) from e
    except Exception as e:
        error_message = (
            f"An unexpected error occurred during VTO image generation: {str(e)}"
        )
        print(error_message)
        raise Exception(error_message) from e
