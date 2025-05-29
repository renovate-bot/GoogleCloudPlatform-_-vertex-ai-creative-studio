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

# from google.cloud.aiplatform import telemetry
from components.header import header
from components.page_scaffold import (
    page_frame,
    page_scaffold,
)
from config.default import Default, ImageModel
from config.rewriters import REWRITER_PROMPT
from models.gemini import image_critique, rewriter
# from models.image_models import ImageModel # Ensure this is removed if ImageModel moved
from models.image_models import generate_images as image_generation
from svg_icon.svg_icon_component import svg_icon_component

app_config_instance = Default()


def _get_default_image_models():
    """Helper function for PageState default_factory."""
    return app_config_instance.display_image_models.copy()


@dataclass
@me.stateclass
class PageState:
    """Local Page State"""

    # Image generation model selection and output
    image_models: list[ImageModel] = field(
        default_factory=_get_default_image_models
    )
    image_output: list[str] = field(default_factory=list)
    image_commentary: str = ""
    image_model_name: str = app_config_instance.MODEL_IMAGEN_FAST # Updated constant name

    # General UI state
    is_loading: bool = False
    show_advanced: bool = False

    # Image prompt and related settings
    image_prompt_input: str = ""
    image_prompt_placeholder: str = ""
    image_textarea_key: int = 0

    image_negative_prompt_input: str = ""
    image_negative_prompt_placeholder: str = ""
    image_negative_prompt_key: int = 0  # Or handle None later

    # Image generation parameters
    imagen_watermark: bool = True
    imagen_seed: int = 0
    imagen_image_count: int = 3

    # Image style modifiers
    image_content_type: str = "Photo"
    image_color_tone: str = "Cool tone"
    image_lighting: str = "Golden hour"
    image_composition: str = "Wide angle"
    image_aspect_ratio: str = "1:1"


def imagen_content(app_state: me.state):
    """Imagen Mesop Page"""

    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Imagen Creative Studio", "image")
            
            with me.box(
                style=me.Style(display="flex",justify_content="end"),
            ):
                image_model_options = []
                for c in state.image_models:
                    image_model_options.append(
                        me.SelectOption(
                            label=c.get("display"), value=c.get("model_name")
                        )
                    )
                me.select(
                    label="Imagen version",
                    options=image_model_options,
                    key="model_name",
                    on_selection_change=on_selection_change_image,
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
                    # on_input=on_image_input,
                    on_blur=on_blur_image_prompt,
                    rows=3,
                    autosize=True,
                    max_rows=10,
                    style=me.Style(width="100%"),
                    value=state.image_prompt_placeholder,
                )
                # Prompt buttons
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
                        style=me.Style(color="#1A73E8"),
                    )
                    # prompt rewriter
                    # disabled = not state.image_prompt_input if not state.image_prompt_input else False
                    with me.content_button(
                        on_click=on_click_rewrite_prompt,
                        type="stroked",
                        # disabled=disabled,
                    ):
                        with me.tooltip(message="rewrite prompt with Gemini"):
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    gap=3,
                                    align_items="center",
                                )
                            ):
                                me.icon("auto_awesome")
                                me.text("Rewriter")
                    # generate
                    me.button(
                        "Generate",
                        color="primary",
                        type="flat",
                        on_click=on_click_generate_images,
                    )

            # Modifiers
            with me.box(style=_BOX_STYLE):
                with me.box(
                    style=me.Style(
                        display="flex",
                        justify_content="space-between",
                        gap=2,
                        width="100%",
                    )
                ):
                    if state.show_advanced:
                        with me.content_button(on_click=on_click_advanced_controls):
                            with me.tooltip(message="hide advanced controls"):
                                with me.box(style=me.Style(display="flex")):
                                    me.icon("expand_less")
                    else:
                        with me.content_button(on_click=on_click_advanced_controls):
                            with me.tooltip(message="show advanced controls"):
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
                        key="aspect_ratio",
                        on_selection_change=on_selection_change_image,
                        style=me.Style(width="160px"),
                        value=state.image_aspect_ratio,
                    )
                    me.select(
                        label="Content Type",
                        options=[
                            me.SelectOption(label="None", value="None"),
                            me.SelectOption(label="Photo", value="Photo"),
                            me.SelectOption(label="Art", value="Art"),
                        ],
                        key="content_type",
                        on_selection_change=on_selection_change_image,
                        style=me.Style(width="160px"),
                        value=state.image_content_type,
                    )

                    color_and_tone_options = []
                    for c in [
                        "None",
                        "Black and white",
                        "Cool tone",
                        "Golden",
                        "Monochromatic",
                        "Muted color",
                        "Pastel color",
                        "Toned image",
                    ]:
                        color_and_tone_options.append(me.SelectOption(label=c, value=c))
                    me.select(
                        label="Color & Tone",
                        options=color_and_tone_options,
                        key="color_tone",
                        on_selection_change=on_selection_change_image,
                        style=me.Style(width="160px"),
                        value=state.image_color_tone,
                    )

                    lighting_options = []
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
                    ]:
                        lighting_options.append(me.SelectOption(label=l, value=l))
                    me.select(
                        label="Lighting",
                        options=lighting_options,
                        key="lighting",
                        on_selection_change=on_selection_change_image,
                        value=state.image_lighting,
                    )

                    composition_options = []
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
                    ]:
                        composition_options.append(me.SelectOption(label=c, value=c))
                    me.select(
                        label="Composition",
                        options=composition_options,
                        key="composition",
                        on_selection_change=on_selection_change_image,
                        value=state.image_composition,
                    )

                # Advanced controls
                # negative prompt
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=5,
                    )
                ):
                    if state.show_advanced:
                        me.box(style=me.Style(width=67))
                        me.input(
                            label="negative phrases",
                            on_blur=on_blur_image_negative_prompt,
                            value=state.image_negative_prompt_placeholder,
                            key=str(state.image_negative_prompt_key),
                            style=me.Style(
                                width="350px",
                            ),
                        )
                        me.select(
                            label="number of images",
                            value="3",
                            options=[
                                me.SelectOption(label="1", value="1"),
                                me.SelectOption(label="2", value="2"),
                                me.SelectOption(label="3", value="3"),
                                me.SelectOption(label="4", value="4"),
                            ],
                            on_selection_change=on_select_image_count,
                            key="imagen_image_count",
                            style=me.Style(width="155px"),
                        )
                        me.checkbox(
                            label="watermark",
                            checked=True,
                            disabled=True,
                            key="imagen_watermark",
                        )
                        me.input(
                            label="seed",
                            disabled=True,
                            key="imagen_seed",
                        )

            # Image output
            with me.box(style=_BOX_STYLE):
                me.text("Output", style=me.Style(font_weight=500))
                if state.is_loading:
                    with me.box(
                        style=me.Style(
                            display="grid",
                            justify_content="center",
                            justify_items="center",
                        )
                    ):
                        me.progress_spinner()
                if len(state.image_output) != 0:
                    with me.box(
                        style=me.Style(
                            display="grid",
                            justify_content="center",
                            justify_items="center",
                        )
                    ):
                        # Generated images row
                        with me.box(
                            style=me.Style(flex_wrap="wrap", display="flex", gap="15px")
                        ):
                            for _, img in enumerate(state.image_output):
                                # print(f"{idx}: {len(img)}")
                                img_url = img.replace(
                                    "gs://",
                                    "https://storage.mtls.cloud.google.com/",
                                )
                                me.image(
                                    # src=f"data:image/png;base64,{img}",
                                    src=f"{img_url}",
                                    style=me.Style(
                                        width="300px",
                                        margin=me.Margin(top=10),
                                        border_radius="35px",
                                    ),
                                )

                        # SynthID notice
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction="row",
                                align_items="center",
                            )
                        ):
                            svg_icon_component(
                                svg="""<svg data-icon-name="digitalWatermarkIcon" viewBox="0 0 24 24" width="24" height="24" fill="none" aria-hidden="true" sandboxuid="2"><path fill="#3367D6" d="M12 22c-.117 0-.233-.008-.35-.025-.1-.033-.2-.075-.3-.125-2.467-1.267-4.308-2.833-5.525-4.7C4.608 15.267 4 12.983 4 10.3V6.2c0-.433.117-.825.35-1.175.25-.35.575-.592.975-.725l6-2.15a7.7 7.7 0 00.325-.1c.117-.033.233-.05.35-.05.15 0 .375.05.675.15l6 2.15c.4.133.717.375.95.725.25.333.375.717.375 1.15V10.3c0 2.683-.625 4.967-1.875 6.85-1.233 1.883-3.067 3.45-5.5 4.7-.1.05-.2.092-.3.125-.1.017-.208.025-.325.025zm0-2.075c2.017-1.1 3.517-2.417 4.5-3.95 1-1.55 1.5-3.442 1.5-5.675V6.175l-6-2.15-6 2.15V10.3c0 2.233.492 4.125 1.475 5.675 1 1.55 2.508 2.867 4.525 3.95z" sandboxuid="2"></path><path fill="#3367D6" d="M12 16.275c0-.68-.127-1.314-.383-1.901a4.815 4.815 0 00-1.059-1.557 4.813 4.813 0 00-1.557-1.06 4.716 4.716 0 00-1.9-.382c.68 0 1.313-.128 1.9-.383a4.916 4.916 0 002.616-2.616A4.776 4.776 0 0012 6.475c0 .672.128 1.306.383 1.901a5.07 5.07 0 001.046 1.57 5.07 5.07 0 001.57 1.046 4.776 4.776 0 001.901.383c-.672 0-1.306.128-1.901.383a4.916 4.916 0 00-2.616 2.616A4.716 4.716 0 0012 16.275z" sandboxuid="2"></path></svg>"""
                            )

                            me.text(
                                text="images watermarked by SynthID",
                                style=me.Style(
                                    padding=me.Padding.all(10),
                                    font_size="0.95em",
                                ),
                            )
                else:
                    if state.is_loading:
                        me.text(
                            text="generating images!",
                            style=me.Style(
                                display="grid",
                                justify_content="center",
                                padding=me.Padding.all(20),
                            ),
                        )
                    else:
                        me.text(
                            text="generate some images!",
                            style=me.Style(
                                display="grid",
                                justify_content="center",
                                padding=me.Padding.all(20),
                            ),
                        )

            # Image commentary
            if len(state.image_output) != 0:
                with me.box(style=_BOX_STYLE):
                    with me.box(
                        style=me.Style(
                            display="flex",
                            justify_content="space-between",
                            gap=2,
                            width="100%",
                        )
                    ):
                        with me.box(
                            style=me.Style(
                                flex_wrap="wrap",
                                display="flex",
                                flex_direction="row",
                                # width="85%",
                                padding=me.Padding.all(10),
                            )
                        ):
                            me.icon("assistant")
                            me.text(
                                "magazine editor",
                                style=me.Style(font_weight=500),
                            )
                            me.markdown(
                                text=state.image_commentary,
                                style=me.Style(padding=me.Padding.all(15)),
                            )


def on_blur_image_prompt(e: me.InputBlurEvent):
    """Image Blur Event"""
    me.state(PageState).image_prompt_input = e.value


def on_blur_image_negative_prompt(e: me.InputBlurEvent):
    """Image Blur Event"""
    me.state(PageState).image_negative_prompt_input = e.value


def on_click_generate_images(e: me.ClickEvent):
    """Click Event to generate images."""
    state = me.state(PageState)
    state.is_loading = True
    state.image_output.clear()
    yield
    generate_images(state.image_prompt_input)
    generate_compliment(state.image_prompt_input)
    state.is_loading = False
    yield


def on_select_image_count(e: me.SelectSelectionChangeEvent):
    """Change Event For Selecting an Image Model."""
    state = me.state(PageState)
    setattr(state, e.key, e.value)


def generate_images(input_txt: str):
    """Generate Images"""
    state = me.state(PageState)

    # handle condition where someone hits "random" but doens't modify
    if not input_txt and state.image_prompt_placeholder:
        input_txt = state.image_prompt_placeholder
    state.image_output.clear()
    modifiers = []
    for mod in app_config_instance.image_modifiers:
        if mod != "aspect_ratio":
            if getattr(state, f"image_{mod}") != "None":
                modifiers.append(getattr(state, f"image_{mod}"))
    prompt_modifiers = ", ".join(modifiers)
    prompt = f"{input_txt} {prompt_modifiers}"
    print(f"prompt: {prompt}")
    if state.image_negative_prompt_input:
        print(f"negative prompt: {state.image_negative_prompt_input}")
    print(f"model: {state.image_model_name}")

    # image_generation_model = ImageGenerationModel.from_pretrained(
    #     state.image_model_name
    # )
    # response = image_generation_model.generate_images(
    #     prompt=prompt,
    #     add_watermark=True,
    #     aspect_ratio=getattr(state, "image_aspect_ratio"),
    #     number_of_images=int(state.imagen_image_count),
    #     output_gcs_uri=f"gs://{config.IMAGE_BUCKET}",
    #     language="auto",
    #     negative_prompt=state.image_negative_prompt_input,
    # )

    response = image_generation(state.image_model_name, prompt)

    # Check if response has generated_images and it's a list
    if hasattr(response, 'generated_images') and isinstance(response.generated_images, list):
        if not response.generated_images:
            print("No images were generated (generated_images list is empty).")
        for idx, img_obj in enumerate(response.generated_images):
            # img_obj is now directly the GeneratedImage object.
            # If include_rai_reason=True, the RAI reason might be an attribute of img_obj
            # or accessible via another part of the 'response' object.
            # For now, we assume img_obj is the GeneratedImage.

            image_uri = img_obj.uri
            b64_string = img_obj.base64_string

            size_str = "N/A"
            if b64_string is not None:
                size_str = str(len(b64_string))
            
            uri_str = "N/A"
            if image_uri is not None:
                uri_str = image_uri
                state.image_output.append(image_uri) # Append valid URI
            
            print(
                f"generated image: {idx} size: {size_str} at {uri_str}"
            )
    else:
        print("Error: 'generated_images' attribute not found in response or is not a list.")
        # For debugging, you might want to log the actual response:
        # print(f"Response type: {type(response)}, Response content: {response}")


def on_image_input(e: me.InputEvent):
    """Image Input Event"""
    state = me.state(PageState)
    state.image_prompt_input = e.value


def random_prompt_generator(e: me.ClickEvent):
    """Click Event to generate a random prompt from a list of predefined prompts."""
    state = me.state(PageState)
    with open(app_config_instance.IMAGEN_PROMPTS_JSON, "r", encoding="utf-8") as file:
        data = file.read()
    prompts = json.loads(data)
    random_prompt = random.choice(prompts["imagen"])
    state.image_prompt_placeholder = random_prompt
    on_image_input(
        me.InputEvent(key=str(state.image_textarea_key), value=random_prompt)
    )
    print(f"preset chosen: {random_prompt}")
    yield


# advanced controls
def on_click_advanced_controls(e: me.ClickEvent):
    """Click Event to toggle advanced controls."""
    me.state(PageState).show_advanced = not me.state(PageState).show_advanced


def on_click_clear_images(e: me.ClickEvent):
    """Click Event to clear images."""
    state = me.state(PageState)
    state.image_prompt_input = ""
    state.image_prompt_placeholder = ""
    state.image_output.clear()
    state.image_negative_prompt_input = ""
    state.image_textarea_key += 1
    state.image_negative_prompt_key += 1


def on_selection_change_image(e: me.SelectSelectionChangeEvent):
    """Change Event For Selecting an Image Model."""
    state = me.state(PageState)
    print(f"changed: {e.key}={e.value}")
    setattr(state, f"image_{e.key}", e.value)


def on_click_rewrite_prompt(e: me.ClickEvent):
    """Click Event to rewrite prompt."""
    state = me.state(PageState)
    if state.image_prompt_input:
        print("got prompt, rewriting...")
        rewritten = rewrite_prompt(state.image_prompt_input)
        state.image_prompt_input = rewritten
        state.image_prompt_placeholder = rewritten


def rewrite_prompt(original_prompt: str):
    """
    Outputs a rewritten prompt

    Args:
        original_prompt (str): artists's original prompt
    """
    # state = me.state(State)
    all_together_now = REWRITER_PROMPT.format(original_prompt)

    try:
        rewritten = rewriter(all_together_now, "")
    except Exception as e:
        print(f"an error {e}")

    print(f"asked to rewrite: '{original_prompt}")
    print(f"rewritten as: {rewritten}")
    return rewritten


_BOX_STYLE = me.Style(
    #flex_basis="max(480px, calc(50% - 48px))",
    # background="#fff",
    background=me.theme_var("background"),
    border_radius=12,
    box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
    padding=me.Padding(top=16, left=16, right=16, bottom=16),
    display="flex",
    flex_direction="column",
    margin=me.Margin(bottom=28)
)


def generate_compliment(generation_instruction: str):
    """
    Outputs a Gemini generated comment about images
    """
    state = me.state(PageState)
    start_time = time.time()  # Record the starting time
    critique = ""
    current_error_message = ""

    try:
        critique = image_critique(generation_instruction, state.image_output)

    # Catch specific exceptions you anticipate
    except ValueError as err:
        print(f"ValueError caught: {err}")
        current_error_message = f"Input Error: {err}"
    except requests.exceptions.HTTPError as err:
        print(f"HTTPError caught: {err}")
        current_error_message = f"Network/API Error: {err}"
    # Catch any other unexpected exceptions
    except Exception as err:
        print(f"Generic Exception caught: {type(err).__name__}: {err}")
        current_error_message = f"An unexpected error occurred: {err}"

    finally:
        end_time = time.time()  # Record the ending time
        execution_time = end_time - start_time  # Calculate the elapsed time
        print(f"Execution time: {execution_time} seconds")  # Print the execution time
        state.timing = f"Generation time: {round(execution_time)} seconds"

        #  If an error occurred, update the state to show the dialog
        if current_error_message:
            state.error_message = current_error_message
            state.show_error_dialog = True
            # Ensure no result video is displayed on error
            state.result_video = ""

        # try:
        #     add_video_metadata(
        #         gcs_uri,
        #         state.veo_prompt_input,
        #         aspect_ratio,
        #         veo_model,
        #         execution_time,
        #         state.video_length,
        #         state.reference_image_gcs,
        #         rewrite_prompt,
        #         error_message=current_error_message,
        #         comment="veo2 default generation",
        #         last_reference_image=state.last_reference_image_gcs,
        #     )
        # except Exception as meta_err:
        #     # Handle potential errors during metadata storage itself
        #     print(f"CRITICAL: Failed to store metadata: {meta_err}")
        #     # Optionally, display another error or log this critical failure
        #     if not state.show_error_dialog:  # Avoid overwriting primary error
        #         state.error_message = f"Failed to store video metadata: {meta_err}"
        #         state.show_error_dialog = True

    state.image_commentary = critique
    state.is_loading = False
    yield
    print(
        "I don't listen to what art critics say. I don't know anybody who needs a critic to find out what art is. - Basquiat"
    )
