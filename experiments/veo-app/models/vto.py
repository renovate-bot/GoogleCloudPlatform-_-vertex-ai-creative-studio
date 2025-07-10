import base64
from google.cloud import aiplatform
from google.api_core.exceptions import GoogleAPIError
from config.default import Default
from common.storage import store_to_gcs

cfg = Default()

def generate_vto_image(person_gcs_url: str, product_gcs_url: str, sample_count: int, base_steps: int) -> list[str]:
    """Generates a VTO image."""

    try:
        client_options = {"api_endpoint": f"{cfg.LOCATION}-aiplatform.googleapis.com"}
        client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
    except Exception as client_err:
        print(f"Failed to create PredictionServiceClient: {client_err}")
        raise ValueError(f"Configuration error: Failed to initialize prediction client. Details: {str(client_err)}") from client_err

    model_endpoint = f"projects/{cfg.PROJECT_ID}/locations/{cfg.LOCATION}/publishers/google/models/{cfg.VTO_MODEL_ID}"

    instance = {
        "personImage": {"image": {"gcsUri": person_gcs_url.replace("https:////storage.mtls.cloud.google.com/", "gs://")}},
        "productImages": [{"image": {"gcsUri": product_gcs_url.replace("https:////storage.mtls.cloud.google.com/", "gs://")}}],
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
            raise ValueError("VTO API returned an unexpected response (no predictions).")

        gcs_uris = []
        for i, prediction in enumerate(response.predictions):
            if not prediction.get("bytesBase64Encoded"):
                raise ValueError("VTO API returned a prediction with no image data.")

            encoded_mask_string = prediction["bytesBase64Encoded"]
            mask_bytes = base64.b64decode(encoded_mask_string)

            gcs_uri = store_to_gcs(
                folder="vto_results",
                file_name=f"vto_result_{i}.png",
                mime_type="image/png",
                contents=mask_bytes,
                decode=False,
            )
            gcs_uris.append(f"gs://{cfg.GENMEDIA_BUCKET}/{gcs_uri}")

        return gcs_uris

    except GoogleAPIError as e:
        error_message = f"VTO API Error: {str(e)}"
        print(error_message)
        raise ValueError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred during VTO image generation: {str(e)}"
        print(error_message)
        raise Exception(error_message) from e
