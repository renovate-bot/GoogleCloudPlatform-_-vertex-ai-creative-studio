"""Configuration for Gemini TTS models."""

GEMINI_TTS_MODELS = {
    "gemini-2.5-flash-preview-tts": {
        "id": "gemini-2.5-flash-preview-tts",
        "label": "Gemini 2.5 Flash TTS",
        "description": "Fast, high-quality text-to-speech model.",
        "tags": ["TTS", "Gemini 2.5 Flash"],
        "version": "2.5-flash",
    },
    "gemini-2.5-pro-preview-tts": {
        "id": "gemini-2.5-pro-preview-tts",
        "label": "Gemini 2.5 Pro TTS",
        "description": "Highest-quality text-to-speech model.",
        "tags": ["TTS", "Gemini 2.5 Pro"],
        "version": "2.5-pro",
    },
}

GEMINI_TTS_MODEL_NAMES = list(GEMINI_TTS_MODELS.keys())
