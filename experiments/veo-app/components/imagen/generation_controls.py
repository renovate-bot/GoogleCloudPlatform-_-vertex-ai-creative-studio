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

import json
import random
import time

import mesop as me

from common.metadata import add_image_metadata
from config.default import Default
from models.gemini import generate_compliment, rewrite_prompt_with_gemini
from models.image_models import generate_images_from_prompt
from state.state import AppState
from state.imagen_state import PageState

app_config_instance = Default()


@me.component
def generation_controls():
    """Image generation controls"""
    state = me.state(PageState)
    with me.box(style=_BOX_STYLE):
        with me.box(style=me.Style(display="flex", justify_content="end")):
            image_model_options = []
            for c in state.image_models:
                image_model_options.append(
                    me.SelectOption(
                        label=c.get("display_name", c.get("display")),
                        value=c.get("model_name"),
                    )
                )
            me.select(
                label="Imagen version",
                options=image_model_options,
                on_selection_change=on_selection_change_image_model,
                value=state.image_model_name,
            )

        me.text(
            "Prompt for image generation",
            style=me.Style(font_weight=500),
        )
        me.box(style=me.Style(height=16))
        me.textarea(
            key=str(state.image_textarea_key),
            on_blur=on_blur_image_prompt,
            rows=3,
            autosize=True,
            max_rows=10,
            style=me.Style(width="100%"),
            value=state.image_prompt_placeholder
            or state.image_prompt_input,  # Show input if placeholder is also input
        )
        me.box(style=me.Style(height=12))
        with me.box(
            style=me.Style(display="flex", justify_content="space-between")
        ):
            me.button(
                "Clear",
                color="primary",
                type="stroked",
                on_click=on_click_clear_images,
            )
            me.button(
                "Random",
                color="primary",
                type="stroked",
                on_click=random_prompt_generator,
                style=me.Style(
                    color="#1A73E8"
                ),  # Consider using theme variables if available
            )
            with me.content_button(
                on_click=on_click_rewrite_prompt,
                type="stroked",
                disabled=not state.image_prompt_input,  # Simplified disabled logic
            ):
                with me.tooltip(message="Rewrite prompt with Gemini"):
                    with me.box(
                        style=me.Style(
                            display="flex",
                            gap=3,
                            align_items="center",
                        )
                    ):
                        me.icon("auto_awesome")
                        me.text("Rewriter")
            me.button(
                "Generate",
                color="primary",
                type="flat",
                on_click=on_click_generate_images,
                disabled=state.is_loading,  # Disable generate button while loading
            )


def on_blur_image_prompt(e: me.InputBlurEvent):
    """Image prompt blur event."""
    state = me.state(PageState)
    state.image_prompt_input = e.value
    state.image_prompt_placeholder = (
        e.value
    )  # Also update placeholder to reflect current input


def on_selection_change_image_model(e: me.SelectSelectionChangeEvent):
    """Handles selection change for the image model."""
    state = me.state(PageState)
    state.image_model_name = e.value


def on_click_generate_images(e: me.ClickEvent):
    """Click Event to generate images and commentary."""
    app_state = me.state(AppState)
    state = me.state(PageState)

    # Determine the current prompt to use
    current_prompt = state.image_prompt_input
    if not current_prompt and state.image_prompt_placeholder:
        # This case happens if "Random" was clicked but then "Generate" without further edits.
        current_prompt = state.image_prompt_placeholder
        state.image_prompt_input = (
            current_prompt  # Ensure input also reflects this for consistency
        )

    if not current_prompt:
        state.error_message = (
            "Image prompt cannot be empty. Please enter a prompt or use 'Random'."
        )
        state.is_loading = False  # Ensure loading is false if we exit early
        yield
        return

    state.is_loading = True
    state.image_output = []  # Reset image output
    state.image_commentary = ""
    state.error_message = ""  # Clear previous errors
    yield  # UI: Spinner ON, outputs cleared

    start_time = time.time()

    try:
        # Phase 1: Generate Images
        print(f"Starting image generation for prompt: '{current_prompt}'")
        modifiers = []
        if hasattr(app_config_instance, "image_modifiers"):
            for mod_key_suffix in app_config_instance.image_modifiers:
                state_attr_name = f"image_{mod_key_suffix}"
                if mod_key_suffix != "aspect_ratio":  # Aspect ratio passed separately
                    modifier_value = getattr(state, state_attr_name, "None")
                    if (
                        modifier_value and modifier_value != "None"
                    ):  # Ensure not None before appending
                        modifiers.append(modifier_value)
        prompt_modifiers_segment = ", ".join(modifiers)

        new_image_uris = generate_images_from_prompt(
            input_txt=current_prompt,
            current_model_name=state.image_model_name,
            image_count=int(state.imagen_image_count),
            negative_prompt=state.image_negative_prompt_input,
            prompt_modifiers_segment=prompt_modifiers_segment,
            aspect_ratio=state.image_aspect_ratio,
        )
        state.image_output = new_image_uris
        state.is_loading = False

        if state.image_output:
            # Generate commentary in the background
            state.image_commentary = generate_compliment(
                current_prompt, state.image_output
            )

        end_time = time.time()
        execution_time = end_time - start_time

        add_image_metadata(
            gcs_uris=state.image_output,
            original_prompt=current_prompt,
            rewritten_prompt=state.image_prompt_input,
            modifiers=modifiers,
            negative_prompt=state.image_negative_prompt_input,
            num_images=state.imagen_image_count,
            seed=state.imagen_seed,
            critique=state.image_commentary,
            model=state.image_model_name,
            aspect_ratio=state.image_aspect_ratio,
            generation_time=execution_time,
            error_message="",
            user_email=app_state.user_email,
        )

    except Exception as ex:
        print(f"Error during the image generation or critique process: {ex}")
        state.dialog_message = f"An unexpected error occurred: {str(ex)}"
        state.show_dialog = True
        state.image_output = []
        state.is_loading = False
    yield


def random_prompt_generator(e: me.ClickEvent):
    """Click Event to generate a random prompt."""
    state = me.state(PageState)
    try:
        with open(
            app_config_instance.IMAGEN_PROMPTS_JSON, "r", encoding="utf-8"
        ) as file:
            data = json.load(file)  # Use json.load for direct parsing
        prompts_list = data.get("imagen", [])
        if not prompts_list:
            state.error_message = "No prompts found in the prompts file."
            yield
            return
        random_prompt = random.choice(prompts_list)

        state.image_prompt_input = random_prompt  # Directly set the input
        state.image_prompt_placeholder = random_prompt  # Update placeholder
        state.image_textarea_key += 1  # Force re-render of textarea if needed
        print(f"Random prompt chosen: {random_prompt}")
    except FileNotFoundError:
        state.error_message = (
            f"Prompts file not found: {app_config_instance.IMAGEN_PROMPTS_JSON}"
        )
        print(state.error_message)
    except json.JSONDecodeError:
        state.error_message = "Error decoding the prompts JSON file."
        print(state.error_message)
    except Exception as ex:
        state.error_message = (
            f"An unexpected error occurred while loading random prompts: {str(ex)}"
        )
        print(state.error_message)
    yield


def on_click_clear_images(e: me.ClickEvent):
    """Clears image prompt, output, and related fields."""
    state = me.state(PageState)
    state.image_prompt_input = ""
    state.image_prompt_placeholder = ""  # Clear placeholder as well
    state.image_output = []  # Use assignment for list reset
    state.image_commentary = ""
    state.image_negative_prompt_input = ""
    state.image_textarea_key += 1
    state.image_negative_prompt_key += 1
    state.error_message = ""  # Clear any existing error messages
    # Reset modifiers to default if desired, or leave them.
    # state.image_content_type = "Photo" # Example reset
    # ... etc. for other modifiers


def on_click_rewrite_prompt(e: me.ClickEvent):
    """Click Event to rewrite prompt using Gemini."""
    state = me.state(PageState)
    if not state.image_prompt_input:
        state.error_message = "Cannot rewrite an empty prompt."
        yield
        return

    state.is_loading = True  # Show spinner for rewrite
    state.error_message = ""
    yield

    try:
        print(f"Rewriting prompt: '{state.image_prompt_input}'")
        rewritten_prompt = rewrite_prompt_with_gemini(
            state.image_prompt_input
        )  # Changed function name for clarity
        state.image_prompt_input = rewritten_prompt
        state.image_prompt_placeholder = rewritten_prompt  # Update placeholder as well
        state.image_textarea_key += 1  # Force re-render
        print(f"Rewritten prompt: '{rewritten_prompt}'")
    except Exception as ex:
        print(f"Error during prompt rewriting: {ex}")
        state.error_message = f"Failed to rewrite prompt: {str(ex)}"
    finally:
        state.is_loading = False  # Hide spinner
        yield


_BOX_STYLE = me.Style(
    background=me.theme_var("surface"),  # Use theme variable for background
    border_radius=12,
    box_shadow=me.theme_var("shadow_elevation_2"),  # Use theme variable for shadow
    padding=me.Padding.all(16),  # Simpler padding
    display="flex",
    flex_direction="column",
    margin=me.Margin(bottom=28),
)
