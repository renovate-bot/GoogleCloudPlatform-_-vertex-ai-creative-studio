import base64
from google.cloud import aiplatform
from config.default import Default
from common.storage import store_to_gcs

cfg = Default()

def generate_vto_image(person_gcs_url: str, product_gcs_url: str, sample_count: int, base_steps: int) -> list[str]:
    """Generates a VTO image."""

    client_options = {"api_endpoint": f"{cfg.LOCATION}-aiplatform.googleapis.com"}
    client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)

    model_endpoint = f"projects/{cfg.PROJECT_ID}/locations/{cfg.LOCATION}/publishers/google/models/{cfg.VTO_MODEL_ID}"

    instance = {
        "personImage": {"image": {"gcsUri": person_gcs_url.replace("https://storage.mtls.cloud.google.com/", "gs://")}},
        "productImages": [{"image": {"gcsUri": product_gcs_url.replace("https://storage.mtls.cloud.google.com/", "gs://")}}],
    }

    parameters = {
        "sampleCount": sample_count,
        "baseSteps": base_steps,
    }

    response = client.predict(
        endpoint=model_endpoint, instances=[instance], parameters=parameters
    )

    gcs_uris = []
    for i, prediction in enumerate(response.predictions):
        encoded_mask_string = prediction["bytesBase64Encoded"]
        mask_bytes = base64.b64decode(encoded_mask_string)

        # Store the generated image to GCS
        gcs_uri = store_to_gcs(
            folder="vto_results",
            file_name=f"vto_result_{i}.png",
            mime_type="image/png",
            contents=mask_bytes,
            decode=False, # Already decoded
        )
        gcs_uris.append(f"gs://{gcs_uri}")

    return gcs_uris