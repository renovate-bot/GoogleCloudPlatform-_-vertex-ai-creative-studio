"""Gemini TTS page."""

import datetime
import uuid

import mesop as me

import common.storage as storage
from common.metadata import MediaItem, add_media_item_to_firestore
from common.utils import gcs_uri_to_https_url
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from config.gemini_tts_models import GEMINI_TTS_MODELS, GEMINI_TTS_MODEL_NAMES
from config.gemini_tts_voices import GEMINI_TTS_VOICES
from models.gemini_tts import synthesize_speech
from state.state import AppState


@me.stateclass
class GeminiTtsState:
    prompt: str = "you are having a casual conversation with a friend and you are amused. say the following:"
    text: str = "[laughing] oh my god! [sigh] did you see what he is wearing?"
    selected_model: str = GEMINI_TTS_MODEL_NAMES[0]
    selected_voice: str = "Callirrhoe"
    is_generating: bool = False
    audio_url: str = ""
    error: str = ""


@me.page(
    path="/gemini-tts",
    title="Gemini TTS",
)
def page():
    """Renders the Gemini TTS page."""
    state = me.state(GeminiTtsState)

    with page_scaffold():  # pylint: disable=E1129
        with page_frame():  # pylint: disable=E1129
            header("Gemini Text-to-Speech", "record_voice_over")

            with me.box(style=me.Style(padding=me.Padding.all(24), display="flex", flex_direction="row", gap=24)):
                # Left column (controls)
                with me.box(
                    style=me.Style(
                        width=500,
                        background=me.theme_var("surface-container-lowest"),
                        padding=me.Padding.all(16),
                        border_radius=12,
                        display="flex",
                        flex_direction="column",
                        gap=16,
                    )
                ):
                    me.textarea(
                        label="Text to Synthesize",
                        on_input=on_input_text,
                        value=state.text,
                        rows=5,
                        style=me.Style(width="100%"),
                    )
                    me.textarea(
                        label="Voice Prompt",
                        on_input=on_input_prompt,
                        value=state.prompt,
                        rows=3,
                        style=me.Style(width="100%"),
                    )
                    with me.box(
                        style=me.Style(
                            display="flex", flex_direction="row", gap=16
                        )
                    ):
                        me.select(
                            label="Model",
                            options=[
                                me.SelectOption(
                                    label=GEMINI_TTS_MODELS[m]["label"], value=m
                                )
                                for m in GEMINI_TTS_MODEL_NAMES
                            ],
                            on_selection_change=on_select_model,
                            value=state.selected_model,
                            style=me.Style(flex_grow=1),
                        )
                        me.select(
                            label="Voice",
                            options=[
                                me.SelectOption(label=v, value=v)
                                for v in GEMINI_TTS_VOICES
                            ],
                            on_selection_change=on_select_voice,
                            value=state.selected_voice,
                            style=me.Style(flex_grow=1),
                        )
                    with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
                        me.button(
                            "Generate",
                            on_click=on_click_generate,
                            type="raised",
                            disabled=state.is_generating,
                        )
                        me.button(
                            "Clear",
                            on_click=on_click_clear,
                            type="stroked",
                        )

                # Output display
                with me.box(
                    style=me.Style(
                        flex_grow=1,
                        display="flex",
                        flex_direction="column",
                        align_items="center",
                        justify_content="center",
                        border=me.Border.all(
                            me.BorderSide(width=1, style="solid")
                        ),
                        border_radius=12,
                        padding=me.Padding.all(16),
                    )
                ):
                    if state.is_generating:
                        me.progress_spinner()
                        me.text("Generating audio...")
                    elif state.audio_url:
                        me.audio(src=state.audio_url)
                    else:
                        me.text("Generated audio will appear here.")


def on_input_text(e: me.InputEvent):
    """Handles text input."""
    state = me.state(GeminiTtsState)
    state.text = e.value


def on_input_prompt(e: me.InputEvent):
    """Handles prompt input."""
    state = me.state(GeminiTtsState)
    state.prompt = e.value


def on_select_model(e: me.SelectSelectionChangeEvent):
    """Handles model selection."""
    state = me.state(GeminiTtsState)
    state.selected_model = e.value


def on_select_voice(e: me.SelectSelectionChangeEvent):
    """Handles voice selection."""
    state = me.state(GeminiTtsState)
    state.selected_voice = e.value


def on_click_clear(e: me.ClickEvent):
    """Resets the page state to its default values."""
    state = me.state(GeminiTtsState)
    state.prompt = "you are having a casual conversation with a friend and you are amused. say the following:"
    state.text = "[laughing] oh my god! [sigh] did you see what he is wearing?"
    state.selected_model = GEMINI_TTS_MODEL_NAMES[0]
    state.selected_voice = "Callirrhoe"
    state.audio_url = ""
    state.error = ""
    state.is_generating = False
    yield


def on_click_generate(e: me.ClickEvent):
    """Handles generate button click."""
    state = me.state(GeminiTtsState)
    app_state = me.state(AppState)
    state.is_generating = True
    state.audio_url = ""
    state.error = ""
    gcs_url = ""
    yield

    try:
        audio_bytes = synthesize_speech(
            text=state.text,
            prompt=state.prompt,
            model_name=state.selected_model,
            voice_name=state.selected_voice,
        )

        file_name = f"gemini-tts-{uuid.uuid4()}.wav"

        gcs_url = storage.store_to_gcs(
            folder="gemini-tts-audio",
            file_name=file_name,
            mime_type="audio/wav",
            contents=audio_bytes,
        )

        state.audio_url = gcs_uri_to_https_url(gcs_url)

    except Exception as ex:
        app_state.snackbar_message = f"An error occurred: {ex}"

    finally:
        state.is_generating = False
        yield

    # Add to library
    if gcs_url:
        try:
            item = MediaItem(
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                prompt=state.text,  # The main text is the core prompt
                comment=f"Voice: {state.selected_voice}, Style Prompt: {state.prompt}",
                model=state.selected_model,
                mime_type="audio/wav",
                gcsuri=gcs_url,
            )
            add_media_item_to_firestore(item)
            app_state.snackbar_message = "Audio saved to library"
        except Exception as ex:
            print(f"CRITICAL: Failed to store metadata: {ex}")
            app_state.snackbar_message = "Error saving audio to library"