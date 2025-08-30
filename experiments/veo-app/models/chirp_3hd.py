"""Model for Chirp3 HD Text-to-Speech."""

from google.cloud import texttospeech

def synthesize_chirp_speech(text: str, voice_name: str, language_code: str) -> bytes:
    """Synthesizes speech from text using the Chirp3 HD model."""
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Construct the full voice name required by the Text-to-Speech API
    # e.g., "en-US-Chirp3-HD-Orus"
    full_voice_name = f"{language_code}-Chirp3-HD-{voice_name}"

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=full_voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    return response.audio_content
