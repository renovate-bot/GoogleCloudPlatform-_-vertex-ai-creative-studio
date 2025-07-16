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

import uuid

import mesop as me

from common.metadata import add_media_item
from common.storage import store_to_gcs
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from config.default import Default
from models.image_models import generate_image_for_vto
from models.vto import generate_vto_image
from state.state import AppState
from state.vto_state import PageState

config = Default()

IMAGE_BOX_STYLE = me.Style(
    width=400,
    height=400,
    border=me.Border.all(
        me.BorderSide(width=2, style="dashed", color=me.theme_var("outline-variant"))
    ),
    border_radius=12,
    display="flex",
    align_items="center",
    justify_content="center",
    flex_direction="column",
    gap=8,
    margin=me.Margin(top=16),
)


@me.page(path="/vto")
def vto():
    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Virtual Try-On", "checkroom")

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
                # Person Image Section
                with me.box(
                    style=me.Style(
                        width="calc(50% - 8px)",
                        display="flex",
                        flex_direction="column",
                        align_items="center",
                    )
                ):
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=8,
                            align_items="center",
                        )
                    ):
                        me.uploader(
                            label="Upload Person Image",
                            on_upload=lambda e: on_upload_person(e),
                            style=me.Style(width="100%"),
                            key="person_uploader",
                        )
                        me.button(
                            "Create Virtual Model",
                            on_click=on_click_generate_person,
                        )
                    with me.box(style=IMAGE_BOX_STYLE):
                        if state.is_generating_person_image:
                            me.progress_spinner()
                        elif state.person_image_gcs:
                            me.image(
                                src=state.person_image_gcs,
                                style=me.Style(
                                    max_width="100%",
                                    max_height="100%",
                                    border_radius=12,
                                ),
                            )
                        else:
                            me.icon("upload_file", style=me.Style(font_size=48))
                            me.text("Upload a person image")

                # Product Image Section
                with me.box(
                    style=me.Style(
                        width="calc(50% - 8px)",
                        display="flex",
                        flex_direction="column",
                        align_items="center",
                    )
                ):
                    me.uploader(
                        label="Upload Product Image",
                        on_upload=lambda e: on_upload_product(e),
                        style=me.Style(width="100%"),
                        key="product_uploader",
                    )
                    with me.box(style=IMAGE_BOX_STYLE):
                        if state.product_image_gcs:
                            me.image(
                                src=state.product_image_gcs,
                                style=me.Style(
                                    max_width="100%",
                                    max_height="100%",
                                    border_radius=12,
                                ),
                            )
                        else:
                            me.icon("upload_file", style=me.Style(font_size=48))
                            me.text("Upload a product image")

            me.box(style=me.Style(height=36))

            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=10,
                    align_items="center",
                    justify_content="center",
                ),
            ):
                with me.box(style=me.Style(margin=me.Margin(top=16))):
                    with me.box(
                        style=me.Style(display="flex", justify_content="space-between"),
                    ):
                        me.text(f"Number of images: {state.vto_sample_count}")
                    me.slider(
                        min=1,
                        max=4,
                        step=1,
                        value=state.vto_sample_count,
                        on_value_change=on_sample_count_change,
                    )

                me.box(style=me.Style(width=36))

                me.button("Generate", on_click=on_generate, type="flat")
                me.button("Clear", on_click=on_clear, type="stroked")

            if state.is_loading:
                with me.box(
                    style=me.Style(
                        display="flex", align_items="center", justify_content="center",
                    )
                ):
                    me.progress_spinner()

            if state.result_images:
                print(f"Images: {state.result_images}")
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_wrap="wrap",
                        gap=16,
                        margin=me.Margin(top=16),
                        justify_content="center",
                    )
                ):
                    for image in state.result_images:
                        me.image(
                            src=image, style=me.Style(width="400px", border_radius=12)
                        )


def on_upload_person(e: me.UploadEvent):
    """Upload person image handler"""
    state = me.state(PageState)
    state.person_image_file = e.file
    gcs_url = store_to_gcs(
        "vto_person_images", e.file.name, e.file.mime_type, e.file.getvalue()
    )
    state.person_image_gcs = gcs_url.replace(
        "gs://", "https://storage.mtls.cloud.google.com/"
    )
    yield


def on_upload_product(e: me.UploadEvent):
    """Upload product image handler"""
    state = me.state(PageState)
    state.product_image_file = e.file
    gcs_url = store_to_gcs(
        "vto_product_images", e.file.name, e.file.mime_type, e.file.getvalue()
    )
    state.product_image_gcs = gcs_url.replace(
        "gs://", "https://storage.mtls.cloud.google.com/"
    )
    yield


def on_click_generate_person(e: me.ClickEvent):
    """Generate person image handler"""
    state = me.state(PageState)
    state.is_generating_person_image = True
    yield

    try:
        prompt = "A full-length studio shot of a model standing against a neutral seamless background, posed for virtual try-on application. Lighting is bright and even, highlighting the model's form without harsh shadows. The model is facing forward with a natural, relaxed posture and a neutral expression. The focus is sharp and clear, capturing the details of clothing textures and fit, suitable for e-commerce apparel display."
        image_bytes = generate_image_for_vto(prompt)
        file_name = f"generated_person_{uuid.uuid4()}.png"
        gcs_url = store_to_gcs(
            "vto_person_images",
            file_name,
            "image/png",
            image_bytes,
            decode=False,
        )
        state.person_image_gcs = gcs_url.replace(
            "gs://", "https://storage.mtls.cloud.google.com/"
        )
    except Exception as e:
        state.error_message = str(e)
        state.show_error_dialog = True
    finally:
        state.is_generating_person_image = False
        yield


def on_generate(e: me.ClickEvent):
    """Generate VTO handler"""
    app_state = me.state(AppState)
    state = me.state(PageState)
    state.is_loading = True
    yield

    try:
        result_gcs_uris = generate_vto_image(
            state.person_image_gcs,
            state.product_image_gcs,
            state.vto_sample_count,
            state.vto_base_steps,
        )
        print(f"Result GCS URIs: {result_gcs_uris}")
        state.result_images = [
            uri.replace("gs://", "https://storage.mtls.cloud.google.com/")
            for uri in result_gcs_uris
        ]
        add_media_item(
            user_email=app_state.user_email,
            model=config.VTO_MODEL_ID,
            mime_type="image/png",
            gcs_uris=result_gcs_uris,
            person_image_gcs=state.person_image_gcs,
            product_image_gcs=state.product_image_gcs,
        )
    except Exception as e:
        state.error_message = str(e)
        state.show_error_dialog = True
    finally:
        state.is_loading = False
        yield
    yield


def on_sample_count_change(e: me.SliderValueChangeEvent):
    """Handles changes to the sample count slider."""
    state = me.state(PageState)
    state.vto_sample_count = int(e.value)
    yield


def on_clear(e: me.ClickEvent):
    state = me.state(PageState)
    state.person_image_gcs = ""
    state.product_image_gcs = ""
    state.result_images = []
    yield
