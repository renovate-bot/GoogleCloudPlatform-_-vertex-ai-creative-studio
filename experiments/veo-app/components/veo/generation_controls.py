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

import mesop as me

from state.veo_state import PageState


@me.component
def generation_controls():
    """Video generation controls"""
    state = me.state(PageState)
    with me.box(style=me.Style(display="flex", flex_basis="row", gap=5)):
        me.select(
            label="aspect",
            appearance="outline",
            options=[
                me.SelectOption(label="16:9 widescreen", value="16:9"),
                me.SelectOption(label="9:16 portrait", value="9:16"),
            ],
            value=state.aspect_ratio,
            on_selection_change=on_selection_change_aspect,
            disabled=True if state.veo_model == "3.0" else False,  # 3.0 only does 16:9
        )
        me.select(
            label="length",
            options=[
                me.SelectOption(label="5 seconds", value="5"),
                me.SelectOption(label="6 seconds", value="6"),
                me.SelectOption(label="7 seconds", value="7"),
                me.SelectOption(label="8 seconds", value="8"),
            ],
            appearance="outline",
            style=me.Style(),
            value=f"{state.video_length}",
            on_selection_change=on_selection_change_length,
            disabled=True
            if state.veo_model == "3.0"
            else False,  # 3.0 only does 8 seconds
        )
        me.checkbox(
            label="auto-enhance prompt",
            checked=state.auto_enhance_prompt,
            on_change=on_change_auto_enhance_prompt,
            disabled=True
            if state.veo_model == "3.0"
            else False,  # 3.0 no enhance prompt
        )
        me.select(
            label="model",
            options=[
                me.SelectOption(label="Veo 2.0", value="2.0"),
                me.SelectOption(label="Veo 3.0", value="3.0"),
            ],
            appearance="outline",
            style=me.Style(),
            value=state.veo_model,
            on_selection_change=on_selection_change_model,
        )


def on_selection_change_length(e: me.SelectSelectionChangeEvent):
    """Adjust the video duration length in seconds based on user event"""
    state = me.state(PageState)
    state.video_length = int(e.value)


def on_selection_change_aspect(e: me.SelectSelectionChangeEvent):
    """Adjust aspect ratio based on user event."""
    state = me.state(PageState)
    state.aspect_ratio = e.value


def on_selection_change_model(e: me.SelectSelectionChangeEvent):
    """Adjust model based on user event."""
    state = me.state(PageState)
    state.veo_model = e.value
    # reset to veo 3 settings
    if state.veo_model == "3.0":
        # aspect = 16x9 only
        # length = 8 seconds
        # t2v only
        # no auto enhance
        state.aspect_ratio = "16:9"
        state.video_length = 8
        state.veo_mode = "t2v"
        state.auto_enhance_prompt = False


def on_change_auto_enhance_prompt(e: me.CheckboxChangeEvent):
    """Toggle auto-enhance prompt"""
    state = me.state(PageState)
    state.auto_enhance_prompt = e.checked
