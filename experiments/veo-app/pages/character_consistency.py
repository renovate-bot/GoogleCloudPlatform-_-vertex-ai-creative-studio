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

from dataclasses import field

import mesop as me

from common.metadata import get_media_item_by_id
from common.storage import store_to_gcs
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from models.character_consistency import generate_character_video
from state.character_consistency_state import CharacterConsistencyState
from state.state import AppState
from config.default import ABOUT_PAGE_CONTENT
from components.dialog import dialog


@me.stateclass
class PageState:
    """Character Consistency Page State"""

    uploaded_image_gcs_uris: list[str] = field(default_factory=list)  # pylint: disable=invalid-field-call
    scene_prompt: str = ""
    candidate_image_urls: list[str] = field(default_factory=list) # pylint: disable=invalid-field-call
    best_image_url: str = ""
    outpainted_image_url: str = ""
    final_video_url: str = ""
    status_message: str = "Ready."
    is_generating: bool = False
    total_generation_time: float = 0.0

    info_dialog_open: bool = False


def character_consistency_page_content():
    """UI for the Character Consistency page."""
    state = me.state(PageState)

    if state.info_dialog_open:
        with dialog(is_open=state.info_dialog_open):  # pylint: disable=not-context-manager
            me.text("About Character Consistency", type="headline-6")
            me.markdown(ABOUT_PAGE_CONTENT["sections"][6]["description"])
            me.divider()
            me.text("Current Settings", type="headline-6")
            me.text(f"Scene Prompt: {state.scene_prompt}")
            with me.box(style=me.Style(margin=me.Margin(top=16))):
                me.button("Close", on_click=close_info_dialog, type="flat")

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Character Consistency", "person", show_info_button=True, on_info_click=open_info_dialog)

            with me.box(style=me.Style(margin=me.Margin.symmetric(vertical=20))):
                me.uploader(
                    label="Upload Reference Images",
                    on_upload=on_upload,
                    multiple=True,
                    style=me.Style(width="100%"),
                )

            if state.uploaded_image_gcs_uris:
                with me.box(style=me.Style(display="flex", flex_wrap="wrap", gap=10, justify_content="center")):
                    for uri in state.uploaded_image_gcs_uris:
                        me.image(
                            src=uri.replace(
                                "gs://", "https://storage.mtls.cloud.google.com/"
                            ),
                            style=me.Style(width=200, height=200, object_fit="contain", border_radius="12px",
                                box_shadow="0 2px 4px rgba(0,0,0,0.1)"),
                        )

            me.textarea(
                label="Scene Prompt",
                rows=3,
                on_input=on_prompt_input,
                style=me.Style(width="100%"),
            )

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=16, justify_content="center")):
                me.button(
                    "Generate",
                    on_click=on_generate_click,
                    disabled=state.is_generating,
                    type="flat",
                )
                me.button(
                    "Clear",
                    on_click=on_clear,
                    disabled=state.is_generating,
                    type="stroked",
                )

            me.text(
                state.status_message,
                style=me.Style(margin=me.Margin.symmetric(vertical=10)),
            )

            if state.total_generation_time > 0:
                me.text(f"Total generation time: {state.total_generation_time:.2f} seconds")

            if state.candidate_image_urls:
                me.text("Candidate Images", type="headline-5")
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_wrap="wrap",
                        gap=10,
                        justify_content="center",
                    )
                ):
                    for url in state.candidate_image_urls:
                        me.image(
                            src=url,
                            style=me.Style(
                                width=200,
                                height=200,
                                border_radius="12px",
                                box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                            ),
                        )

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=16, justify_content="center")):
                if state.best_image_url:
                    with me.box(style=me.Style(display="flex", flex_direction="column", gap=4, justify_content="center")):
                        me.text("Best Image", type="headline-5")
                        me.image(
                            src=state.best_image_url,
                            style=me.Style(width=400, height=400, object_fit="contain", border_radius="12px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",),
                        )

                if state.outpainted_image_url:
                    with me.box(style=me.Style(display="flex", flex_direction="column", gap=4, justify_content="center")):
                        me.text("Outpainted Image", type="headline-5")
                        me.image(
                            src=state.outpainted_image_url,
                            style=me.Style(width=600, height=338, object_fit="contain", border_radius="12px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",),
                        )

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=16, justify_content="center")):
                if state.final_video_url:
                    with me.box(style=me.Style(display="flex", flex_direction="column", gap=12, justify_content="center")):
                        me.text("Final Video", type="headline-5")
                        me.video(
                            src=state.final_video_url, style=me.Style(width=600, height=338)
                        )

def on_upload(e: me.UploadEvent):
    """Handle image uploads."""
    state = me.state(PageState)
    for file in e.files:
        gcs_url = store_to_gcs(
            "character_consistency_references",
            file.name,
            file.mime_type,
            file.getvalue(),
        )
        state.uploaded_image_gcs_uris.append(gcs_url)
    yield


def on_prompt_input(e: me.InputEvent):
    """Handle prompt input."""
    state = me.state(PageState)
    state.scene_prompt = e.value

def on_generate_click(e: me.ClickEvent):
    """Handle generate button click."""
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_generating = True
    state.total_generation_time = 0.0
    state.candidate_image_urls = []
    state.best_image_url = ""
    state.outpainted_image_url = ""
    state.final_video_url = ""
    yield

    try:
        for step_result in generate_character_video(
            user_email=app_state.user_email,
            reference_image_gcs_uris=state.uploaded_image_gcs_uris,
            scene_prompt=state.scene_prompt,
        ):
            state.status_message = step_result.message
            state.total_generation_time += step_result.duration_seconds
            if step_result.data:
                if "candidate_image_gcs_uris" in step_result.data:
                    state.candidate_image_urls = [
                        uri.replace("gs://", "https://storage.mtls.cloud.google.com/")
                        for uri in step_result.data["candidate_image_gcs_uris"]
                    ]
                if "best_image_gcs_uri" in step_result.data:
                    state.best_image_url = step_result.data["best_image_gcs_uri"].replace("gs://", "https://storage.mtls.cloud.google.com/")
                if "outpainted_image_gcs_uri" in step_result.data:
                    state.outpainted_image_url = step_result.data["outpainted_image_gcs_uri"].replace("gs://", "https://storage.mtls.cloud.google.com/")
                if "video_gcs_uri" in step_result.data:
                    state.final_video_url = step_result.data["video_gcs_uri"].replace("gs://", "https://storage.mtls.cloud.google.com/")
            yield

        state.status_message = f"Workflow complete! Total time: {state.total_generation_time:.2f} seconds"

    except Exception as e:
        state.status_message = f"Error: {e}"

    state.is_generating = False
    yield

def on_clear(e: me.ClickEvent):
    """Clear the state of the page."""
    state = me.state(PageState)
    state.uploaded_image_gcs_uris = []
    state.scene_prompt = ""
    state.candidate_image_urls = []
    state.best_image_url = ""
    state.outpainted_image_url = ""
    state.final_video_url = ""
    state.status_message = "Ready."
    state.is_generating = False
    state.total_generation_time = 0.0
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
