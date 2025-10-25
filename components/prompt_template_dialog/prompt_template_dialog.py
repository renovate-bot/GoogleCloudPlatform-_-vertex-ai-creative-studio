"""A reusable dialog component for saving a new prompt template."""

from typing import Callable

import mesop as me

from components.dialog import dialog


@me.stateclass
class DialogState:
    label: str = ""
    key: str = ""
    category: str = ""
    key_manually_edited: bool = False


@me.component
def prompt_template_dialog(
    is_open: bool,
    prompt_text: str,
    on_save: Callable,
    on_close: Callable,
):
    """A dialog for saving a new prompt template."""
    state = me.state(DialogState)

    def on_save_click(e: me.ClickEvent):
        # Pass the state back to the parent page's handler and execute it
        yield from on_save(state.label, state.key, state.category)
        # Clear state for next time
        state.label = ""
        state.key = ""
        state.category = ""
        state.key_manually_edited = False

    def on_cancel_click(e: me.ClickEvent):
        # Clear state for next time
        state.label = ""
        state.key = ""
        state.category = ""
        state.key_manually_edited = False
        # Call the parent's on_close handler
        on_close(e)

    def on_label_input(e: me.InputEvent):
        state.label = e.value
        if not state.key_manually_edited:
            state.key = e.value.lower().replace(" ", "-")

    def on_key_input(e: me.InputEvent):
        state.key = e.value
        state.key_manually_edited = True

    def on_category_input(e: me.InputEvent):
        state.category = e.value

    with dialog(
        is_open=is_open,
    ):
        with me.box(
            style=me.Style(
                padding=me.Padding.all(24), display="flex", flex_direction="column", gap=16
            )
        ):
            me.text("Save as Prompt Template", type="headline-5")

            me.text("Prompt:")
            me.text(
                prompt_text,
                style=me.Style(
                    font_style="italic", max_height="150px", overflow_y="auto"
                ),
            )

            me.input(label="Label", on_input=on_label_input, value=state.label)
            me.input(
                label="Key",
                on_input=on_key_input,
                value=state.key,
                placeholder="A unique identifier, e.g., my-awesome-template",
            )
            me.input(
                label="Category",
                on_input=on_category_input,
                value=state.category,
                placeholder="e.g., Creative, Editing",
            )

            with me.box(
                style=me.Style(
                    display="flex", justify_content="flex-end", gap=8, margin=me.Margin(top=24)
                )
            ):
                me.button("Cancel", on_click=on_cancel_click)
                me.button(
                    "Save",
                    type="raised",
                    on_click=on_save_click,
                    disabled=not (state.label and state.key and state.category),
                )
