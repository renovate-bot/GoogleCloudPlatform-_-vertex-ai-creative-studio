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

"""Interior Design page."""

import datetime
from dataclasses import field, asdict
import uuid
import json

import mesop as me

from common.analytics import log_ui_click, track_click

from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import store_to_gcs
from components.header import header
from components.dialog import dialog
from components.info_dialog.info_dialog import info_dialog
from components.library.events import LibrarySelectionChangeEvent
from components.page_scaffold import page_frame, page_scaffold
from components.interior_design.floor_plan_uploader import floor_plan_uploader
from components.interior_design.generated_3d_view import generated_3d_view
from components.interior_design.room_selector import room_selector
from components.interior_design.room_view import room_view
from components.interior_design.design_studio import design_studio
from config.default import Default as cfg
from models.gemini import (
    extract_room_names_from_image,
    generate_image_from_prompt_and_images,
)
from state.state import AppState


with open("config/about_content.json", "r") as f:
    about_content = json.load(f)
    INTERIOR_DESIGN_INFO = next(
        (
            s
            for s in about_content["sections"]
            if s.get("id") == "interior_design"
        ),
        None,
    )


from state.state import AppState
from state.interior_design_v2_state import PageState


@me.page(
    path="/interior_design",
    title="Interior Design V2",
)
def interior_design_page():
    with page_scaffold(page_name="interior_design_v2"):  # pylint: disable=E1129:not-context-manager
        with page_frame():  # pylint: disable=E1129:not-context-manager
            header("Interior Design", "chair", show_info_button=True, on_info_click=open_info_dialog)
            page_content()


def page_content():
    state = me.state(PageState)

    info_dialog(
        is_open=state.info_dialog_open,
        info_data=INTERIOR_DESIGN_INFO,
        on_close=close_info_dialog,
        default_title="Interior Design",
    )

    with me.box(
        style=me.Style(
            display="flex", flex_direction="column", gap=24, align_items="center"
        )
    ):
        # Input and Output Area
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=32, justify_content="center"
            )
        ):
            floor_plan_uploader(
                storyboard=state.storyboard,
                on_upload=on_upload_floor_plan,
                on_library_select=on_select_floor_plan,
            )
            generated_3d_view(
                storyboard=state.storyboard,
                is_generating=state.is_generating,
                on_generate=on_generate_3d_view_click,
            )

        if state.storyboard and state.storyboard.get("room_names"):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    gap=10,
                )
            ):
                me.text("Identified Rooms", type="headline-6")
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=10,
                        flex_wrap="wrap",
                        justify_content="center",
                    )
                ):
                    for room in state.storyboard["room_names"]:
                        with me.content_button(
                            key=room, on_click=on_room_button_click, type="stroked"
                        ):
                            if state.is_generating_zoom and state.storyboard.get("selected_room") == room:
                                me.progress_spinner(diameter=18)
                            else:
                                me.text(room)

        # Display the zoomed-in room view and design controls
        if state.storyboard and state.storyboard.get("storyboard_items"):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=24,
                    margin=me.Margin(top=24),
                    width="100%",
                    justify_content="center",
                )
            ):
                room_view(
                    storyboard=state.storyboard,
                    is_generating_zoom=state.is_generating_zoom,
                )
                design_studio(
                    storyboard_item=next((item for item in state.storyboard["storyboard_items"] if item["room_name"] == state.storyboard["selected_room"]), None),
                    design_image_uri=state.design_image_uri,
                    is_designing=state.is_designing,
                    on_upload_design_image=on_upload_design_image,
                    on_select_design_image=on_select_design_image,
                    on_design_prompt_blur=on_design_prompt_blur,
                    on_clear_design=on_clear_design,
                    on_design_click=on_design_click,
                )

        if state.error_message:
            me.text(state.error_message, style=me.Style(color="red"))


# --- Event Handlers ---


def on_upload_floor_plan(e: me.UploadEvent):
    """Upload floor plan handler."""
    state = me.state(PageState)
    app_state = me.state(AppState)
    file = e.files[0]
    gcs_url = store_to_gcs(
        "interior_design_uploads", file.name, file.mime_type, file.getvalue()
    )
    state.storyboard = {
        "user_email": app_state.user_email,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "original_floor_plan_uri": gcs_url,
        "room_names": [],
        "storyboard_items": [],
        "selected_room": "",
    }
    print(f"storyboard created: {state.storyboard}")
    yield


def on_select_floor_plan(e: LibrarySelectionChangeEvent):
    """Floor plan selection from library handler."""
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.storyboard = {
        "user_email": app_state.user_email,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "original_floor_plan_uri": e.gcs_uri,
        "room_names": [],
        "storyboard_items": [],
        "selected_room": "",
    }
    print(f"storyboard created: {state.storyboard}")
    yield


@track_click(element_id="interior_design_generate_3d_view_button")
def on_generate_3d_view_click(e: me.ClickEvent):
    """Handles the 3D view generation."""
    state = me.state(PageState)
    state.is_generating = True
    state.storyboard["generated_3d_view_uri"] = ""
    state.storyboard["room_names"] = []
    state.error_message = ""
    yield

    try:
        prompt = "create a 3D version for the floor plan. make it realistic. keep the furnitures as per the floor plan and follow the measurement. retain the names of rooms in the appropriate location"

        gcs_uris, _ = generate_image_from_prompt_and_images(
            prompt=prompt,
            images=[state.storyboard["original_floor_plan_uri"]],
            gcs_folder="interior_design_generations",
        )

        if gcs_uris:
            state.storyboard["generated_3d_view_uri"] = gcs_uris[0]

            try:
                room_names = extract_room_names_from_image(state.storyboard["original_floor_plan_uri"])
                state.storyboard["room_names"] = room_names
            except Exception as room_ex:
                print(f"Could not extract room names: {room_ex}")
                state.error_message = "An error occurred while extracting room names from the floor plan."

        else:
            state.error_message = "Image generation failed to return a result."

    except Exception as ex:
        state.error_message = f"An error occurred during generation: {ex}"
    finally:
        state.is_generating = False
        yield


@track_click(element_id="interior_design_room_button")
def on_room_button_click(e: me.ClickEvent):
    """Handles the generation of a zoomed-in view for a specific room."""
    state = me.state(PageState)
    room_name = e.key

    # Find the existing storyboard item for this room, or create a new one
    storyboard_item = next((item for item in state.storyboard["storyboard_items"] if item["room_name"] == room_name), None)
    if not storyboard_item:
        storyboard_item = {"room_name": room_name, "styled_image_uri": "", "style_history": []}
        state.storyboard["storyboard_items"].append(storyboard_item)

    state.is_generating_zoom = True
    state.storyboard["selected_room"] = room_name
    storyboard_item["styled_image_uri"] = ""
    state.error_message = ""
    yield

    try:
        prompt = f"Using the provided 3D rendering as a layout guide, create a photorealistic interior photograph. The photo should be from a first-person perspective, as if a person is standing in the hallway or adjacent room and looking through the doorway into the {room_name}. Capture the sense of entering the room for the first time on a house tour. Ensure the lighting and furniture placement are consistent with the 3D model."

        gcs_uris, _ = generate_image_from_prompt_and_images(
            prompt=prompt,
            images=[state.storyboard["generated_3d_view_uri"]],  # Use the 3D view as input
            gcs_folder="interior_design_zoomed_views",
        )

        if gcs_uris:
            storyboard_item["styled_image_uri"] = gcs_uris[0]
            storyboard_item["style_history"].append(gcs_uris[0])
        else:
            state.error_message = "Zoomed view generation failed to return a result."

    except Exception as ex:
        state.error_message = f"An error occurred during zoom generation: {ex}"
    finally:
        state.is_generating_zoom = False
        yield


def on_design_prompt_blur(e: me.InputBlurEvent):
    """Updates the design prompt in the page state."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="interior_design_design_prompt",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(PageState)
    state.design_prompt = e.value


def on_clear_design(e: me.ClickEvent):
    """Clear design prompt and image."""
    state = me.state(PageState)
    state.design_prompt = ""
    state.design_image_uri = ""
    yield


def on_upload_design_image(e: me.UploadEvent):
    """Upload design image handler."""
    state = me.state(PageState)
    file = e.files[0]
    gcs_url = store_to_gcs(
        "interior_design_uploads", file.name, file.mime_type, file.getvalue()
    )
    state.design_image_uri = gcs_url
    yield


def on_select_design_image(e: LibrarySelectionChangeEvent):
    """Design image selection from library handler."""
    state = me.state(PageState)
    state.design_image_uri = e.gcs_uri
    yield


@track_click(element_id="interior_design_design_button")
def on_design_click(e: me.ClickEvent):
    """Handles the iterative design generation."""
    state = me.state(PageState)

    if not state.design_prompt:
        state.error_message = "Please enter a design modification prompt."
        yield
        return

    state.is_designing = True
    state.error_message = ""
    yield

    try:
        # Find the current storyboard item
        storyboard_item = next((item for item in state.storyboard["storyboard_items"] if item["room_name"] == state.storyboard["selected_room"]), None)
        if not storyboard_item:
            state.error_message = "Could not find the current room to style."
            yield
            return

        images = [storyboard_item["styled_image_uri"]]
        if state.design_image_uri:
            images.append(state.design_image_uri)

        gcs_uris, _ = generate_image_from_prompt_and_images(
            prompt=state.design_prompt,
            images=images,  # Use the current zoomed view as input
            gcs_folder="interior_design_iterations",
        )

        if gcs_uris:
            # Update the styled image with the new image, creating the loop
            storyboard_item["styled_image_uri"] = gcs_uris[0]
            storyboard_item["style_history"].append(gcs_uris[0])

            # Clear the prompt for the next input
            state.design_prompt = ""
            state.design_image_uri = ""
        else:
            state.error_message = "Design generation failed to return a result."

    except Exception as ex:
        state.error_message = f"An error occurred during design generation: {ex}"
    finally:
        state.is_designing = False
        yield

def open_info_dialog(e: me.ClickEvent):
    """Open the info dialog."""
    print("DEBUG: open_info_dialog called")
    state = me.state(PageState)
    state.info_dialog_open = True
    yield


@track_click(element_id="interior_design_close_info_dialog_button")
def close_info_dialog(e: me.ClickEvent):
    """Close the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = False
    yield
