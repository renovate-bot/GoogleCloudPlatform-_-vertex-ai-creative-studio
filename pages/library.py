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
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Optional

import mesop as me

from common.metadata import MediaItem, get_media_for_page, get_media_item_by_id
from common.utils import gcs_uri_to_https_url
from components.header import header
from components.lightbox_dialog.lightbox_dialog import lightbox_dialog
from components.library.image_details import CarouselState
from components.media_detail_viewer.media_detail_viewer import media_detail_viewer
from components.media_tile.media_tile import media_tile, get_pills_for_item
from components.page_scaffold import page_frame, page_scaffold
from components.scroll_sentinel.scroll_sentinel import scroll_sentinel
from state.state import AppState


@me.stateclass
@dataclass
class PageState:
    """State for the library page."""

    is_loading: bool = True
    media_items: List[MediaItem] = field(default_factory=list)
    show_details_dialog: bool = False
    selected_media_item_id: Optional[str] = None
    initial_load_complete: bool = False
    current_page: int = 1
    all_items_loaded: bool = False
    user_filter: str = "mine"  # "all" or "mine"
    type_filters: list[str] = field(default_factory=lambda: ["all"]) # "all", "images", "videos", "audio"
    error_filter: str = "all" # "all", "no_errors", "only_errors"


def on_load(e: me.LoadEvent):
    """Handles page load events for permalinks and initial data fetch."""
    pagestate = me.state(PageState)
    if not pagestate.initial_load_complete:
        yield from _load_media(pagestate, is_filter_change=True)
        pagestate.initial_load_complete = True

        media_id = me.query_params.get("media_id")
        if media_id:
            item = next((i for i in pagestate.media_items if i.id == media_id), None)
            if not item:
                item = get_media_item_by_id(media_id)
                if item:
                    pagestate.media_items.insert(0, item)
            
            if item:
                pagestate.selected_media_item_id = media_id
                pagestate.show_details_dialog = True
    yield


def _load_media(pagestate: PageState, is_filter_change: bool = False):
    """Central function to load media based on current filters and pagination."""
    app_state = me.state(AppState)
    user_email_to_filter = app_state.user_email if pagestate.user_filter == "mine" else None

    if is_filter_change:
        pagestate.current_page = 1
        pagestate.media_items = []
        pagestate.all_items_loaded = False

    pagestate.is_loading = True
    yield

    new_items = get_media_for_page(
        page=pagestate.current_page,
        media_per_page=20,
        sort_by_timestamp=True,
        type_filters=pagestate.type_filters,
        filter_by_user_email=user_email_to_filter,
        error_filter=pagestate.error_filter,
    )

    if not new_items:
        pagestate.all_items_loaded = True
    else:
        if is_filter_change:
            pagestate.media_items = new_items
        else:
            pagestate.media_items.extend(new_items)

    pagestate.is_loading = False
    yield


def on_load_more(e: me.WebEvent):
    """Event handler for infinite scroll, fetches the next page of items."""
    pagestate = me.state(PageState)
    if pagestate.is_loading or pagestate.all_items_loaded:
        return

    pagestate.current_page += 1
    yield from _load_media(pagestate)


def on_user_filter_change(e: me.ButtonToggleChangeEvent):
    """Handles changes to the user filter."""
    pagestate = me.state(PageState)
    pagestate.user_filter = e.value
    yield from _load_media(pagestate, is_filter_change=True)


def on_type_filter_change(e: me.ButtonToggleChangeEvent):
    """Handles changes to the media type filter."""
    pagestate = me.state(PageState)
    new_filters = e.values
    if not new_filters:
        pagestate.type_filters = ["all"]
    elif "all" in new_filters and len(new_filters) > 1:
        pagestate.type_filters = [val for val in new_filters if val != "all"]
    else:
        pagestate.type_filters = new_filters
    yield from _load_media(pagestate, is_filter_change=True)


def on_error_filter_change(e: me.ButtonToggleChangeEvent):
    """Handles changes to the error filter."""
    pagestate = me.state(PageState)
    pagestate.error_filter = e.value
    yield from _load_media(pagestate, is_filter_change=True)


@me.page(
    path="/library",
    title="GenMedia Creative Studio - Library",
    on_load=on_load,
)
def page():
    """Main Page."""
    with page_scaffold(page_name="library"):
        library_content()


def library_content():
    """The main content of the library page."""
    pagestate = me.state(PageState)

    with page_frame():
        header("Library", "perm_media")

        with me.box(style=me.Style(display="flex", flex_direction="row", gap=10, margin=me.Margin(bottom=20))):
            me.button_toggle(
                value=pagestate.type_filters,
                buttons=[
                    me.ButtonToggleButton(label="All Types", value="all"),
                    me.ButtonToggleButton(label="Images", value="images"),
                    me.ButtonToggleButton(label="Videos", value="videos"),
                    me.ButtonToggleButton(label="Audio", value="audio"),
                ],
                multiple=True,
                on_change=on_type_filter_change,
            )
            me.button_toggle(
                value=pagestate.user_filter,
                buttons=[
                    me.ButtonToggleButton(label="All Users", value="all"),
                    me.ButtonToggleButton(label="Mine Only", value="mine"),
                ],
                on_change=on_user_filter_change,
            )
            me.button_toggle(
                value=pagestate.error_filter,
                buttons=[
                    me.ButtonToggleButton(label="Show All", value="all"),
                    me.ButtonToggleButton(label="No Errors", value="no_errors"),
                    me.ButtonToggleButton(label="Only Errors", value="only_errors"),
                ],
                on_change=on_error_filter_change,
            )

        with me.box(
            style=me.Style(
                display="grid",
                grid_template_columns="repeat(auto-fill, minmax(300px, 1fr))",
                gap="16px",
                width="100%",
            )
        ):
            if not pagestate.media_items and not pagestate.is_loading:
                with me.box(
                    style=me.Style(padding=me.Padding.all(20), text_align="center")
                ):
                    me.text("No media items found for the selected filters.")
            else:
                for item in pagestate.media_items:
                    gcs_uri = (
                        item.gcsuri
                        if item.gcsuri
                        else (item.gcs_uris[0] if item.gcs_uris else None)
                    )
                    https_url = gcs_uri_to_https_url(gcs_uri) if gcs_uri else ""
                    
                    render_type = item.media_type
                    if item.media_type == "character_consistency":
                        render_type = "video"
                    elif not render_type and https_url:
                        if ".mp4" in https_url or ".webm" in https_url:
                            render_type = "video"
                        elif ".wav" in https_url or ".mp3" in https_url:
                            render_type = "audio"
                        else:
                            render_type = "image"

                    media_tile(
                        key=item.id,
                        on_click=on_media_item_click,
                        media_type=render_type,
                        https_url=https_url,
                        pills_json=get_pills_for_item(item, https_url),
                    )
        
        scroll_sentinel(
            on_visible=on_load_more,
            is_loading=pagestate.is_loading,
            all_items_loaded=pagestate.all_items_loaded,
        )

        library_dialog(pagestate)


def on_media_item_click(e: me.ClickEvent):
    pagestate = me.state(PageState)
    item_id = e.key
    item = next((i for i in pagestate.media_items if i.id == item_id), None)
    if not item:
        return

    pagestate.selected_media_item_id = item.id
    pagestate.show_details_dialog = True
    yield


def on_close_details_dialog(e: me.ClickEvent):
    pagestate = me.state(PageState)
    carousel_state = me.state(CarouselState)
    pagestate.show_details_dialog = False
    pagestate.selected_media_item_id = None
    carousel_state.current_index = 0
    yield


def handle_edit_click(e: me.ClickEvent):
    pagestate = me.state(PageState)
    item = next(
        (i for i in pagestate.media_items if i.id == pagestate.selected_media_item_id),
        None,
    )
    if item:
        gcs_uri = item.gcs_uris[0] if item.gcs_uris else item.gcsuri
        me.navigate("/gemini_image_generation", query_params={"image_uri": gcs_uri})


def handle_veo_click(e: me.ClickEvent):
    pagestate = me.state(PageState)
    item = next(
        (i for i in pagestate.media_items if i.id == pagestate.selected_media_item_id),
        None,
    )
    if item:
        gcs_uri = item.gcs_uris[0] if item.gcs_uris else item.gcsuri
        me.navigate("/veo", query_params={"image_uri": gcs_uri})


@me.component
def library_dialog(pagestate: PageState):
    with lightbox_dialog(
        is_open=pagestate.show_details_dialog, on_close=on_close_details_dialog
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

            # Prepare data for the detail viewer component
            primary_urls = []
            if item.gcs_uris:
                primary_urls = [gcs_uri_to_https_url(uri) for uri in item.gcs_uris]
            elif item.gcsuri:
                primary_urls.append(gcs_uri_to_https_url(item.gcsuri))
            primary_urls_json = json.dumps(primary_urls)

            source_urls = []
            if item.reference_image:
                source_urls.append(gcs_uri_to_https_url(item.reference_image))
            if item.last_reference_image:
                source_urls.append(gcs_uri_to_https_url(item.last_reference_image))
            if item.raw_data and item.raw_data.get("source_images_gcs"):
                for uri in item.raw_data["source_images_gcs"]:
                    source_urls.append(gcs_uri_to_https_url(uri))
            source_urls_json = json.dumps(source_urls)

            metadata_dict = {
                "Prompt": getattr(item, "prompt", None),
                "Model": item.raw_data.get("model") if item.raw_data else None,
                "Timestamp": getattr(item, "timestamp", None),
                "User": getattr(item, "user_email", None),
                "Generation Time (s)": getattr(item, "generation_time", None),
                "Aspect Ratio": getattr(item, "aspect", None),
                "Duration (s)": getattr(item, "duration", None),
            }
            # Filter out keys where the value is None
            filtered_metadata = {
                k: v for k, v in metadata_dict.items() if v is not None
            }
            metadata_json = json.dumps(filtered_metadata, default=str)

            raw_metadata_json = json.dumps(item.raw_data, indent=2, default=str) if item.raw_data else "{}"

            # Determine the render type for the detail view
            render_type = item.media_type
            if item.media_type == "character_consistency":
                render_type = "video"
            # Fallback for items with no media_type
            elif not render_type and primary_urls:
                main_url_for_type_inference = primary_urls[0]
                if ".mp4" in main_url_for_type_inference or ".webm" in main_url_for_type_inference:
                    render_type = "video"
                elif ".wav" in main_url_for_type_inference or ".mp3" in main_url_for_type_inference:
                    render_type = "audio"
                else:
                    render_type = "image"

            media_detail_viewer(
                id=item.id,
                key=item.id,
                media_type=render_type,
                primary_urls_json=primary_urls_json,
                source_urls_json=source_urls_json,
                metadata_json=metadata_json,
                raw_metadata_json=raw_metadata_json,
                on_edit_click=handle_edit_click,
                on_veo_click=handle_veo_click,
            )


        else:
            with me.box(style=me.Style(padding=me.Padding.all(16))):
                me.text("No media item selected or found for the given ID.")
