# Copyright 2024 Google LLC
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
"""Creative Studio - Imagen"""

import json
import random
import time
from dataclasses import dataclass, field

import mesop as me
import requests

# Assuming these components and models are correctly implemented and imported
# from google.cloud.aiplatform import telemetry # Not used in snippet
from components.header import header
from components.page_scaffold import (
    page_frame,
    page_scaffold,
)
from config.default import (
    Default,
    ImageModel,
)  # Assuming ImageModel structure is compatible
from config.rewriters import REWRITER_PROMPT
from models.gemini import image_critique, rewriter
from models.image_models import generate_images
from svg_icon.svg_icon_component import svg_icon_component

app_config_instance = Default()


def _get_default_image_models() -> list[ImageModel]:
    """Helper function for PageState default_factory."""
    # Ensure app_config_instance.display_image_models provides a list of ImageModel compatible dicts or objects
    return app_config_instance.display_image_models.copy()


@dataclass
@me.stateclass
class PageState:
    """Local Page State"""

    # Image generation model selection and output
    image_models: list[ImageModel] = field(default_factory=_get_default_image_models)
    image_output: list[str] = field(default_factory=list)
    image_commentary: str = ""
    image_model_name: str = app_config_instance.MODEL_IMAGEN_FAST

    # General UI state
    is_loading: bool = False
    show_advanced: bool = False
    error_message: str = ""

    # Image prompt and related settings
    image_prompt_input: str = ""
    image_prompt_placeholder: str = ""
    image_textarea_key: int = 0  # Used as str(key) for component

    image_negative_prompt_input: str = ""
    image_negative_prompt_placeholder: str = ""
    image_negative_prompt_key: int = 0  # Used as str(key) for component

    # Image generation parameters
    imagen_watermark: bool = True  # SynthID notice implies watermark is active
    imagen_seed: int = 0
    imagen_image_count: int = 4

    # Image style modifiers
    image_content_type: str = "Photo"
    image_color_tone: str = "Cool tone"
    image_lighting: str = "Golden hour"
    image_composition: str = "Wide angle"
    image_aspect_ratio: str = "1:1"

    timing: str = ""  # For displaying generation time


def imagen_content(app_state: me.state):  # app_state parameter is not used
    """Imagen Mesop Page"""
    state = me.state(PageState)  # Single call to get state

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Imagen Creative Studio", "image")

            with me.box(
                style=me.Style(display="flex", justify_content="end"),
            ):
                image_model_options = []
                # ImageModel is a dict-like structure and has .get method
                for c in state.image_models:
                    image_model_options.append(
                        me.SelectOption(
                            label=c.get(
                                "display_name", c.get("display")
                            ),  # Prioritize display_name if available
                            value=c.get("model_name"),
                        )
                    )
                me.select(
                    label="Imagen version",
                    options=image_model_options,
                    # key="model_name", # This key should match a PageState attribute if meant to auto-bind
                    # If on_selection_change handles it, then it's more explicit.
                    # For clarity, if image_model_name is the target, use that as key or ensure handler sets it.
                    on_selection_change=on_selection_change_image_model_name,  # More specific handler name
                    value=state.image_model_name,
                )

            with me.box(style=_BOX_STYLE):
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

            # Modifiers
            with me.box(style=_BOX_STYLE):
                with me.box(
                    style=me.Style(
                        display="flex",
                        justify_content="space-between",  # This might crowd if many items
                        flex_wrap="wrap",  # Allow wrapping for smaller screens
                        gap="16px",  # Use gap for spacing
                        width="100%",
                    )
                ):
                    if state.show_advanced:
                        with me.content_button(on_click=on_click_advanced_controls):
                            with me.tooltip(message="Hide advanced controls"):
                                with me.box(style=me.Style(display="flex")):
                                    me.icon("expand_less")
                    else:
                        with me.content_button(on_click=on_click_advanced_controls):
                            with me.tooltip(message="Show advanced controls"):
                                with me.box(style=me.Style(display="flex")):
                                    me.icon("expand_more")

                    # Default Modifiers
                    me.select(
                        label="Aspect Ratio",
                        options=[
                            me.SelectOption(label="1:1", value="1:1"),
                            me.SelectOption(label="3:4", value="3:4"),
                            me.SelectOption(label="4:3", value="4:3"),
                            me.SelectOption(label="16:9", value="16:9"),
                            me.SelectOption(label="9:16", value="9:16"),
                        ],
                        key="image_aspect_ratio",  # Match PageState attribute directly
                        on_selection_change=on_selection_change_modifier,
                        style=me.Style(min_width="160px", flex_grow=1),
                        value=state.image_aspect_ratio,
                    )
                    me.select(
                        label="Content Type",
                        options=[
                            me.SelectOption(label="None", value="None"),
                            me.SelectOption(label="Photo", value="Photo"),
                            me.SelectOption(label="Art", value="Art"),
                        ],
                        key="image_content_type",  # Match PageState attribute
                        on_selection_change=on_selection_change_modifier,
                        style=me.Style(min_width="160px", flex_grow=1),
                        value=state.image_content_type,
                    )

                    color_and_tone_options = [
                        me.SelectOption(label=c, value=c)
                        for c in [
                            "None",
                            "Black and white",
                            "Cool tone",
                            "Golden",
                            "Monochromatic",
                            "Muted color",
                            "Pastel color",
                            "Toned image",
                        ]
                    ]
                    me.select(
                        label="Color & Tone",
                        options=color_and_tone_options,
                        key="image_color_tone",  # Match PageState attribute
                        on_selection_change=on_selection_change_modifier,
                        style=me.Style(min_width="160px", flex_grow=1),
                        value=state.image_color_tone,
                    )

                    lighting_options = [
                        me.SelectOption(label=l, value=l)
                        for l in [
                            "None",
                            "Backlighting",
                            "Dramatic light",
                            "Golden hour",
                            "Long-time exposure",
                            "Low lighting",
                            "Multiexposure",
                            "Studio light",
                            "Surreal lighting",
                        ]
                    ]
                    me.select(
                        label="Lighting",
                        options=lighting_options,
                        key="image_lighting",  # Match PageState attribute
                        on_selection_change=on_selection_change_modifier,
                        style=me.Style(min_width="160px", flex_grow=1),
                        value=state.image_lighting,
                    )

                    composition_options = [
                        me.SelectOption(label=c, value=c)
                        for c in [
                            "None",
                            "Closeup",
                            "Knolling",
                            "Landscape photography",
                            "Photographed through window",
                            "Shallow depth of field",
                            "Shot from above",
                            "Shot from below",
                            "Surface detail",
                            "Wide angle",
                        ]
                    ]
                    me.select(
                        label="Composition",
                        options=composition_options,
                        key="image_composition",  # Match PageState attribute
                        on_selection_change=on_selection_change_modifier,
                        style=me.Style(min_width="160px", flex_grow=1),
                        value=state.image_composition,
                    )

                # Advanced controls
                if state.show_advanced:  # Show this section only if advanced
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",  # Could be column for better stacking on small screens
                            flex_wrap="wrap",
                            gap="16px",
                            margin=me.Margin(
                                top=16
                            ),  # Add some space above advanced controls
                        )
                    ):
                        # Removed fixed width for negative prompt box, let flex handle it
                        me.input(
                            label="Negative prompt phrases",
                            on_blur=on_blur_image_negative_prompt,
                            value=state.image_negative_prompt_input,  # Use input directly, placeholder if needed
                            key=str(
                                state.image_negative_prompt_key
                            ),  # Ensure unique key if needed
                            style=me.Style(
                                min_width="300px", flex_grow=2
                            ),  # Allow more growth
                        )
                        me.select(
                            label="Number of images",
                            value=str(state.imagen_image_count),
                            options=[
                                me.SelectOption(label="1", value="1"),
                                me.SelectOption(label="2", value="2"),
                                me.SelectOption(label="3", value="3"),
                                me.SelectOption(label="4", value="4"),
                            ],
                            on_selection_change=on_select_image_count,
                            # key="imagen_image_count", # Handled by on_select_image_count
                            style=me.Style(min_width="155px", flex_grow=1),
                        )
                        me.checkbox(
                            label="Watermark (SynthID)",  # Clarify it's SynthID
                            checked=state.imagen_watermark,  # Use state value
                            disabled=True,  # If always true and not changeable by user
                            # on_change=on_toggle_watermark, # If it were changeable
                            key="imagen_watermark",
                        )
                        me.input(
                            label="Seed (0 for random)",
                            value=str(state.imagen_seed),
                            on_blur=on_blur_imagen_seed,
                            type="number",
                            style=me.Style(min_width="155px", flex_grow=1),
                        )

            # Error Message Display
            if state.error_message:
                with me.box(style=_BOX_STYLE):
                    me.text(
                        "Error", style=me.Style(font_weight=500, color="red")
                    )  # Use theme error color if available
                    me.text(state.error_message)

            # Image Output Box
            with me.box(style=_BOX_STYLE):
                me.text("Output", style=me.Style(font_weight=500))
                me.box(style=me.Style(height=10))

                print(f"loading? {state.is_loading}")
                print(f"images? {len(state.image_output)} images")
                print(f"commentary? {len(state.image_commentary)} char")
                
                if state.is_loading:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            justify_content="center",
                            align_items="center",
                            flex_direction="column",
                            min_height="200px",
                        )
                    ):
                        me.progress_spinner()
                        me.text(
                            "Generating, please wait...",
                            style=me.Style(margin=me.Margin(top=10)),
                        )

                elif state.image_output:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="column",
                            align_items="center",
                        )
                    ):
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_wrap="wrap",
                                gap="15px",
                                justify_content="center",
                            )
                        ):
                            for img_uri in state.image_output:
                                final_img_src = img_uri
                                if img_uri.startswith("gs://"):
                                    final_img_src = img_uri.replace(
                                        "gs://", "https://storage.googleapis.com/"
                                    )

                                me.image(
                                    src=final_img_src,
                                    style=me.Style(
                                        width="300px",  # Consider using max_width or responsive units
                                        height="300px",
                                        object_fit="contain",
                                        border_radius="12px",
                                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                    ),
                                )
                        if state.imagen_watermark:  # Only show if watermark was applied
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    flex_direction="row",
                                    align_items="center",
                                    margin=me.Margin(top=15),
                                )
                            ):
                                svg_icon_component(
                                    svg="""<svg data-icon-name="digitalWatermarkIcon" viewBox="0 0 24 24" width="24" height="24" fill="none" aria-hidden="true"><path fill="#3367D6" d="M12 22c-.117 0-.233-.008-.35-.025-.1-.033-.2-.075-.3-.125-2.467-1.267-4.308-2.833-5.525-4.7C4.608 15.267 4 12.983 4 10.3V6.2c0-.433.117-.825.35-1.175.25-.35.575-.592.975-.725l6-2.15a7.7 7.7 0 00.325-.1c.117-.033.233-.05.35-.05.15 0 .375.05.675.15l6 2.15c.4.133.717.375.95.725.25.333.375.717.375 1.15V10.3c0 2.683-.625 4.967-1.875 6.85-1.233 1.883-3.067 3.45-5.5 4.7-.1.05-.2.092-.3.125-.1.017-.208.025-.325.025zm0-2.075c2.017-1.1 3.517-2.417 4.5-3.95 1-1.55 1.5-3.442 1.5-5.675V6.175l-6-2.15-6 2.15V10.3c0 2.233.492 4.125 1.475 5.675 1 1.55 2.508 2.867 4.525 3.95z"></path><path fill="#3367D6" d="M12 16.275c0-.68-.127-1.314-.383-1.901a4.815 4.815 0 00-1.059-1.557 4.813 4.813 0 00-1.557-1.06 4.716 4.716 0 00-1.9-.382c.68 0 1.313-.128 1.9-.383a4.916 4.916 0 002.616-2.616A4.776 4.776 0 0012 6.475c0 .672.128 1.306.383 1.901a5.07 5.07 0 001.046 1.57 5.07 5.07 0 001.57 1.046 4.776 4.776 0 001.901.383c-.672 0-1.306.128-1.901.383a4.916 4.916 0 00-2.616 2.616A4.716 4.716 0 0012 16.275z"></path></svg>"""
                                )
                                me.text(
                                    text="Images watermarked by SynthID (Google)",
                                    style=me.Style(
                                        padding=me.Padding.all(10),
                                        font_size="0.9em",
                                        color="#5f6368",
                                    ),
                                )  # Use theme text color
                else:
                    me.text(
                        text="Generate some images to see them here!",
                        style=me.Style(
                            display="flex",
                            justify_content="center",
                            padding=me.Padding.all(20),
                            color=me.theme_var("outline"),
                            min_height="100px",
                            align_items="center",
                        ),  # Use theme color
                    )

            # Image commentary
            if state.image_output and state.image_commentary and not state.is_loading:
                with me.box(style=_BOX_STYLE):
                    with me.box(
                        style=me.Style(
                            display="flex",
                            align_items="center",
                            gap="8px",
                            margin=me.Margin(bottom=10),
                        )
                    ):
                        me.icon("assistant")
                        me.text(
                            "Magazine Editor's Critique",
                            style=me.Style(font_weight=500),
                        )
                    me.markdown(
                        text=state.image_commentary,
                        style=me.Style(
                            padding=me.Padding(left=15, right=15, bottom=15)
                        ),
                    )


def on_blur_image_prompt(e: me.InputBlurEvent):
    """Image prompt blur event."""
    state = me.state(PageState)
    state.image_prompt_input = e.value
    state.image_prompt_placeholder = (
        e.value
    )  # Also update placeholder to reflect current input


def on_blur_image_negative_prompt(e: me.InputBlurEvent):
    """Negative image prompt blur event."""
    me.state(PageState).image_negative_prompt_input = e.value


def on_click_generate_images(e: me.ClickEvent):
    """Click Event to generate images and commentary."""
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
        print(f"Image generation phase complete. Received {len(new_image_uris)} URIs.")

        #state.is_loading = False  # Stop main spinner after image generation attempt
        yield  # UI: Show images (if any) or updated empty state, spinner OFF

        # Phase 2: Generate Compliment (Critique) if images were produced
        if state.image_output:
            print(
                f"Proceeding to generate commentary for {len(state.image_output)} produced images."
            )
            #state.is_loading = True  # Spinner ON for critique phase
            yield  # UI: Show spinner for critique

            generate_compliment(current_prompt)  # This function updates state.image_commentary and state.error_message

            state.is_loading = False  # Spinner OFF after critique is done (or attempted)
            print("Commentary generation phase complete.")
            yield  # UI: Show critique and turn spinner OFF
        else:
            print(
                "Skipping commentary generation as no images were successfully generated."
            )
            # is_loading is already False from the image generation phase. No further yield needed here.

    except Exception as ex:
        print(f"Error during the image generation or critique process: {ex}")
        state.error_message = f"An unexpected error occurred: {str(ex)}"
        state.is_loading = False  # Ensure spinner is off on any error
        yield  # UI: Update UI with error message and ensure spinner is OFF


def on_select_image_count(e: me.SelectSelectionChangeEvent):
    """Handles selection change for the number of images."""
    state = me.state(PageState)
    try:
        state.imagen_image_count = int(e.value)
    except ValueError:
        print(
            f"Invalid value for image count: {e.value}. Defaulting or handling error."
        )
        state.imagen_image_count = 4  # Or some other default / error state handling


def generate_images_from_prompt(
    input_txt: str,
    current_model_name: str,
    image_count: int,
    negative_prompt: str,
    prompt_modifiers_segment: str,
    aspect_ratio: str,
) -> list[str]:
    """
    Generates images based on the input prompt and parameters.
    Returns a list of image URIs. Does not directly modify PageState.
    """
    generated_uris = []
    final_prompt = f"{input_txt} {prompt_modifiers_segment}".strip().rstrip(
        ","
    )  # Ensure clean prompt

    print(f"Calling image_generation_api with prompt: '{final_prompt}'")
    if negative_prompt:
        print(f"Negative prompt: '{negative_prompt}'")
    print(
        f"Model: {current_model_name}, Count: {image_count}, Aspect Ratio: {aspect_ratio}"
    )

    try:
        response = generate_images(
            model=current_model_name,
            prompt=final_prompt,
            number_of_images=image_count,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt if negative_prompt else None,
            # output_gcs_uri=output_gcs_uri, # If you save to GCS and get URIs
            # language="auto" # If applicable
        )

        if hasattr(response, "generated_images") and isinstance(
            response.generated_images, list
        ):
            if not response.generated_images:
                print(
                    "Image API returned successfully but with an empty list of images."
                )
            for idx, img_obj in enumerate(response.generated_images):
                image_uri_to_append = None
                if hasattr(img_obj, "image") and img_obj.image is not None:
                    actual_image_object = img_obj.image
                    if (
                        hasattr(actual_image_object, "gcs_uri")
                        and actual_image_object.gcs_uri
                    ):
                        image_uri_to_append = actual_image_object.gcs_uri
                    # Example for base64, if your API might return that instead/also
                    # elif hasattr(actual_image_object, 'base64_string') and actual_image_object.base64_string:
                    #     image_uri_to_append = f"data:image/png;base64,{actual_image_object.base64_string}"
                    else:
                        print(
                            f"Warning: Image object {idx} has no GCS URI or recognized format."
                        )
                else:
                    print(
                        f"Warning: GeneratedImage at index {idx} has no '.image' attribute or it's None."
                    )

                if image_uri_to_append:
                    generated_uris.append(image_uri_to_append)
                    print(f"Retrieved image URI {idx}: {image_uri_to_append}")
                else:
                    print(f"Warning: No valid URI to append for image {idx}.")
        else:
            print(
                f"Error: API response missing 'generated_images' or it's not a list. Response: {response}"
            )
            # Potentially set an error message here if this function were to return more than just URIs

    except Exception as e:
        print(f"An error occurred during the call to the image generation API: {e}")
        # This error is currently only logged. The caller will see an empty list of URIs.
        # Consider raising a custom exception or returning an error status if the caller needs to know.

    return generated_uris


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


def on_click_advanced_controls(e: me.ClickEvent):
    """Toggles visibility of advanced controls."""
    me.state(PageState).show_advanced = not me.state(PageState).show_advanced


def on_blur_imagen_seed(e: me.InputBlurEvent):
    """Handles blur event for the image seed input."""
    state = me.state(PageState)
    try:
        seed_value = int(e.value)
        state.imagen_seed = (
            seed_value if seed_value >= 0 else 0
        )  # Ensure seed is not negative
    except ValueError:
        state.imagen_seed = 0  # Default to 0 if input is not a valid integer
        print(f"Invalid seed value '{e.value}', defaulting to 0.")


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


def on_selection_change_modifier(e: me.SelectSelectionChangeEvent):
    """Handles selection change for image style modifiers."""
    state = me.state(PageState)
    print(f"Modifier changed: {e.key} = {e.value}")
    if hasattr(state, e.key):  # Ensure the key corresponds to a state attribute
        setattr(state, e.key, e.value)
    else:
        print(f"Warning: No state attribute found for key {e.key}")


def on_selection_change_image_model_name(e: me.SelectSelectionChangeEvent):
    """Handles selection change for the image model name."""
    state = me.state(PageState)
    state.image_model_name = e.value
    print(f"Image model changed to: {e.value}")


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


def rewrite_prompt_with_gemini(original_prompt: str) -> str:
    """
    Outputs a rewritten prompt using the Gemini model.
    Args:
        original_prompt (str): The user's original prompt.
    Returns:
        str: The rewritten prompt.
    Raises:
        Exception: If the rewriter service fails.
    """
    full_rewriter_instruction = REWRITER_PROMPT.format(
        original_prompt=original_prompt
    )  # Ensure placeholder matches

    # Assuming 'rewriter' is an imported function that calls the Gemini API
    # and handles its own errors or raises them.
    try:
        # The empty string argument for the second parameter of `rewriter` is unclear;
        # assuming it's part of the `rewriter` function's signature.
        rewritten_text = rewriter(full_rewriter_instruction, "")
        if not rewritten_text:  # Handle cases where rewriter might return empty
            print("Warning: Rewriter returned an empty prompt.")
            return original_prompt  # Fallback to original prompt
        return rewritten_text
    except Exception as e:
        print(f"Gemini rewriter failed: {e}")
        raise  # Re-raise the exception to be caught by the caller


_BOX_STYLE = me.Style(
    background=me.theme_var("surface"),  # Use theme variable for background
    border_radius=12,
    box_shadow=me.theme_var("shadow_elevation_2"),  # Use theme variable for shadow
    padding=me.Padding.all(16),  # Simpler padding
    display="flex",
    flex_direction="column",
    margin=me.Margin(bottom=28),
)


def generate_compliment(generation_instruction: str):
    """
    Generates a Gemini-powered critique/commentary for the generated images.
    Updates PageState.image_commentary and PageState.error_message directly.
    """
    state = me.state(PageState)
    start_time = time.time()
    critique_text = ""
    error_for_this_op = ""

    print(
        f"Generating critique for instruction: '{generation_instruction}' and {len(state.image_output)} images."
    )
    try:
        # Assuming image_critique is a blocking call to your Gemini model for critique
        critique_text = image_critique(generation_instruction, state.image_output)
        if not critique_text:
            print("Warning: Image critique returned empty.")
            # critique_text = "No critique available for these images." # Optional default

    except requests.exceptions.HTTPError as err_http:
        print(f"HTTPError during image critique: {err_http}")
        error_for_this_op = f"Network error during critique: {err_http.response.status_code if err_http.response else 'Unknown'}"
    except ValueError as err_value:
        print(f"ValueError during image critique: {err_value}")
        error_for_this_op = f"Input error for critique: {str(err_value)}"
    except Exception as err_generic:
        print(
            f"Generic Exception during image critique: {type(err_generic).__name__}: {err_generic}"
        )
        error_for_this_op = f"Unexpected error during critique: {str(err_generic)}"
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        state.timing = f"Critique generation time: {execution_time:.2f} seconds"  # More precise timing
        print(state.timing)

        state.image_commentary = critique_text
        if error_for_this_op:  # If an error occurred specifically in this operation
            state.error_message = (
                error_for_this_op  # Set/overwrite the main error message
            )

        # The commented-out metadata logging is specific to another context (video)
        # and should be handled separately if similar logic is needed for images.

    print("Critique generation function finished.")
