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

import mesop as me

from common.storage import store_to_gcs
from components.library.library_chooser_button import library_chooser_button


@me.stateclass
class PageState:
    selected_gcs_uri: str = ""


@me.page(path="/test_uploader")
def test_uploader_page():
    state = me.state(PageState)

    def on_test_upload(e: me.UploadEvent):
        gcs_url = store_to_gcs(
            "test_uploads", e.file.name, e.file.mime_type, e.file.getvalue()
        )
        state.selected_gcs_uri = gcs_url.replace(
            "gs://", "https://storage.mtls.cloud.google.com/"
        )
        yield

    def on_test_library_select(uri: str):
        print(f"Test Uploader Page: Received URI from library: {uri}")
        state.selected_gcs_uri = uri.replace(
            "gs://", "https://storage.mtls.cloud.google.com/"
        )
        yield

    with me.box(
        style=me.Style(
            padding=me.Padding.all(24), display="flex", flex_direction="column", gap=16
        )
    ):
        me.text("Test Uploader Components", type="headline-5")

        me.divider()

        me.text("Example 1: Standard Uploader Only")
        me.uploader(label="Upload a file", on_upload=on_test_upload)

        me.divider()

        me.text("Example 2: Library Chooser (Icon and Text)")
        library_chooser_button(
            button_label="Add from Library", on_library_select=on_test_library_select
        )

        me.divider()

        me.text("Example 3: Library Chooser (Icon Only)")
        library_chooser_button(on_library_select=on_test_library_select)

        me.divider()

        me.text("Example 4: Composed Together")
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=8, align_items="center"
            )
        ):
            me.uploader(
                label="Upload a file",
                on_upload=on_test_upload,
                style=me.Style(flex_grow=1),
            )
            library_chooser_button(
                button_label="Add from Library",
                on_library_select=on_test_library_select,
            )

        me.divider()

        if state.selected_gcs_uri:
            with me.box(style=me.Style(margin=me.Margin(top=24))):
                me.text("Selected Image:")
                me.image(
                    src=state.selected_gcs_uri,
                    style=me.Style(width="300px", border_radius=8),
                )
