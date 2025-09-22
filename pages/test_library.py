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
from components.header import header
from components.lightbox_dialog.lightbox_dialog import lightbox_dialog
from components.library.image_details import CarouselState
from components.media_detail_viewer.media_detail_viewer import media_detail_viewer
from components.media_tile.media_tile import media_tile, get_pills_for_item
from components.page_scaffold import page_frame, page_scaffold


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
    print(f"on_media_item_click received event for key: {e.key}")
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
                source_urls.append(
                    gcs_uri_to_https_url(item.last_reference_image)
                )
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

            # Infer type if missing for robustness
            main_url_for_type_inference = primary_urls[0] if primary_urls else ""
            effective_media_type = item.media_type
            if not effective_media_type and main_url_for_type_inference:
                if (
                    ".wav" in main_url_for_type_inference
                    or ".mp3" in main_url_for_type_inference
                ):
                    effective_media_type = "audio"
                elif (
                    ".mp4" in main_url_for_type_inference
                    or ".webm" in main_url_for_type_inference
                ):
                    effective_media_type = "video"
                else:
                    effective_media_type = "image"

            media_detail_viewer(
                key=item.id,
                media_type=effective_media_type,
                primary_urls_json=primary_urls_json,
                source_urls_json=source_urls_json,
                metadata_json=metadata_json,
            )

            if item.raw_data:
                with me.expansion_panel(
                    key="raw_metadata_panel_dialog",
                    title="Firestore Metadata",
                    description=item.id or "N/A",
                    icon="dataset",
                ):
                    try:
                        json_string = json.dumps(item.raw_data, indent=2, default=str)
                        me.markdown(f"```json\n{json_string}\n```")
                    except Exception:
                        me.text("Could not display raw data (serialization error).")
            else:
                me.text("Raw Firestore data not available.")
        else:
            with me.box(style=me.Style(padding=me.Padding.all(16))):
                me.text("No media item selected or found for the given ID.")
