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

"""Dialog for viewing and editing a PromptTemplate."""

from typing import Callable

import mesop as me

from components.dialog import dialog
from common.utils import create_display_url


@me.stateclass
class DialogState:
    """State for the detail dialog."""

    # To hold the edited values
    label: str = ""
    key: str = ""
    category: str = ""
    prompt: str = ""
    template_type: str = ""


@me.component
def prompt_template_detail_dialog(
    template: dict | None,
    is_open: bool,
    is_editable: bool,
    on_close: Callable,
    on_update: Callable,
):
    """A dialog for viewing and potentially editing a prompt template."""
    state = me.state(DialogState)

    with dialog(is_open=is_open): # pylint: disable=E1129:not-context-manager
        if template:
            # Sync state when dialog opens or template changes
            if state.key != template["key"]:
                state.label = template["label"]
                state.key = template["key"]
                state.category = template["category"]
                state.prompt = template["prompt"]
                state.template_type = template["template_type"]

            def on_update_click(e: me.ClickEvent):
                updates = {
                    "label": state.label,
                    "key": state.key,
                    "category": state.category,
                    "prompt": state.prompt,
                    "template_type": state.template_type,
                }
                yield from on_update(template["id"], updates)

            with me.box(
                style=me.Style(
                    padding=me.Padding.all(24),
                    display="flex",
                    flex_direction="column",
                    gap=16,
                )
            ):
                me.text(f"Template: {template['label']}", type="headline-5")

                # Display fields (editable or read-only)
                if is_editable:
                    me.input(
                        label="Label",
                        value=state.label,
                        on_blur=lambda e: setattr(state, "label", e.value),
                    )
                    me.input(
                        label="Key",
                        value=state.key,
                        on_blur=lambda e: setattr(state, "key", e.value),
                    )
                    me.input(
                        label="Category",
                        value=state.category,
                        on_blur=lambda e: setattr(state, "category", e.value),
                    )
                    me.input(
                        label="Type",
                        value=state.template_type,
                        on_blur=lambda e: setattr(state, "template_type", e.value),
                    )
                    me.textarea(
                        label="Prompt",
                        value=state.prompt,
                        on_blur=lambda e: setattr(state, "prompt", e.value),
                        rows=5,
                        autosize=True,
                        style=me.Style(width="100%"),
                    )
                else:
                    _detail_row("Key:", template["key"])
                    _detail_row("Category:", template["category"])
                    _detail_row("Type:", template["template_type"])
                    _detail_row("Attribution:", template["attribution"])
                    if template.get("created_at"):
                        _detail_row("Created:", str(template["created_at"]))
                    if template.get("updated_at"):
                        _detail_row("Last Edited:", str(template["updated_at"]))
                    me.text(
                        "Prompt:",
                        style=me.Style(font_weight="bold", margin=me.Margin(top=16)),
                    )
                    with me.box(
                        style=me.Style(
                            background=me.theme_var("surface-container"),
                            padding=me.Padding.all(16),
                            border_radius=8,
                            max_height="300px",
                            overflow_y="auto",
                        )
                    ):
                        me.text(template["prompt"])

            # Display references if they exist
            if template.get("references"):
                me.text(
                    "References:",
                    style=me.Style(font_weight="bold", margin=me.Margin(top=16)),
                )
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="row", gap=8, flex_wrap="wrap"
                    )
                ):
                    for ref_uri in template["references"]:
                        me.image(
                            src=create_display_url(ref_uri),
                            style=me.Style(
                                width=100, height=100, border_radius=8, object_fit="cover"
                            ),
                        )

            with me.box(
                style=me.Style(
                    display="flex",
                        justify_content="flex-end",
                        gap=8,
                        margin=me.Margin(top=24),
                    )
                ):
                    me.button("Close", on_click=on_close, type="stroked")
                    if is_editable:
                        me.button(
                            "Save Changes", on_click=on_update_click, type="raised"
                        )


@me.component
def _detail_row(label: str, value: str):
    with me.box(style=me.Style(display="flex", flex_direction="row", gap=8)):
        me.text(label, style=me.Style(font_weight="bold"))
        me.text(value)
