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

import base64
import uuid
import time
import traceback
import mesop as me
from config.default import Default
from components.page_scaffold import page_scaffold, page_frame
from components.header import header
from components.library.library_chooser_button import library_chooser_button
from components.library.events import LibrarySelectionChangeEvent
from components.selfie_camera.selfie_camera import selfie_camera
from components.dialog import dialog
from common.utils import create_display_url
from common.storage import store_to_gcs
from common.metadata import add_media_item
from state.state import AppState
from pages.styles import _BOX_STYLE_CENTER_DISTRIBUTED
from workflows.retro_games_backend import (
    RetroGameWorkflowState, initialize_workflow,
    step_1_generate_8bit, step_2_generate_character_sheet,
    step_3_generate_video, step_4_append_bumper
)
from workflows.retro_games_config import RetroGameConfig

print(f"DEBUG: retro_games loaded. PROJECT_ID={Default().PROJECT_ID}")

@me.stateclass
class PageState:
    input_image_uri: str = ""
    input_image_display_url: str = ""
    selected_theme_value: str = "Dish" # Default to Dish
    
    # Removed workflow_state from PageState to avoid potential serialization issues
    is_running: bool = False
    current_step: str = ""
    
    # For UI display of intermediate results
    eight_bit_display_url: str = ""
    char_sheet_display_url: str = ""
    final_video_display_url: str = ""
    
    error_message: str = ""
    show_selfie_dialog: bool = False
    
    start_time: float = 0.0
    total_duration: str = ""

def on_upload(e: me.UploadEvent):
    state = me.state(PageState)
    data = e.file.getvalue()
    gcs_uri = store_to_gcs("uploads", e.file.name, e.file.mime_type, data)
    state.input_image_uri = gcs_uri
    state.input_image_display_url = create_display_url(gcs_uri)
    yield

def on_library_select(e: LibrarySelectionChangeEvent):
    state = me.state(PageState)
    state.input_image_uri = e.gcs_uri
    state.input_image_display_url = create_display_url(e.gcs_uri)
    yield

def on_theme_click(e: me.ClickEvent):
    state = me.state(PageState)
    state.selected_theme_value = e.key
    yield

def on_click_generate(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    
    if not state.input_image_uri:
        state.error_message = "Please select an input image first."
        yield
        return

    state.is_running = True
    state.error_message = ""
    state.eight_bit_display_url = ""
    state.char_sheet_display_url = ""
    state.final_video_display_url = ""
    state.current_step = "Initializing..."
    state.start_time = time.time()
    state.total_duration = ""
    yield
    
    try:
        theme = state.selected_theme_value
        wf_state = initialize_workflow(app_state.user_email, theme, state.input_image_uri)
        yield
        
        # Step 1
        state.current_step = "Generating 8-bit image..."
        yield
        wf_state = step_1_generate_8bit(wf_state)
        if wf_state.status == "error":
            raise Exception(wf_state.error_message)
        if wf_state.eight_bit_image_uri:
            state.eight_bit_display_url = create_display_url(wf_state.eight_bit_image_uri)
        yield
        
        # Step 2
        state.current_step = "Generating character sheet..."
        yield
        wf_state = step_2_generate_character_sheet(wf_state)
        if wf_state.status == "error":
             raise Exception(wf_state.error_message)
        if wf_state.character_sheet_uri:
            state.char_sheet_display_url = create_display_url(wf_state.character_sheet_uri)
        yield
        
        # Step 3
        state.current_step = "Generating video (this may take a minute)..."
        yield
        wf_state = step_3_generate_video(wf_state)
        if wf_state.status == "error":
             raise Exception(wf_state.error_message)
        yield

        # Step 4
        state.current_step = "Finalizing video..."
        yield
        wf_state = step_4_append_bumper(wf_state)
        if wf_state.status == "error":
             raise Exception(wf_state.error_message)
        if wf_state.final_video_uri:
            state.final_video_display_url = create_display_url(wf_state.final_video_uri)
            
            # Persist to Firestore
            try:
                config = RetroGameConfig()
                theme_8bit_logo = config.get_theme_8bit_logo(theme)
                
                r2v_refs = [
                    wf_state.eight_bit_image_uri,
                    wf_state.character_sheet_uri,
                    theme_8bit_logo
                ]
                add_media_item(
                    user_email=app_state.user_email,
                    prompt=wf_state.scene_direction, # Use scene direction as prompt for video
                    gcsuri=wf_state.final_video_uri,
                    mime_type="video/mp4",
                    media_type="video",
                    model="veo-3.1-generate-preview",
                    duration=8.0, # Approx, includes bumper
                    comment=f"Retro Game Workflow ({theme} Theme)",
                    r2v_reference_images=r2v_refs,
                    mode="r2v"
                )
            except Exception as e:
                print(f"Error saving to Firestore: {e}")
                traceback.print_exc()
        
        duration = time.time() - state.start_time
        state.total_duration = f"Total time: {int(duration)} seconds"
        state.current_step = "Complete!"

    except Exception as ex:
        traceback.print_exc()
        state.error_message = str(ex)
        state.current_step = "Failed"
    finally:
        state.is_running = False
        yield

def on_clear(e: me.ClickEvent):
    state = me.state(PageState)
    state.input_image_uri = ""
    state.input_image_display_url = ""
    state.eight_bit_display_url = ""
    state.char_sheet_display_url = ""
    state.final_video_display_url = ""
    state.error_message = ""
    state.is_running = False
    state.current_step = ""
    state.total_duration = ""
    yield

# Selfie handlers
def on_open_selfie_dialog(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_selfie_dialog = True
    yield

def on_close_selfie_dialog(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_selfie_dialog = False
    yield

def on_selfie_capture(e: me.WebEvent):
    state = me.state(PageState)
    # Don't close dialog immediately, wait for processing
    
    try:
        data_url = e.value["value"]
        header, encoded = data_url.split(",", 1)
        mime_type = header.split(";")[0].split(":")[1]
        image_data = base64.b64decode(encoded)
        
        gcs_uri = store_to_gcs(
            folder="selfies",
            file_name=f"selfie_{uuid.uuid4()}.png",
            mime_type=mime_type,
            contents=image_data,
        )
        
        state.input_image_uri = gcs_uri
        state.input_image_display_url = create_display_url(gcs_uri)
        state.show_selfie_dialog = False # Close on success
    except Exception as ex:
        traceback.print_exc()
        state.error_message = f"Failed to process selfie: {ex}"
        # Keep dialog open on error so they can try again? Or close it?
        # Let's close it for now to avoid getting stuck.
        state.show_selfie_dialog = False
    yield

@me.page(path="/retro_games", title="Retro Games Workflow")
def page():
    with page_scaffold(page_name="retro_games"):
        retro_games_content()

def retro_games_content():
    state = me.state(PageState)
    config = RetroGameConfig()
    
    # Selfie Dialog
    if state.show_selfie_dialog:
        with dialog(is_open=state.show_selfie_dialog):
             with me.box(style=me.Style(padding=me.Padding.all(16), width="500px", height="600px")): # Added fixed size for dialog content
                me.text("Take a Selfie", type="headline-6")
                # Ensure selfie camera fits
                with me.box(style=me.Style(flex_grow=1, overflow_y="auto")):
                    selfie_camera(on_capture=on_selfie_capture)
                with me.box(style=me.Style(display="flex", justify_content="flex-end", margin=me.Margin(top=16))):
                    me.button("Cancel", on_click=on_close_selfie_dialog, type="flat")

    with page_frame():
        header("Retro Games", "videogame_asset")
        
        # Main Content Container
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=24)):
            
            # Top Section: Two Columns
            with me.box(style=me.Style(display="flex", flex_direction="row", gap=24, flex_wrap="wrap")):
                
                # Left Column: Inputs
                with me.box(style=me.Style(flex_grow=1, flex_basis="400px", min_width="300px")):
                    with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED):
                        me.text("Input Image", type="headline-6")
                        
                        # Image Display
                        if state.input_image_display_url:
                            me.image(src=state.input_image_display_url, style=me.Style(height=200, object_fit="contain", margin=me.Margin(top=16, bottom=16)))
                        else:
                            with me.box(style=me.Style(height=200, width="100%", background=me.theme_var("surface-variant"), border_radius=8, margin=me.Margin(top=16, bottom=16), display="flex", justify_content="center", align_items="center")):
                                me.icon("image", style=me.Style(font_size=48, color=me.theme_var("on-surface-variant")))

                        # Input Controls
                        with me.box(style=me.Style(display="flex", gap=8, flex_wrap="wrap", justify_content="center")):
                            me.uploader(label="Upload", on_upload=on_upload, accepted_file_types=["image/jpeg", "image/png"], type="flat")
                            library_chooser_button(on_library_select=on_library_select, button_type="icon", key="retro_lib")
                            with me.content_button(type="icon", on_click=on_open_selfie_dialog):
                                me.icon("camera_alt")
                            me.button("Clear", on_click=on_clear, type="flat", color="warn")

                    # Theme Selection with Logos
                    with me.box(style=me.Style(
                        # flex_basis="max(480px, calc(50% - 48px))", # Removed to let parent control
                        background=me.theme_var("background"),
                        border_radius=12,
                        box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
                        padding=me.Padding.all(16),
                        display="flex",
                        flex_direction="column",
                        margin=me.Margin(top=24)
                    )):
                        me.text("Theme Selection", type="headline-6")
                        with me.box(style=me.Style(display="flex", gap=16, flex_wrap="wrap", margin=me.Margin(top=16), justify_content="center")):
                            for theme_name in config.get_theme_names():
                                is_selected = state.selected_theme_value == theme_name
                                logo_uri = config.get_theme_logo(theme_name)
                                display_url = create_display_url(logo_uri) if logo_uri else ""
                                
                                with me.box(
                                    key=theme_name,
                                    on_click=on_theme_click,
                                    style=me.Style(
                                        cursor="pointer", 
                                        display="flex", 
                                        flex_direction="column", 
                                        align_items="center", 
                                        gap=8,
                                        padding=me.Padding.all(8),
                                        border=me.Border.all(me.BorderSide(width=3 if is_selected else 1, color=me.theme_var("primary") if is_selected else me.theme_var("outline"))),
                                        border_radius=12,
                                        background=me.theme_var("secondary-container") if is_selected else "transparent"
                                    )
                                ):
                                    if display_url:
                                        me.image(src=display_url, style=me.Style(height=80, width=80, object_fit="contain"))
                                    else:
                                        # Fallback if no logo
                                        with me.box(style=me.Style(height=80, width=80, display="flex", justify_content="center", align_items="center", background="#eee")):
                                            me.text(theme_name[0])
                                            
                                    me.text(theme_name, type="body-1" if is_selected else "body-2", style=me.Style(font_weight="bold" if is_selected else "normal"))
                        
                        with me.box(style=me.Style(margin=me.Margin(top=24), width="100%")):
                             me.button("Generate Retro Game", on_click=on_click_generate, type="raised", style=me.Style(width="100%"), disabled=state.is_running or not state.input_image_uri)

                # Right Column: Status & Intermediate Results
                with me.box(style=me.Style(flex_grow=1, flex_basis="400px", min_width="300px", display="flex", flex_direction="column", gap=24)):
                    if state.error_message:
                        with me.box(style=me.Style(background=me.theme_var("error-container"), color=me.theme_var("on-error-container"), padding=me.Padding.all(16), border_radius=8)):
                            me.text(state.error_message)

                    if state.is_running:
                        with me.box(style=me.Style(display="flex", align_items="center", gap=16)):
                            me.progress_spinner()
                            me.text(state.current_step, type="headline-6")
                    elif state.current_step == "Complete!":
                         with me.box(style=me.Style(display="flex", flex_direction="column")):
                             me.text("Generation Complete!", type="headline-5", style=me.Style(color=me.theme_var("primary")))
                             if state.total_duration:
                                 me.text(state.total_duration, type="body-1")

                    # Intermediate Results Row
                    with me.box(style=me.Style(display="flex", flex_wrap="wrap", gap=24)):
                        # 8-bit Image
                        if state.eight_bit_display_url:
                            with me.box(style=me.Style(
                                background=me.theme_var("background"),
                                border_radius=12,
                                box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
                                padding=me.Padding.all(16),
                                display="flex",
                                flex_direction="column",
                                align_items="center",
                                flex_grow=1,
                                flex_basis="250px", # Slightly smaller basis to fit two side-by-side more easily
                            )):
                                me.text("8-bit Character", type="subtitle-1")
                                me.image(src=state.eight_bit_display_url, style=me.Style(width="100%", aspect_ratio="1/1", border_radius=8, margin=me.Margin(top=8), object_fit="cover"))
                        
                        # Character Sheet
                        if state.char_sheet_display_url:
                            with me.box(style=me.Style(
                                background=me.theme_var("background"),
                                border_radius=12,
                                box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
                                padding=me.Padding.all(16),
                                display="flex",
                                flex_direction="column",
                                align_items="center",
                                flex_grow=1,
                                flex_basis="250px",
                            )):
                                me.text("Character Sheet", type="subtitle-1")
                                me.image(src=state.char_sheet_display_url, style=me.Style(width="100%", aspect_ratio="1/1", border_radius=8, margin=me.Margin(top=8), object_fit="cover"))

            # Bottom Section: Final Video (Full Width)
            if state.final_video_display_url:
                with me.box(style=me.Style(
                    background=me.theme_var("background"),
                    border_radius=12,
                    box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
                    padding=me.Padding.all(16),
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    width="100%", # Ensure full width
                )):
                    me.text("Final Retro Game Video", type="headline-4") # Larger headline
                    me.video(src=state.final_video_display_url, style=me.Style(width="100%", max_width="960px", border_radius=12, margin=me.Margin(top=24))) # Larger max width