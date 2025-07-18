from dataclasses import field
from typing import Callable

import mesop as me

from pages.library import MediaItem, get_media_for_page
from .events import LibrarySelectionChangeEvent


@me.stateclass
class State:
    media_items: list[MediaItem] = field(default_factory=list)  # pylint: disable=invalid-field-call
    is_loading: bool = True


@me.component
def library_image_selector(on_select: Callable[[LibrarySelectionChangeEvent], None]):
    """A component that displays a grid of recent images from the library."""
    state = me.state(State)

    def on_image_click(e: me.ClickEvent):
        """Handles the click event on an image in the grid."""
        print(f"Image Clicked. URI from key: {e.key}")
        yield from on_select(LibrarySelectionChangeEvent(gcs_uri=e.key))

    # This pattern ensures that we only fetch data from Firestore one time,
    # when the component is first loaded. The `is_loading` flag prevents
    # subsequent re-renders from re-fetching the data.
    if state.is_loading:
        state.media_items = get_media_for_page(1, 20, ["images"])
        state.is_loading = False
        # NOTE: There is no `yield` here. This is critical.
        # The function continues to the rendering part of the code in the same pass.

    with me.box(
        style=me.Style(
            display="grid",
            grid_template_columns="repeat(auto-fill, minmax(150px, 1fr))",
            gap="16px",
        )
    ):
        if not state.media_items:
            me.text("No recent images found in the library.")
        else:
            for item in state.media_items:
                image_uri_to_display = ""
                if item.gcs_uris:
                    image_uri_to_display = item.gcs_uris[0]
                elif item.gcsuri:
                    image_uri_to_display = item.gcsuri

                if image_uri_to_display:
                    with me.box(
                        on_click=on_image_click,
                        key=image_uri_to_display,
                        style=me.Style(cursor="pointer"),
                    ):
                        me.image(
                            src=image_uri_to_display.replace(
                                "gs://", "https://storage.mtls.cloud.google.com/"
                            ),
                            style=me.Style(
                                width="100%", border_radius=8, object_fit="cover",
                            ),
                        )