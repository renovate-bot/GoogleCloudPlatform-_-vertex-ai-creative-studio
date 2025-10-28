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
"""Veo mesop UI page."""

import datetime  # Required for timestamp
import time

import mesop as me

from common.analytics import log_ui_click, track_click, track_model_call
from common.error_handling import GenerationError
from common.metadata import MediaItem, add_media_item_to_firestore  # Updated import
from common.storage import store_to_gcs
from common.utils import create_display_url
from components.dialog import dialog, dialog_actions
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.page_scaffold import page_frame, page_scaffold
from components.veo.generation_controls import generation_controls
from components.veo.prompt_inputs import prompt_inputs
from components.veo.veo_modes import veo_modes
from components.veo.video_display import video_display
from config.default import ABOUT_PAGE_CONTENT, Default
from config.rewriters import VIDEO_REWRITER
from config.veo_models import get_veo_model_config
from models.gemini import rewriter
from models.model_setup import VeoModelSetup
from models.veo import APIReferenceImage, VideoGenerationRequest, generate_video
from state.state import AppState
from state.veo_state import PageState

config = Default()

veo_model = VeoModelSetup.init()


def on_veo_load(e: me.LoadEvent):
    """Handles page load events, including query parameters for deep linking."""
    state = me.state(PageState)
    image_path = me.query_params.get("image_path")  # Changed from image_uri
    veo_model_param = me.query_params.get("veo_model")

    if veo_model_param:
        _update_state_for_new_model(veo_model_param)

    if image_path:
        # When an image is passed, default to the i2v mode and Veo 3.1 Fast model.
        _update_state_for_new_model("3.1-fast")

        image_uri = ""
        if image_path.startswith("https://"):
            from common.utils import https_url_to_gcs_uri

            image_uri = https_url_to_gcs_uri(image_path)
        else:
            # Reconstruct the full GCS URI from the path for backward compatibility
            image_uri = f"gs://{image_path}"

        # Set the image from the query parameter
        state.reference_image_gcs = image_uri
        state.reference_image_uri = create_display_url(image_uri)
        # Switch to the Image-to-Video tab
        state.veo_mode = "i2v"
        # Provide a default prompt for a better user experience
        state.veo_prompt_input = "Animate this image with subtle motion."

    yield


@me.page(
    path="/veo",
    title="Veo - GenMedia Creative Studio",
    on_load=on_veo_load,
)
def veo_page():
    """Main Page."""
    state = me.state(AppState)
    with page_scaffold(page_name="veo"):  # pylint: disable=not-context-manager
        veo_content(state)


def on_selection_change_person_generation(e: me.SelectSelectionChangeEvent):
    """Handles changes to the person generation setting."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="veo_person_generation",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(PageState)
    state.person_generation = e.value
    yield


def on_change_video_length_select(e: me.SelectSelectionChangeEvent):
    """Handles changes to the video length select dropdown."""
    state = me.state(PageState)
    state.video_length = int(e.value)
    yield


def on_selection_change_aspect_ratio(e: me.SelectSelectionChangeEvent):
    """Handles changes to the aspect ratio setting."""
    state = me.state(PageState)
    state.aspect_ratio = e.value
    yield


def on_selection_change_resolution(e: me.SelectSelectionChangeEvent):
    """Handles changes to the resolution setting."""
    state = me.state(PageState)
    state.resolution = e.value
    yield


def on_selection_change_video_count(e: me.SelectSelectionChangeEvent):
    """Handles changes to the video count slider."""
    state = me.state(PageState)
    state.video_count = int(e.value)
    yield


def _update_state_for_new_model(model_version_id: str):
    """Update state when the model changes."""
    state = me.state(PageState)
    state.veo_model = model_version_id

    # Get the config for the NEW model
    new_model_config = get_veo_model_config(model_version_id)
    if new_model_config:
        # If the current mode is not supported by the new model, reset to default 't2v'.
        if state.veo_mode not in new_model_config.supported_modes:
            state.veo_mode = "t2v"

        # If the new model has a specific list of supported durations (discontinuous values)
        if new_model_config.supported_durations:
            # Check if the current video length is in the allowed list.
            if state.video_length not in new_model_config.supported_durations:
                # If not, reset to the model's default duration.
                state.video_length = new_model_config.default_duration
        # Otherwise, use the continuous min/max range
        else:
            min_dur = new_model_config.min_duration
            max_dur = new_model_config.max_duration
            if not (min_dur <= state.video_length <= max_dur):
                state.video_length = new_model_config.default_duration

        # Check for aspect ratio override for the current mode
        if (
            new_model_config.mode_overrides
            and state.veo_mode in new_model_config.mode_overrides
        ):
            override = new_model_config.mode_overrides[state.veo_mode]
            if (
                override.supported_aspect_ratios
                and state.aspect_ratio not in override.supported_aspect_ratios
            ):
                state.aspect_ratio = override.supported_aspect_ratios[0]


def on_selection_change_veo_model(e: me.SelectSelectionChangeEvent):
    """Handle changes to the Veo model selection."""
    _update_state_for_new_model(e.value)
    yield


def on_change_auto_enhance_prompt(e: me.CheckboxChangeEvent):
    """Toggle auto-enhance prompt."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="veo_auto_enhance_prompt",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"checked": e.checked},
    )
    state = me.state(PageState)
    state.auto_enhance_prompt = e.checked
    yield


def veo_content(app_state: me.state):
    """Veo Mesop Page."""
    state = me.state(PageState)

    if state.info_dialog_open:
        with dialog(is_open=state.info_dialog_open):  # pylint: disable=E1129:not-context-manager
            me.text("About Veo", type="headline-6")
            me.markdown(ABOUT_PAGE_CONTENT["sections"][1]["description"])
            me.divider()
            me.text("Current Settings", type="headline-6")
            me.text(f"Prompt: {state.veo_prompt_input}")
            me.text(f"Negative Prompt: {state.negative_prompt}")
            me.text(f"Model: {state.veo_model}")
            me.text(f"Duration: {state.video_length}s")

            # Mode-specific settings display
            if state.veo_mode == "i2v":
                if state.reference_image_gcs:
                    me.text(f"Input Image: {state.reference_image_gcs}")
            elif state.veo_mode == "interpolation":
                if state.reference_image_gcs:
                    me.text(f"First Frame: {state.reference_image_gcs}")
                if state.last_reference_image_gcs:
                    me.text(f"Last Frame: {state.last_reference_image_gcs}")
            elif state.veo_mode == "r2v":
                if state.r2v_reference_images:
                    me.text(f"Asset Images: {len(state.r2v_reference_images)} selected")
                if state.r2v_style_image:
                    me.text(f"Style Image: {state.r2v_style_image}")

            with dialog_actions():  # pylint: disable=E1129:not-context-manager
                me.button("Close", on_click=close_info_dialog, type="flat")

    with page_frame():  # pylint: disable=E1129:not-context-manager
        header("Veo", "movie", show_info_button=True, on_info_click=open_info_dialog)

        # Main container with a column direction
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=20)):
            # --- TOP ROW ---
            # A nested container with a row direction
            with me.box(style=me.Style(display="flex", flex_direction="row", gap=10)):
                # Left column of the top row
                with me.box(
                    style=me.Style(
                        flex_basis="max(480px, calc(60% - 48px))",
                        display="flex",
                        flex_direction="column",
                        gap=10,
                    )
                ):
                    prompt_inputs(
                        on_click_generate=on_click_veo,
                        on_click_rewrite=on_click_custom_rewriter,
                        on_click_clear=on_click_clear,
                        on_blur_prompt=on_blur_veo_prompt,
                        on_blur_negative_prompt=on_blur_negative_prompt,
                    )

                # Right column of the top row
                veo_modes(
                    on_upload_image=on_upload_image,
                    on_upload_last_image=on_upload_last_image,
                    on_library_select=on_veo_image_from_library,
                    on_r2v_asset_add=on_r2v_asset_add,
                    on_r2v_asset_remove=on_r2v_asset_remove,
                    on_r2v_style_add=on_r2v_style_add,
                    on_r2v_style_remove=on_r2v_style_remove,
                    on_click_clear=on_click_clear,
                    on_clear_first_image=on_clear_first_image,
                    on_clear_last_image=on_clear_last_image,
                )

            # --- SECOND ROW ---
            # This component will now be in its own row underneath
            generation_controls(
                on_selection_change_veo_model=on_selection_change_veo_model,
                on_selection_change_aspect_ratio=on_selection_change_aspect_ratio,
                on_selection_change_resolution=on_selection_change_resolution,
                on_change_video_length_select=on_change_video_length_select,
                on_selection_change_video_count=on_selection_change_video_count,
                on_selection_change_person_generation=on_selection_change_person_generation,
                on_change_auto_enhance_prompt=on_change_auto_enhance_prompt,
            )

        me.box(style=me.Style(height=50))

        video_display(on_thumbnail_click=on_thumbnail_click)

    with dialog(is_open=state.show_error_dialog):  # pylint: disable=E1129:not-context-manager
        me.text(
            "Generation Error",
            type="headline-6",
            style=me.Style(color=me.theme_var("error")),
        )
        me.text(state.error_message, style=me.Style(margin=me.Margin(top=16)))
        with dialog_actions():  # pylint: disable=E1129:not-context-manager
            me.button("Close", on_click=on_close_error_dialog, type="flat")


def on_input_prompt(e: me.InputEvent):
    state = me.state(PageState)
    state.prompt = e.value
    yield


def on_blur_negative_prompt(e: me.InputBlurEvent):
    state = me.state(PageState)
    state.negative_prompt = e.value
    yield


@track_click(element_id="veo_clear_button")
def on_click_clear(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Clear prompt and video."""
    state = me.state(PageState)
    state.result_gcs_uris = []
    state.result_display_urls = []
    state.selected_video_url = ""
    state.prompt = None
    state.negative_prompt = ""
    state.veo_prompt_input = None
    state.original_prompt = None
    state.veo_prompt_textarea_key += 1
    state.video_length = 5
    state.aspect_ratio = "16:9"
    state.is_loading = False
    state.auto_enhance_prompt = False
    state.veo_model = "2.0"
    # Clear all image types
    state.reference_image_gcs = None
    state.reference_image_uri = None
    state.last_reference_image_gcs = None
    state.last_reference_image_uri = None
    state.r2v_reference_images = []
    state.r2v_reference_mime_types = []
    state.r2v_style_image = None
    state.r2v_style_image_mime_type = None
    yield


def on_clear_first_image(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Clears the first reference image for i2v or interpolation."""
    state = me.state(PageState)
    state.reference_image_gcs = None
    state.reference_image_uri = None
    yield


def on_clear_last_image(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Clears the last reference image for interpolation."""
    state = me.state(PageState)
    state.last_reference_image_gcs = None
    state.last_reference_image_uri = None
    yield


@track_click(element_id="veo_rewrite_button")
def on_click_custom_rewriter(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Veo custom rewriter."""
    state = me.state(PageState)
    if not state.veo_prompt_input:
        print("Prompt is empty, skipping rewrite.")
        yield
        return
    rewritten_prompt = rewriter(state.veo_prompt_input, VIDEO_REWRITER)
    state.veo_prompt_input = rewritten_prompt
    state.veo_prompt_placeholder = rewritten_prompt
    yield


@track_click(element_id="veo_create_button")
def on_click_veo(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Veo generate request handler."""
    app_state = me.state(AppState)
    state = me.state(PageState)

    if state.veo_mode == "t2v" and not state.veo_prompt_input:
        state.error_message = "Prompt cannot be empty for VEO generation."
        state.show_error_dialog = True
        yield
        return

    state.is_loading = True
    state.show_error_dialog = False
    state.error_message = ""
    state.result_video = ""
    state.timing = ""
    yield

    start_time = time.time()

    request = VideoGenerationRequest(
        prompt=state.veo_prompt_input,
        negative_prompt=state.negative_prompt,
        duration_seconds=state.video_length,
        video_count=state.video_count,
        aspect_ratio=state.aspect_ratio,
        resolution=state.resolution,
        enhance_prompt=state.auto_enhance_prompt,
        model_version_id=state.veo_model,
        person_generation=state.person_generation,
        reference_image_gcs=state.reference_image_gcs,
        last_reference_image_gcs=state.last_reference_image_gcs,
        reference_image_mime_type=state.reference_image_mime_type,
        last_reference_image_mime_type=state.last_reference_image_mime_type,
        r2v_references=[
            APIReferenceImage(gcs_uri=uri, mime_type=mime)
            for uri, mime in zip(
                state.r2v_reference_images, state.r2v_reference_mime_types
            )
        ]
        if state.veo_mode == "r2v" and state.r2v_reference_images
        else None,
        r2v_style_image=APIReferenceImage(
            gcs_uri=state.r2v_style_image, mime_type=state.r2v_style_image_mime_type
        )
        if state.veo_mode == "r2v" and state.r2v_style_image
        else None,
    )

    item_to_log = MediaItem(
        user_email=app_state.user_email,
        timestamp=datetime.datetime.now(datetime.UTC),
        prompt=request.prompt,
        original_prompt=(
            state.original_prompt if state.original_prompt else request.prompt
        ),
        model=get_veo_model_config(request.model_version_id).model_name,
        mime_type="video/mp4",
        mode=state.veo_mode,
        aspect=request.aspect_ratio,
        duration=float(request.duration_seconds),
        reference_image=request.reference_image_gcs,
        last_reference_image=request.last_reference_image_gcs,
        r2v_reference_images=state.r2v_reference_images,
        r2v_style_image=state.r2v_style_image,
        negative_prompt=request.negative_prompt,
        enhanced_prompt_used=request.enhance_prompt,
        comment="veo default generation",
    )

    try:
        model_name_for_analytics = get_veo_model_config(
            request.model_version_id
        ).model_name
        with track_model_call(
            model_name=model_name_for_analytics,
            prompt_length=len(request.prompt) if request.prompt else 0,
            duration_seconds=request.duration_seconds,
            aspect_ratio=request.aspect_ratio,
            video_count=request.video_count,
            mode=state.veo_mode,
        ):
            gcs_uris, resolution = generate_video(request)

        # Create display URLs for the UI
        display_urls = [create_display_url(uri) for uri in gcs_uris]
        state.result_gcs_uris = gcs_uris
        state.result_display_urls = display_urls
        if display_urls:
            state.selected_video_url = display_urls[0]

        item_to_log.gcs_uris = gcs_uris  # Log permanent URIs
        item_to_log.gcsuri = gcs_uris[0] if gcs_uris else None
        item_to_log.resolution = resolution

    except GenerationError as ge:
        state.error_message = ge.message
        state.show_error_dialog = True
        state.result_video = ""
        item_to_log.error_message = ge.message
    except Exception as ex:
        state.error_message = (
            f"An unexpected error occurred during video generation: {str(ex)}"
        )
        state.show_error_dialog = True
        state.result_video = ""
        item_to_log.error_message = state.error_message

    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        state.timing = f"Generation time: {round(execution_time)} seconds"
        item_to_log.generation_time = execution_time

        try:
            add_media_item_to_firestore(item_to_log)
        except Exception as meta_err:
            print(f"CRITICAL: Failed to store metadata: {meta_err}")
            if not state.show_error_dialog:
                state.error_message = f"Failed to store video metadata: {meta_err}"
                state.show_error_dialog = True

    state.is_loading = False
    yield


def on_blur_veo_prompt(e: me.InputBlurEvent):
    """Veo prompt blur event."""
    state = me.state(PageState)
    state.veo_prompt_input = e.value
    yield


def on_thumbnail_click(e: me.ClickEvent):
    """Sets the clicked thumbnail as the main selected video."""
    state = me.state(PageState)
    state.selected_video_url = e.key
    yield


def on_close_error_dialog(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Handler to close the error dialog."""
    state = me.state(PageState)
    state.show_error_dialog = False
    yield


def open_info_dialog(e: me.ClickEvent):
    """Open the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = True
    yield


def close_info_dialog(e: me.ClickEvent):
    """Close the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = False
    yield


def on_upload_image(e: me.UploadEvent):
    """Upload image to GCS and update state."""
    state = me.state(PageState)
    try:
        # Store the uploaded file to GCS
        gcs_path = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, e.file.getvalue()
        )
        # Update the state with the new image details
        state.reference_image_gcs = gcs_path
        state.reference_image_uri = create_display_url(gcs_path)
        state.reference_image_mime_type = e.file.mime_type
        print(f"Image uploaded to {gcs_path} with mime type {e.file.mime_type}")
    except Exception as ex:
        state.error_message = f"Failed to upload image: {ex}"
        state.show_error_dialog = True
    yield


def on_upload_last_image(e: me.UploadEvent):
    """Upload last image to GCS and update state."""
    state = me.state(PageState)
    try:
        # Store the uploaded file to GCS
        gcs_path = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, e.file.getvalue()
        )
        # Update the state with the new image details
        state.last_reference_image_gcs = gcs_path
        state.last_reference_image_uri = create_display_url(gcs_path)
        state.last_reference_image_mime_type = e.file.mime_type
    except Exception as ex:
        state.error_message = f"Failed to upload image: {ex}"
        state.show_error_dialog = True
    yield


def on_r2v_asset_add(e: me.UploadEvent):
    """Adds a new asset reference image for R2V mode."""
    state = me.state(PageState)
    if len(state.r2v_reference_images) >= 3:
        state.error_message = "You can upload a maximum of 3 asset images."
        state.show_error_dialog = True
        yield
        return

    try:
        gcs_path = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, e.file.getvalue()
        )
        state.r2v_reference_images.append(gcs_path)
        state.r2v_reference_mime_types.append(e.file.mime_type)
    except Exception as ex:
        state.error_message = f"Failed to upload image: {ex}"
        state.show_error_dialog = True
    yield


def on_r2v_asset_remove(e: me.ClickEvent):
    """Removes an asset reference image from the R2V list."""
    state = me.state(PageState)
    index_to_remove = int(e.key)
    if 0 <= index_to_remove < len(state.r2v_reference_images):
        state.r2v_reference_images.pop(index_to_remove)
        state.r2v_reference_mime_types.pop(index_to_remove)
    yield


def on_r2v_style_add(e: me.UploadEvent):
    """Adds a style reference image for R2V mode."""
    state = me.state(PageState)
    try:
        gcs_path = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, e.file.getvalue()
        )
        state.r2v_style_image = gcs_path
        state.r2v_style_image_mime_type = e.file.mime_type
    except Exception as ex:
        state.error_message = f"Failed to upload image: {ex}"
        state.show_error_dialog = True
    yield


def on_r2v_style_remove(e: me.ClickEvent):
    """Removes the style reference image."""
    state = me.state(PageState)
    state.r2v_style_image = None
    state.r2v_style_image_mime_type = None
    yield


def on_veo_image_from_library(e: LibrarySelectionChangeEvent):
    """VEO image from library handler."""
    state = me.state(PageState)
    if e.chooser_id.startswith("i2v") or e.chooser_id.startswith("first_frame"):
        state.reference_image_gcs = e.gcs_uri
        state.reference_image_uri = create_display_url(e.gcs_uri)
    elif e.chooser_id.startswith("interpolation_last"):
        state.last_reference_image_gcs = e.gcs_uri
        state.last_reference_image_uri = create_display_url(e.gcs_uri)
    elif e.chooser_id.startswith("r2v_asset_library_chooser"):
        if len(state.r2v_reference_images) >= 3:
            state.error_message = "You can upload a maximum of 3 asset images."
            state.show_error_dialog = True
            yield
            return
        state.r2v_reference_images.append(e.gcs_uri)
        state.r2v_reference_mime_types.append("image/png")
    elif e.chooser_id.startswith("r2v_style_library_chooser"):
        state.r2v_style_image = e.gcs_uri
        state.r2v_style_image_mime_type = "image/png"

    yield
