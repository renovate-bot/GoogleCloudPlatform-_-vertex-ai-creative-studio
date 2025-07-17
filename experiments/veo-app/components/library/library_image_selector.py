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
from typing import Callable

import mesop as me

from pages.library import MediaItem, get_media_for_page


@me.stateclass
class State:
    media_items: list[MediaItem] = field(default_factory=list)  # pylint: disable=invalid-field-call
    is_loading: bool = True


def on_image_click(e: me.ClickEvent, on_select: Callable[[str], None]):
    """Handles the click event on an image in the grid."""
    # Log the URI received from the click event's key.
    print(f"Image Clicked. URI from key: {e.key}")
    # We must `yield from` the on_select callback, because it is a generator.
    # This ensures the parent's event handler is fully executed.
    yield from on_select(e.key)


@me.component
def library_image_selector(on_select: Callable[[str], None]):
    """A component that displays a grid of recent images from the library."""
    state = me.state(State)

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
                        on_click=lambda e: on_image_click(e, on_select),
                        key=image_uri_to_display,
                        style=me.Style(cursor="pointer"),
                    ):
                        me.image(
                            src=image_uri_to_display.replace(
                                "gs://", "https://storage.mtls.cloud.google.com/"
                            ),
                            style=me.Style(
                                width="100%",
                                border_radius=8,
                                object_fit="cover",
                            ),
                        )
