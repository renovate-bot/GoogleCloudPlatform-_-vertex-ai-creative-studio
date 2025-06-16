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

import mesop as me

from state.veo_state import PageState
from common.storage import store_to_gcs
from config.default import Default

config = Default()


@me.component
def file_uploader():
    """File uploader for I2V and interpolation"""
    state = me.state(PageState)
    me.button_toggle(
        value=state.veo_mode,
        buttons=[
            me.ButtonToggleButton(label="t2v", value="t2v"),
            me.ButtonToggleButton(label="i2v", value="i2v"),
            me.ButtonToggleButton(label="interpolation", value="interpolation"),
        ],
        multiple=False,
        hide_selection_indicator=True,
        on_change=on_selection_change_veo_mode,
        disabled=True if state.veo_model == "3.0" else False,
    )
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            align_items="center",
            flex_basis="max(480px, calc(50% - 48px))",
            padding=me.Padding(bottom=15),
        ),
    ):
        if state.veo_mode == "t2v":
            me.image(src=None, style=me.Style(height=250))
        elif state.veo_mode == "i2v":
            _image_uploader(last_image=False)
        elif state.veo_mode == "interpolation":
            _image_uploader(last_image=True)


@me.component
def _image_uploader(last_image: bool):
    state = me.state(PageState)
    if state.reference_image_uri:
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=5)):
            me.image(
                src=state.reference_image_uri,
                style=me.Style(
                    height=150,
                    border_radius=12,
                ),
                key=str(state.reference_image_file_key),
            )
            if last_image and state.last_reference_image_uri:
                me.image(
                    src=state.last_reference_image_uri,
                    style=me.Style(
                        height=150,
                        border_radius=12,
                    ),
                    key=str(state.last_reference_image_file_key),
                )
    else:
        me.image(src=None, style=me.Style(height=200))
    with me.box(style=me.Style(display="flex", flex_direction="row", gap=5)):
        if last_image:
            me.uploader(
                label="Upload first",
                accepted_file_types=["image/jpeg", "image/png"],
                on_upload=on_click_upload,
                type="raised",
                color="primary",
                style=me.Style(font_weight="bold"),
            )
            me.uploader(
                label="Upload last",
                key="last",
                accepted_file_types=["image/jpeg", "image/png"],
                on_upload=on_click_upload,
                type="raised",
                color="primary",
                style=me.Style(font_weight="bold"),
            )
        else:
            me.uploader(
                label="Upload",
                accepted_file_types=["image/jpeg", "image/png"],
                on_upload=on_click_upload,
                type="raised",
                color="primary",
                style=me.Style(font_weight="bold"),
            )
        me.button(label="Clear", on_click=on_click_clear_reference_image)


def on_selection_change_veo_mode(e: me.ButtonToggleChangeEvent):
    """toggle veo mode"""
    state = me.state(PageState)
    state.veo_mode = e.value


def on_click_upload(e: me.UploadEvent):
    """Upload image to GCS"""
    state = me.state(PageState)
    if e.key == "last":
        print("Interpolation: adding last image")
        state.last_reference_image_file = e.file
        contents = e.file.getvalue()
        destination_blob_name = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, contents
        )
        state.last_reference_image_gcs = f"gs://{destination_blob_name}"
        state.last_reference_image_uri = (
            f"https://storage.mtls.cloud.google.com/{destination_blob_name}"
        )
    else:
        state.reference_image_file = e.file
        contents = e.file.getvalue()
        destination_blob_name = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, contents
        )
        state.reference_image_gcs = f"gs://{destination_blob_name}"
        state.reference_image_uri = (
            f"https://storage.mtls.cloud.google.com/{destination_blob_name}"
        )
    print(
        f"{destination_blob_name} with contents len {len(contents)} of type {e.file.mime_type} uploaded to {config.GENMEDIA_BUCKET}."
    )


def on_click_clear_reference_image(e: me.ClickEvent):
    """Clear reference image"""
    state = me.state(PageState)
    state.reference_image_file = None
    state.reference_image_file_key += 1
    state.reference_image_uri = None
    state.reference_image_gcs = None

    state.last_reference_image_file = None
    state.last_reference_image_file_key += 1
    state.last_reference_image_uri = None
    state.last_reference_image_gcs = None
    state.is_loading = False
