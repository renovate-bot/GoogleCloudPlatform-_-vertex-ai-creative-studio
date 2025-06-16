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
""" Veo mesop ui page"""
import time

import mesop as me

from common.error_handling import GenerationError
from common.metadata import add_video_metadata
from components.dialog import dialog, dialog_actions
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from components.veo.file_uploader import file_uploader
from components.veo.generation_controls import generation_controls
from components.veo.video_display import video_display
from config.default import Default
from config.rewriters import VIDEO_REWRITER
from models.gemini import rewriter
from models.model_setup import VeoModelSetup
from models.veo import generate_video

config = Default()

veo_model = VeoModelSetup.init()


from state.veo_state import PageState


def veo_content(app_state: me.state):
    """Veo Mesop Page"""
    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Veo", "movie")

            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=10,
                    height=250,
                )
            ):
                with me.box(
                    style=me.Style(
                        flex_basis="max(480px, calc(60% - 48px))",
                        display="flex",
                        flex_direction="column",
                        align_items="stretch",
                        justify_content="space-between",
                        gap=10,
                    )
                ):
                    subtle_veo_input()
                    generation_controls()

                file_uploader()

            me.box(style=me.Style(height=50))

            video_display()

    with dialog(is_open=state.show_error_dialog):  # pylint: disable=not-context-manager
        me.text(
            "Generation Error",
            type="headline-6",
            style=me.Style(color=me.theme_var("error")),
        )
        me.text(state.error_message, style=me.Style(margin=me.Margin(top=16)))
        with dialog_actions():  # pylint: disable=not-context-manager
            me.button("Close", on_click=on_close_error_dialog, type="flat")








def on_click_clear(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Clear prompt and video"""
    state = me.state(PageState)
    state.result_video = None
    state.prompt = None
    state.veo_prompt_input = None
    state.original_prompt = None
    state.veo_prompt_textarea_key += 1
    state.video_length = 5
    state.aspect_ratio = "16:9"
    state.is_loading = False
    state.auto_enhance_prompt = False
    state.veo_model = "2.0"
    yield




def on_click_custom_rewriter(e: me.ClickEvent):  # pylint: disable=unused-argument
    """ Veo custom rewriter """
    state = me.state(PageState)
    rewritten_prompt = rewriter(state.veo_prompt_input, VIDEO_REWRITER)
    state.veo_prompt_input = rewritten_prompt
    state.veo_prompt_placeholder = rewritten_prompt
    yield


def on_click_veo(e: me.ClickEvent):
    """Veo generate request handler"""
    state = me.state(PageState)
    state.is_loading = True
    state.show_error_dialog = False
    state.error_message = ""
    state.result_video = ""
    state.timing = ""
    yield

    start_time = time.time()
    gcs_uri = ""

    try:
        gcs_uri = generate_video(state)
        state.result_video = gcs_uri

    except GenerationError as e:
        state.error_message = e.message
        state.show_error_dialog = True
        state.result_video = ""

    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        state.timing = f"Generation time: {round(execution_time)} seconds"

        try:
            add_video_metadata(
                gcs_uri,
                state.veo_prompt_input,
                state.aspect_ratio,
                state.veo_model,
                execution_time,
                state.video_length,
                state.reference_image_gcs,
                state.auto_enhance_prompt,
                error_message=state.error_message,
                comment="veo default generation",
                last_reference_image=state.last_reference_image_gcs,
            )
        except Exception as meta_err:
            print(f"CRITICAL: Failed to store metadata: {meta_err}")
            if not state.show_error_dialog:
                state.error_message = f"Failed to store video metadata: {meta_err}"
                state.show_error_dialog = True

    state.is_loading = False
    yield


def on_blur_veo_prompt(e: me.InputBlurEvent):
    """Veo prompt blur event"""
    me.state(PageState).veo_prompt_input = e.value


@me.component
def subtle_veo_input():
    """veo input"""

    pagestate = me.state(PageState)

    icon_style = me.Style(
        display="flex",
        flex_direction="column",
        gap=3,
        font_size=10,
        align_items="center",
    )
    with me.box(
        style=me.Style(
            border_radius=16,
            padding=me.Padding.all(8),
            background=me.theme_var("secondary-container"),
            display="flex",
            width="100%",
        )
    ):
        with me.box(
            style=me.Style(
                flex_grow=1,
            )
        ):
            me.native_textarea(
                autosize=True,
                min_rows=10,
                max_rows=13,
                placeholder="video creation instructions",
                style=me.Style(
                    padding=me.Padding(top=16, left=16),
                    background=me.theme_var("secondary-container"),
                    outline="none",
                    width="100%",
                    overflow_y="auto",
                    border=me.Border.all(
                        me.BorderSide(style="none"),
                    ),
                    color=me.theme_var("foreground"),
                    flex_grow=1,
                ),
                on_blur=on_blur_veo_prompt,
                key=str(pagestate.veo_prompt_textarea_key),
                value=pagestate.veo_prompt_placeholder,
            )
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
                gap=15,
            )
        ):
            # do the veo
            with me.content_button(
                type="icon",
                on_click=on_click_veo,
            ):
                with me.box(style=icon_style):
                    me.icon("play_arrow")
                    me.text("Create")
            # invoke gemini
            with me.content_button(
                type="icon",
                on_click=on_click_custom_rewriter,
            ):
                with me.box(style=icon_style):
                    me.icon("auto_awesome")
                    me.text("Rewriter")
            # clear all of this
            with me.content_button(
                type="icon",
                on_click=on_click_clear,
            ):
                with me.box(style=icon_style):
                    me.icon("clear")
                    me.text("Clear")



def on_close_error_dialog(e: me.ClickEvent):
    """Handler to close the error dialog."""
    state = me.state(PageState)
    state.show_error_dialog = False
    yield
