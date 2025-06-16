import mesop as me

from common.metadata import MediaItem


@me.stateclass
class CarouselState:
    current_index: int = 0


def on_next(e: me.ClickEvent):
    state = me.state(CarouselState)
    state.current_index += 1


def on_prev(e: me.ClickEvent):
    state = me.state(CarouselState)
    state.current_index -= 1


@me.component
def image_details(item: MediaItem):
    """Image details component"""
    state = me.state(CarouselState)
    num_images = len(item.gcs_uris)

    with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center", gap=16)):
        # Image display
        me.image(
            src=item.gcs_uris[state.current_index].replace(
                "gs://", "https://storage.mtls.cloud.google.com/"
            ),
            style=me.Style(
                width="100%",
                height="auto",
                border_radius="8px",
            ),
        )

        # Carousel controls
        with me.box(style=me.Style(display="flex", align_items="center", justify_content="center", gap=16)):
            me.button(
                "Back",
                on_click=on_prev,
                disabled=state.current_index == 0,
            )
            me.text(f"{state.current_index + 1} / {num_images}")
            me.button(
                "Next",
                on_click=on_next,
                disabled=state.current_index >= num_images - 1,
            )
    
    if item.rewritten_prompt:
        me.text(f'Rewritten Prompt: "{item.rewritten_prompt}"')
    else:
        me.text(f"Prompt: \"{item.prompt or 'N/A'}\"")
    if item.critique:
        me.text(f"Critique: {item.critique}")