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

from typing import Callable, Optional

import mesop as me

from components.dialog import dialog
from components.library.library_image_selector import library_image_selector


@me.stateclass
class State:
    show_library_dialog: bool = False


@me.component
def library_chooser_button(
    on_library_select: Callable[[str], None],
    button_label: Optional[str] = None,
):
    """Renders a button that opens a dialog to select an image from the library."""
    state = me.state(State)

    def on_select_from_library(uri: str):
        """Callback to handle image selection from the library dialog."""
        # This is a generator function passed from the parent page.
        # We must `yield from` it to ensure the parent's state update
        # and re-render is correctly triggered.
        yield from on_library_select(uri)

        # Now, update this component's local state to close the dialog.
        state.show_library_dialog = False
        yield

    with me.content_button(
        on_click=lambda e: setattr(state, "show_library_dialog", True), type="stroked"
    ):
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=8, align_items="center"
            )
        ):
            me.icon("photo_library")
            if button_label:
                me.text(button_label)

    # Define a style for the dialog to make it large
    dialog_style = me.Style(
        width="80vw",
        height="80vh",
        display="flex",
        flex_direction="column",
    )

    with dialog(is_open=state.show_library_dialog, dialog_style=dialog_style):  # pylint: disable=not-context-manager
        with me.box(
            style=me.Style(display="flex", flex_direction="column", gap=16, flex_grow=1)
        ):
            me.text("Select an Image from Library", type="headline-6")
            # The library_image_selector needs to be in a flexible box to allow it to scroll
            with me.box(style=me.Style(flex_grow=1, overflow_y="auto")):
                library_image_selector(on_select=on_select_from_library)
            with me.box(
                style=me.Style(
                    display="flex", justify_content="flex-end", margin=me.Margin(top=24)
                )
            ):
                me.button(
                    "Cancel",
                    on_click=lambda e: setattr(state, "show_library_dialog", False),
                    type="stroked",
                )
