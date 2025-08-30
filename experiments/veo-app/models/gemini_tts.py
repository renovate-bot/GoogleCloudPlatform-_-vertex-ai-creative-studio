"""Model for Gemini Text-to-Speech."""
import base64

import google.auth
import google.auth.transport.requests
import requests

from config.default import Default

cfg = Default()


def synthesize_speech(text: str, prompt: str, model_name: str, voice_name: str, language_code: str) -> bytes:
    """
    Synthesizes speech from text using the Gemini TTS API.

    Args:
        text: The text to synthesize.
        prompt: The prompt for the voice.
        model_name: The name of the TTS model to use.
        voice_name: The name of the voice to use.

    Returns:
        The synthesized audio in bytes.
    """
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)

    url = "https://texttospeech.googleapis.com/v1/text:synthesize"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "x-goog-user-project": cfg.PROJECT_ID,
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "input": {
            "text": text,
            "prompt": prompt,
        },
        "voice": {
            "languageCode": language_code,
            "name": voice_name,
            "model_name": model_name,
        },
        "audioConfig": {
            "audioEncoding": "LINEAR16",
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Error from TTS API: {response.status_code} - {response.text}")
    response.raise_for_status()  # Raise an exception for bad status codes

    audio_content_base64 = response.json()["audioContent"]
    audio_bytes = base64.b64decode(audio_content_base64)

    return audio_bytes