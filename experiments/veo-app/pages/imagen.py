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

from components.dialog import dialog, dialog_actions
from components.header import header
from components.imagen.advanced_controls import advanced_controls
from components.imagen.generation_controls import generation_controls
from components.imagen.image_output import image_output
from components.imagen.modifier_controls import modifier_controls
from components.page_scaffold import page_frame, page_scaffold
from state.imagen_state import PageState


def imagen_content(app_state: me.state):
    """Imagen Mesop Page"""
    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Imagen Creative Studio", "image")

            generation_controls()
            modifier_controls()
            advanced_controls()
            image_output()

    with dialog(is_open=state.show_dialog):  # pylint: disable=not-context-manager
        me.text(
            "Generation Error",
            type="headline-6",
            style=me.Style(color=me.theme_var("error")),
        )
        me.text(state.dialog_message, style=me.Style(margin=me.Margin(top=16)))
        with dialog_actions(): # pylint: disable=not-context-manager
            me.button("Close", on_click=on_close_dialog, type="flat")


def on_close_dialog(e: me.ClickEvent):
    """Handler to close the dialog."""
    state = me.state(PageState)
    state.show_dialog = False
    yield