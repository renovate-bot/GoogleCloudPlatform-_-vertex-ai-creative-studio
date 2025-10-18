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

from typing import Callable, List

import mesop as me

from common.metadata import MediaItem
from components.library.events import LibrarySelectionChangeEvent


@me.component
def library_image_selector(
    on_select: Callable[[LibrarySelectionChangeEvent], None],
    media_items: List[MediaItem],
):
    """A component that displays a grid of recent images from the library."""

    def on_image_click(e: me.ClickEvent):
        """Handles the click event on an image in the grid."""
        print(f"Image Clicked. URI from key: {e.key}")
        yield from on_select(LibrarySelectionChangeEvent(gcs_uri=e.key))

    with me.box(
        style=me.Style(
            display="grid",
            grid_template_columns="repeat(auto-fill, minmax(150px, 1fr))",
            gap="16px",
        )
    ):
        if not media_items:
            me.text("No recent images found in the library.")
        else:
            for item in media_items:
                # The signed_url attribute is now added by the parent component.
                image_url = item.signed_url if hasattr(item, "signed_url") else ""
                gcs_uri = item.gcsuri or (item.gcs_uris[0] if item.gcs_uris else None)

                if gcs_uri:
                    with me.box(
                        on_click=on_image_click,
                        key=gcs_uri, # The key should be the permanent GCS URI
                        style=me.Style(cursor="pointer"),
                    ):
                        me.image(
                            src=image_url,
                            style=me.Style(
                                width="100%",
                                border_radius=8,
                                object_fit="cover",
                            ),
                        )