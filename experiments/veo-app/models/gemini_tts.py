"""Model for Gemini Text-to-Speech."""
import base64
import json
import subprocess

import requests


def _get_gcloud_auth_token() -> str:
    """Gets the gcloud auth token."""
    try:
        # Run the gcloud command to print the access token
        result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error getting gcloud auth token: {e}")
        # Handle the error as needed, e.g., by raising an exception
        # or returning a specific error indicator.
        raise

def synthesize_speech(text: str, prompt: str, model_name: str) -> bytes:
    """
    Synthesizes speech from text using the Gemini TTS API.

    Args:
        text: The text to synthesize.
        prompt: The prompt for the voice.
        model_name: The name of the TTS model to use.

    Returns:
        The synthesized audio in bytes.
    """
    token = _get_gcloud_auth_token()
    url = "https://texttospeech.googleapis.com/v1/text:synthesize"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": "genai-blackbelt-fishfooding",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "input": {
            "text": text,
            "prompt": prompt,
        },
        "voice": {
            "languageCode": "en-us",
            "name": "Callirrhoe",
            "model_name": model_name,
        },
        "audioConfig": {
            "audioEncoding": "LINEAR16",
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # Raise an exception for bad status codes

    audio_content_base64 = response.json()["audioContent"]
    audio_bytes = base64.b64decode(audio_content_base64)

    return audio_bytes
