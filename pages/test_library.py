# Copyright 2024 Google LLC
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
"""A test library page using the new media_tile component."""

import json
from dataclasses import dataclass, field
from typing import List, Optional

import mesop as me

from common.metadata import MediaItem, get_media_for_page
from common.utils import gcs_uri_to_https_url
from components.dialog import dialog
from components.header import header
from components.library.audio_details import audio_details
from components.library.character_consistency_details import \
    character_consistency_details
from components.library.image_details import CarouselState, image_details
from components.library.video_details import video_details
from components.media_tile.media_tile import media_tile, get_pills_for_item
from components.page_scaffold import page_frame, page_scaffold
from components.library import grid_parts


@me.page(path="/test_library", title="GenMedia Creative Studio - Test Library")
def page():
    """Main Page."""
    with page_scaffold(page_name="library"):
        library_content()


@me.stateclass
@dataclass
class PageState:
    """State for the test library page."""

    is_loading: bool = True
    media_items: List[MediaItem] = field(default_factory=list)
    show_details_dialog: bool = False
    selected_media_item_id: Optional[str] = None
    dialog_instance_key: int = 0
    dialog_selected_video_url: str = ""
    initial_load_complete: bool = False


def library_content():
    """The main content of the library page."""
    pagestate = me.state(PageState)

    if not pagestate.initial_load_complete:
        pagestate.media_items = get_media_for_page(
            page=1, media_per_page=50, sort_by_timestamp=True
        )
        pagestate.is_loading = False
        pagestate.initial_load_complete = True

    with page_frame():
        header("Test Library", "science")

        with me.box(
            style=me.Style(
                display="grid",
                grid_template_columns="repeat(auto-fill, minmax(300px, 1fr))",
                gap="16px",
                width="100%",
            )
        ):
            if pagestate.is_loading:
                with me.box(
                    style=me.Style(
                        display="flex",
                        justify_content="center",
                        padding=me.Padding.all(20),
                    )
                ):
                    me.progress_spinner()
            elif not pagestate.media_items:
                with me.box(
                    style=me.Style(padding=me.Padding.all(20), text_align="center")
                ):
                    me.text("No media items found.")
            else:
                for item in pagestate.media_items:
                    gcs_uri = (
                        item.gcsuri
                        if item.gcsuri
                        else (item.gcs_uris[0] if item.gcs_uris else None)
                    )
                    https_url = gcs_uri_to_https_url(gcs_uri) if gcs_uri else ""
                    media_tile(
                        key=item.id,
                        on_click=on_media_item_click,
                        media_type=item.media_type,
                        https_url=https_url,
                        pills_json=get_pills_for_item(item, https_url),
                    )

        library_dialog(pagestate)


def on_media_item_click(e: me.ClickEvent):
    pagestate = me.state(PageState)
    item_id = e.key
    item = next((i for i in pagestate.media_items if i.id == item_id), None)
    if not item:
        return

    pagestate.selected_media_item_id = item.id
    if item.gcs_uris:
        pagestate.dialog_selected_video_url = item.gcs_uris[0]
    elif item.gcsuri:
        pagestate.dialog_selected_video_url = item.gcsuri
    else:
        pagestate.dialog_selected_video_url = ""
    pagestate.show_details_dialog = True
    pagestate.dialog_instance_key += 1
    yield

def on_close_details_dialog(e: me.ClickEvent):
    pagestate = me.state(PageState)
    carousel_state = me.state(CarouselState)
    pagestate.show_details_dialog = False
    pagestate.selected_media_item_id = None
    pagestate.dialog_selected_video_url = ""
    carousel_state.current_index = 0
    yield

def on_dialog_thumbnail_click(e: me.ClickEvent):
    pagestate = me.state(PageState)
    pagestate.dialog_selected_video_url = e.key
    yield

def on_click_set_permalink(e: me.ClickEvent):
    if e.key:
        me.query_params["media_id"] = e.key


@me.component
def library_dialog(pagestate: PageState):
    with dialog(
        key=str(pagestate.dialog_instance_key),
        is_open=pagestate.show_details_dialog,
        dialog_style=me.Style(max_width="80vw", width="80vw", min_width="600px"),
    ):
        item_to_display = None
        if pagestate.selected_media_item_id:
            item_to_display = next(
                (
                    v
                    for v in pagestate.media_items
                    if v.id == pagestate.selected_media_item_id
                ),
                None,
            )

        if item_to_display:
            item = item_to_display
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    gap=12,
                    width="100%",
                    max_height="80vh",
                    overflow_y="auto",
                    padding=me.Padding.all(24),
                )
            ):
                me.text(
                    "Media Details",
                    style=me.Style(
                        font_size="1.5rem",
                        font_weight="bold",
                        margin=me.Margin(bottom=16),
                        color=me.theme_var("on-surface-variant"),
                        flex_shrink=0,
                    ),
                )
                if item.media_type == "video":
                    video_details(
                        item=item,
                        on_click_permalink=on_click_set_permalink,
                        selected_url=pagestate.dialog_selected_video_url,
                        on_thumbnail_click=on_dialog_thumbnail_click,
                    )
                elif item.media_type == "image":
                    image_details(item, on_click_permalink=on_click_set_permalink)
                elif item.media_type == "audio":
                    audio_details(item=item, on_click_permalink=on_click_set_permalink)
                elif item.media_type == "character_consistency":
                    character_consistency_details(
                        item=item, on_click_permalink=on_click_set_permalink
                    )
                else:
                    me.text("Details for this media type are not yet implemented.")

                if item.raw_data:
                    with me.expansion_panel(
                        key="raw_metadata_panel_dialog",
                        title="Firestore Metadata",
                        description=item.id or "N/A",
                        icon="dataset",
                    ):
                        try:
                            json_string = json.dumps(
                                item.raw_data, indent=2, default=str
                            )
                            me.markdown(f"```json\n{json_string}\n```")
                        except Exception:
                            me.text("Could not display raw data (serialization error).")
                else:
                    me.text("Raw Firestore data not available.")
        else:
            with me.box(style=me.Style(padding=me.Padding.all(16))):
                me.text("No media item selected or found for the given ID.")

        me.button(
            "Close",
            on_click=on_close_details_dialog,
            type="flat",
            style=me.Style(margin=me.Margin(top=24)),
        )
