"""Dialog for viewing and editing a PromptTemplate."""

from typing import Callable

import mesop as me

from components.dialog import dialog


@me.stateclass
class DialogState:
    """State for the detail dialog."""

    # To hold the edited values
    label: str = ""
    key: str = ""
    category: str = ""
    prompt: str = ""


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

            def on_update_click(e: me.ClickEvent):
                updates = {
                    "label": state.label,
                    "key": state.key,
                    "category": state.category,
                    "prompt": state.prompt,
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
                        on_input=lambda e: setattr(state, "label", e.value),
                    )
                    me.input(
                        label="Key",
                        value=state.key,
                        on_input=lambda e: setattr(state, "key", e.value),
                    )
                    me.input(
                        label="Category",
                        value=state.category,
                        on_input=lambda e: setattr(state, "category", e.value),
                    )
                    me.textarea(
                        label="Prompt",
                        value=state.prompt,
                        on_input=lambda e: setattr(state, "prompt", e.value),
                        rows=5,
                        autosize=True,
                        style=me.Style(width="100%"),
                    )
                else:
                    _detail_row("Key:", template["key"])
                    _detail_row("Category:", template["category"])
                    _detail_row("Type:", template["template_type"])
                    _detail_row("Attribution:", template["attribution"])
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
