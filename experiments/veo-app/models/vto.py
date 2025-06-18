import base64
from google.cloud import aiplatform
from config.default import Default
from common.storage import store_to_gcs

cfg = Default()

def generate_vto_image(person_gcs_url: str, product_gcs_url: str) -> str:
    """Generates a VTO image."""

    client_options = {"api_endpoint": f"{cfg.LOCATION}-aiplatform.googleapis.com"}
    client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)

    model_endpoint = f"projects/{cfg.PROJECT_ID}/locations/{cfg.LOCATION}/publishers/google/models/{cfg.VTO_MODEL_ID}"

    instance = {
        "personImage": {"image": {"gcsUri": person_gcs_url.replace("https://storage.mtls.cloud.google.com/", "gs://")}},
        "productImages": [{"image": {"gcsUri": product_gcs_url.replace("https://storage.mtls.cloud.google.com/", "gs://")}}],
    }

    response = client.predict(
        endpoint=model_endpoint, instances=[instance], parameters={}
    )

    encoded_mask_string = response.predictions[0]["bytesBase64Encoded"]
    mask_bytes = base64.b64decode(encoded_mask_string)

    # Store the generated image to GCS
    gcs_uri = store_to_gcs(
        folder="vto_results",
        file_name="vto_result.png",
        mime_type="image/png",
        contents=mask_bytes,
        decode=False, # Already decoded
    )

    return f"gs://{gcs_uri}"