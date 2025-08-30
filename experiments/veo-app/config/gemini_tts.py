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

"""Consolidated configuration for Gemini TTS models, voices, and languages."""

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

GEMINI_TTS_VOICES = [
    "Achernar", "Achird", "Algenib", "Algieba", "Alnilam", "Aoede", "Autonoe",
    "Callirrhoe", "Charon", "Despina", "Enceladus", "Erinome", "Fenrir",
    "Gacrux", "Iapetus", "Kore", "Laomedeia", "Leda", "Orus", "Pulcherrima",
    "Puck", "Rasalgethi", "Sadachbia", "Sadaltager", "Schedar", "Sulafat",
    "Umbriel", "Vindemiatrix", "Zephyr", "Zubenelgenubi",
]

GEMINI_TTS_ENCODINGS = {
    "X-SAMPA": "PHONETIC_ENCODING_X_SAMPA",
    "IPA": "PHONETIC_ENCODING_IPA",
    "Pinyin": "PHONETIC_ENCODING_PINYIN",
    "Japanese": "PHONETIC_ENCODING_JAPANESE_YOMIGANA",
}

GEMINI_TTS_LANGUAGES = {
    "Arabic (Generic)": "ar-XA",
    "Bengali (India)": "bn-IN",
    "Danish (Denmark)": "da-DK",
    "Dutch (Belgium)": "nl-BE",
    "Dutch (Netherlands)": "nl-NL",
    "English (Australia)": "en-AU",
    "English (India)": "en-IN",
    "English (United Kingdom)": "en-GB",
    "English (United States)": "en-US",
    "Finnish (Finland)": "fi-FI",
    "French (Canada)": "fr-CA",
    "French (France)": "fr-FR",
    "German (Germany)": "de-DE",
    "Gujarati (India)": "gu-IN",
    "Hindi (India)": "hi-IN",
    "Indonesian (Indonesia)": "id-ID",
    "Italian (Italy)": "it-IT",
    "Japanese (Japan)": "ja-JP",
    "Kannada (India)": "kn-IN",
    "Korean (South Korea)": "ko-KR",
    "Malayalam (India)": "ml-IN",
    "Mandarin Chinese (China)": "cmn-CN",
    "Marathi (India)": "mr-IN",
    "Norwegian Bokmål (Norway)": "nb-NO",
    "Polish (Poland)": "pl-PL",
    "Portuguese (Brazil)": "pt-BR",
    "Russian (Russia)": "ru-RU",
    "Spanish (Spain)": "es-ES",
    "Spanish (United States)": "es-US",
    "Swahili (Kenya)": "sw-KE",
    "Swedish (Sweden)": "sv-SE",
    "Tamil (India)": "ta-IN",
    "Telugu (India)": "te-IN",
    "Thai (Thailand)": "th-TH",
    "Turkish (Turkey)": "tr-TR",
    "Ukrainian (Ukraine)": "uk-UA",
    "Urdu (India)": "ur-IN",
    "Vietnamese (Vietnam)": "vi-VN"
}
