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

# TODO add metdata to firestore for VTO image in addition to the video output

import base64
import concurrent.futures
import csv
import datetime
import time
import uuid
from dataclasses import field

import mesop as me
import requests
from google.cloud import firestore

import models.shop_the_look_workflow as shop_the_look_workflow
from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import (
    download_from_gcs,
    download_from_gcs_as_string,
    list_files_in_bucket,
    store_to_gcs,
)
from common.workflows import WorkflowStepResult
from components.header import header
from components.page_scaffold import (
    page_frame,
    page_scaffold,
)
from components.tab_nav import Tab, tab_group
from config.default import Default
from models.gemini import (
    describe_images_and_look,
    final_image_critic,
    select_best_image_with_description,
)
from models.shop_the_look_models import (
    CatalogRecord,
    GeneratedImageAccuracyWrapper,
    ModelRecord,
    ProgressionImage,
    ProgressionImages,
)
from models.veo import image_to_video
from models.vto import call_virtual_try_on
from pages.styles import _BOX_STYLE_CENTER_DISTRIBUTED
from state.shop_the_look_state import PageState
from state.state import AppState

GROUP_ORDER = ["workflow-retail-modes"]
config = Default()


@me.component
def tab_config():
    state = me.state(PageState)
    state.models = shop_the_look_workflow.load_model_data()
    vto_enterprise_config()


@me.component
def tab_stl():
    state = me.state(PageState)
    if not state.catalog:
        state.catalog = shop_the_look_workflow.load_look_data()
    if not state.models:
        state.models = shop_the_look_workflow.load_model_data()
        shop_the_look_workflow.load_article_data()
    if state.reference_image_gcs_model is None or not state.reference_image_gcs_model:
        stl_model_select()
    elif not state.look or state.look == 0:
        stl_look_select()
    else:
        stl_result()


def on_click_veo(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Veo generate request handler"""
    state = me.state(PageState)
    state.is_loading = True
    state.show_error_dialog = False
    state.error_message = ""
    state.result_video = ""
    state.timing = ""
    state.current_status = f"Generating video with Veo {state.veo_model}"
    yield

    print(f"Lights, camera, action!:\n{state.veo_prompt_input}")

    aspect_ratio = (
        "16:9" if state.veo_model == "3.0" else state.aspect_ratio
    )  # @param ["16:9", "9:16"]
    # TODO seed
    seed = 120
    # TODO set default FALSE instead of requiring
    rewrite_prompt = False
    start_time = time.time()  # Record the starting time
    gcs_uri = ""
    current_error_message = ""

    try:
        veo_prompt = state.veo_prompt_input

        # Attach products descriptions to Veo prompt
        for item in state.catalog:
            if item.look_id == state.look:
                veo_prompt += f"\n {item.ai_description}"

        op = image_to_video(
            veo_prompt,
            state.result_image,
            seed,
            aspect_ratio,
            state.veo_sample_count,
            f"gs://{config.VIDEO_BUCKET}",
            rewrite_prompt,
            state.video_length,
            state.veo_model,
        )

        # Check for explicit errors in response
        if op.get("done") and op.get("error"):
            current_error_message = op["error"].get("message", "Unknown API error")
            print(f"API Error Detected: {current_error_message}")
            # No GCS URI in this case
            gcs_uri = ""
        elif op.get("done") and op.get("response"):
            response_data = op["response"]
            print(f"Response: {response_data}")

            if response_data.get("raiMediaFilteredCount", 0) > 0 and response_data.get(
                "raiMediaFilteredReasons"
            ):
                # Extract the first reason provided
                filter_reason = response_data["raiMediaFilteredReasons"][0]
                current_error_message = f"Content Filtered: {filter_reason}"
                print(f"Filtering Detected: {current_error_message}")
                gcs_uri = ""  # No GCS URI if content was filtered

            else:
                # Extract GCS URI from different possible locations
                if (
                    "generatedSamples" in response_data
                    and response_data["generatedSamples"]
                ):
                    # print(f"Generated Samples: {response_data["generatedSamples"]}")
                    gcs_uri = (
                        response_data["generatedSamples"][0]
                        .get("video", {})
                        .get("uri", "")
                    )
                elif "videos" in response_data and response_data["videos"]:
                    # print(f"Videos: {response_data["videos"]}")
                    gcs_uri = response_data["videos"][0].get("gcsUri", "")

                if gcs_uri:
                    file_name = gcs_uri.split("/")[-1]
                    print("Video generated - use the following to copy locally")
                    print(f"gsutil cp {gcs_uri} {file_name}")
                    state.result_video = gcs_uri
                else:
                    # Success reported, but no video URI found - treat as an error/unexpected state
                    current_error_message = "API reported success but no video URI was found in the response."
                    print(f"Error: {current_error_message}")
                    state.result_video = ""  # Ensure no video is shown
        else:
            # Handle cases where 'done' is false or response structure is unexpected
            current_error_message = (
                "Unexpected API response structure or operation not done."
            )
            print(f"Error: {current_error_message}")
            state.result_video = ""

    # Catch specific exceptions you anticipate
    except ValueError as err:
        print(f"ValueError caught: {err}")
        current_error_message = f"Input Error: {err}"
    except requests.exceptions.HTTPError as err:
        print(f"HTTPError caught: {err}")
        current_error_message = f"Network/API Error: {err}"
    # Catch any other unexpected exceptions
    except Exception as err:
        print(f"Generic Exception caught: {type(err).__name__}: {err}")
        current_error_message = f"An unexpected error occurred: {err}"

    finally:
        end_time = time.time()  # Record the ending time
        execution_time = end_time - start_time  # Calculate the elapsed time
        print(f"Execution time: {execution_time} seconds")  # Print the execution time
        state.timing = f"Generation time: {round(execution_time)} seconds"
        app_state = me.state(AppState)

        #  If an error occurred, update the state to show the dialog
        if current_error_message:
            state.error_message = current_error_message
            state.show_error_dialog = True
            # Ensure no result video is displayed on error
            state.result_video = ""
            yield

        try:
            item_to_log = MediaItem(
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                prompt=state.veo_prompt_input,
                original_prompt=state.veo_prompt_input,
                model=state.veo_model,
                mime_type="video/mp4",
                aspect=aspect_ratio,
                duration=float(execution_time),
                reference_image=state.reference_image_gcs_model,
                last_reference_image=None,
                # negative_prompt=request.negative_prompt,
                # enhanced_prompt_used=request.enhance_prompt,
                comment="veo default generation",
                gcsuri=gcs_uri,
                generation_time=execution_time,
            )
            add_media_item_to_firestore(item_to_log)

        except Exception as meta_err:
            # Handle potential errors during metadata storage itself
            print(f"CRITICAL: Failed to store metadata: {meta_err}")
            # Optionally, display another error or log this critical failure
            if not state.show_error_dialog:  # Avoid overwriting primary error
                state.error_message = f"Failed to store video metadata: {meta_err}"
                state.show_error_dialog = True

    state.is_loading = False
    state.current_status = ""
    yield
    print("Cut! That's a wrap!")


def stl_model_select():
    state = me.state(PageState)

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=10,
            align_items="center",
            width="100%",
        )
    ):
        me.text(
            text="Choose a Model",
            type="headline-2",
            # style=me.Style(width="100%", text_align="center"),
        )
    with me.box():
        with me.box(
            style=me.Style(
                height="100%",
                width="100%",
                display="flex",
                flex_direction="row",
                flex_wrap="wrap",
            )
        ):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="left",
                    # margin=me.Margin(left=10),
                )
            ):
                with me.box(
                    style=me.Style(
                        position="relative",
                        height="100%",
                        margin=me.Margin(left=7, top=7),
                        cursor="pointer",
                    ),
                    key="model",
                    # on_click=on_click_upload_image,
                ):
                    me.uploader(
                        label="",
                        accepted_file_types=["image/jpeg", "image/png"],
                        on_upload=on_click_upload_image,
                        type="flat",
                        color="primary",
                        style=me.Style(
                            position="relative",
                            # margin=me.Margin(left=7, top=7),
                            cursor="pointer",
                            width="200px",  # Consider using max_width or responsive units
                            height="200px",
                            object_fit="cover",
                            border_radius="5px",
                            box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                            background="#FFFFFF",
                        ),
                        key="model",
                        multiple=True,
                    )
                    # me.box(
                    #     style=me.Style(
                    #         width="200px",  # Consider using max_width or responsive units
                    #         height="200px",
                    #         object_fit="cover",
                    #         border_radius="5px",
                    #         box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                    #         background="#FFFFFF",
                    #     ),
                    # )
                    (
                        me.icon(
                            "add",
                            style=me.Style(
                                color="black",
                                position="absolute",
                                top="35px",
                                left="35px",
                                width="35px",
                                height="35px",
                                font_size="35px",
                            ),  # Consider using max_width or responsive units
                        ),
                    )
                    (
                        me.icon(
                            "person_outline",
                            style=me.Style(
                                color="black",
                                position="absolute",
                                top="50px",
                                left="55px",
                                width="100px",
                                height="100px",
                                font_size="100px",
                            ),  # Consider using max_width or responsive units
                        ),
                    )
                    (
                        me.text(
                            text="Add Model",
                            style=me.Style(
                                position="absolute",
                                # width="100%",
                                text_align="center",
                                bottom="45px",
                                left="55px",
                                font_size="20px",
                            ),
                        ),
                    )

            for model in state.models:
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=5,
                        align_items="left",
                        # margin=me.Margin(left=10),
                    )
                ):
                    with me.box(
                        key=f"{model.model_image}",
                        style=me.Style(
                            position="relative",
                            height="100%",
                            margin=me.Margin(left=7, top=7),
                            cursor="pointer",
                        ),
                        on_click=on_model_click,
                    ):
                        # me.icon(
                        #     "delete_forever",
                        #     style=me.Style(
                        #         color="black",
                        #         position="absolute",
                        #         top="5px",
                        #         right="5px",
                        #         width="20px",
                        #         height="20px",
                        #         font_size=("20px"),
                        #     ),
                        # )
                        me.image(
                            src=model.model_image.replace(
                                "gs://",
                                "https://storage.mtls.cloud.google.com/",
                            ),
                            style=me.Style(
                                # width="200px",  # Consider using max_width or responsive units
                                # height="200px",
                                object_fit="cover",
                                border_radius="5px",
                                box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                max_height="200px",
                                height="auto",
                            ),
                        )

    return me


def stl_result():
    state = me.state(PageState)
    with me.box(
        style=me.Style(
            # flex_basis="100%",
            # flex_basis="max(80px, calc(40% - 48px))",
            display="flex",
            flex_direction="row",
            # align_items="stretch",
            justify_content="space-between",
            gap=0,
            margin=me.Margin(top=10),
        )
    ):
        # Model Recap and Action Buttons
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
                gap=0,
                align_items="center",
                flex_basis="300px",
                flex_grow=0,
                flex_shrink=0,
            )
        ):
            if state.before_image_uri:
                me.text(
                    text="Your Model",
                    type="headline-4",
                    style=me.Style(
                        # width="100%",
                        text_align="center",
                        margin=me.Margin(bottom=20),
                    ),
                )
                me.image(
                    src=state.before_image_uri.replace(
                        "gs://",
                        "https://storage.mtls.cloud.google.com/",
                    ),
                    style=me.Style(
                        width="200px",  # Consider using max_width or responsive units
                        height="200px",
                        object_fit="contain",
                        border_radius="115px",
                    ),
                )

            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    align_items="stretch",
                    justify_content="space-between",
                    gap=0,
                    margin=me.Margin(top=10),
                )
            ):
                icon_style = me.Style(
                    display="flex",
                    flex_direction="column",
                    gap=3,
                    font_size=10,
                    align_items="center",
                    cursor="pointer",
                )

                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=15,
                    )
                ):
                    if (
                        state.result_image
                        and not state.result_video
                        and not state.generate_video
                        and not state.is_loading
                    ):
                        with me.content_button(
                            type="icon",
                            on_click=on_click_veo,
                        ):
                            with me.box(style=icon_style):
                                me.icon("cinematic_blur")
                                me.text("Create Video")
                    # if (
                    #     state.result_image
                    #     and not state.result_video
                    #     and not state.generate_alternate_views
                    # ):
                    #     with me.content_button(
                    #         type="icon",
                    #         on_click=on_click_vto_look,
                    #         key="alternate",
                    #     ):
                    #         with me.box(style=icon_style):
                    #             me.icon("directions_walk")
                    #             me.text("Create Alternate Views")
                    if (
                        state.look
                        and state.look != 0
                        and not state.result_image
                        and not state.is_loading
                    ):
                        with me.content_button(
                            type="icon",
                            on_click=on_click_vto_look,
                            key="primary",
                        ):
                            with me.box(style=icon_style):
                                me.icon("play_arrow")
                                me.text("Try On")
                    with me.content_button(
                        type="icon",
                        on_click=on_click_clear_reference_image,
                    ):
                        with me.box(style=icon_style):
                            me.icon("clear")
                            me.text("Clear")

        # Look recap, catalog enrichment
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
                gap=0,
                align_items="left",
                flex_grow=1,
            )
        ):
            me.text(
                text="Your Look",
                type="headline-4",
                style=me.Style(
                    width="100%",
                    text_align="center",
                    margin=me.Margin(bottom=20),
                ),
            )
            if state.look_description:
                me.text(
                    state.look_description,
                    style=me.Style(
                        font_size="14px",
                        margin=me.Margin(bottom=5),
                    ),
                )

            for item in state.articles:
                # if item.look_id == state.look:
                if item.selected:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=0,
                            align_items="center",
                            margin=me.Margin(top=5),
                        )
                    ):
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction=(
                                    "row" if item.ai_description else "column"
                                ),
                                align_items="center",
                                # justify_content="space-between",
                                width="100%",
                            )
                        ):
                            img = item.clothing_image.replace(
                                "gs://",
                                "https://storage.mtls.cloud.google.com/",
                            )
                            me.image(
                                src=img,
                                style=me.Style(
                                    width="100px",  # Consider using max_width or responsive units
                                    height="100px",
                                    object_fit="cover",
                                    border_radius="15px",
                                ),
                            )
                            me.text(
                                item.ai_description,
                                style=me.Style(
                                    font_size="14px",
                                    margin=me.Margin(left=10),
                                    align_items="center",
                                ),
                            )

        # Result image & video
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
                gap=0,
                align_items="center",
                margin=me.Margin(left=30),
                flex_basis="500px",
                flex_grow=0,
                flex_shrink=0,
            )
        ):
            if state.tryon_started:
                me.text(
                    text="Your Try-On",
                    type="headline-4",
                    style=me.Style(
                        width="100%",
                        text_align="center",
                        margin=me.Margin(bottom=20),
                    ),
                    # style=me.Style(font_size="14px", margin=me.Margin(left=10)),
                )
            if state.result_image:
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=0,
                        align_items="center",
                    )
                ):
                    if state.final_critic:
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction="column",
                                position="relative",
                                height="100%",
                            )
                        ):
                            with me.tooltip(
                                message=str(state.final_critic.reasoning),
                            ):
                                if state.final_accuracy:
                                    me.icon(
                                        "check_circle",
                                        style=me.Style(
                                            color="green",
                                            position="absolute",
                                            top="5px",
                                            left="15px",
                                            # font_size="50px",
                                            width="100px",
                                            height="100px",
                                            font_size=(
                                                "25px" if state.result_video else "50px"
                                            ),  # Consider using max_width or responsive units
                                        ),
                                    )
                                else:
                                    me.icon(
                                        "error",
                                        style=me.Style(
                                            color="red",
                                            width="50px",
                                            height="50px",
                                            font_size=(
                                                "25px" if state.result_video else "50px"
                                            ),
                                        ),
                                    )
                                    if not state.is_loading:
                                        with me.tooltip(
                                            message="Retry",
                                        ):
                                            with me.box(
                                                on_click=on_click_manual_retry,
                                            ):
                                                me.icon(
                                                    "refresh",
                                                    style=me.Style(
                                                        color="black",
                                                        width="50px",
                                                        height="50px",
                                                        font_size=(
                                                            "25px"
                                                            if state.result_video
                                                            else "50px"
                                                        ),
                                                    ),
                                                )
                    me.image(
                        src=state.result_image.replace(
                            "gs://",
                            "https://storage.mtls.cloud.google.com/",
                        ),
                        style=me.Style(
                            margin=me.Margin(left=10),
                            width=(
                                "250px" if state.result_video else "500px"
                            ),  # Consider using max_width or responsive units
                            height=(
                                "250px" if state.result_video else "500px"
                            ),  # Consider using max_width or responsive units
                            object_fit="contain",
                            border_radius="5px",
                            box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                        ),
                    )
                    if state.result_video:
                        video_url = state.result_video.replace(
                            "gs://",
                            "https://storage.mtls.cloud.google.com/",
                        )
                        print(f"video_url: {video_url}")
                        with me.tooltip(message=state.veo_prompt_input):
                            me.icon("information")
                        me.video(
                            src=video_url,
                            style=me.Style(
                                border_radius=6,
                                width="250px",  # Consider using max_width or responsive units
                                height="250px",
                                object_fit="contain",
                            ),
                        )
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=0,
                        align_items="right",
                    )
                ):
                    if state.alternate_images:
                        with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED):
                            with me.box(
                                style=me.Style(
                                    height="100%",
                                    align_items="right",
                                )
                            ):
                                for img in state.alternate_images:
                                    image_url = img.replace(
                                        "gs://",
                                        "https://storage.mtls.cloud.google.com/",
                                    )
                                    me.image(
                                        src=image_url,
                                        style=me.Style(
                                            margin=me.Margin(left=10),
                                            width="200px",  # Consider using max_width or responsive units
                                            height="200px",
                                            object_fit="contain",
                                            border_radius="5px",
                                            box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                        ),
                                    )
            else:
                me.image(
                    src=state.before_image_uri.replace(
                        "gs://",
                        "https://storage.mtls.cloud.google.com/",
                    ),
                    style=me.Style(
                        margin=me.Margin(left=10),
                        width="500px",  # Consider using max_width or responsive units
                        height="500px",
                        object_fit="contain",
                        border_radius="5px",
                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                        opacity=".1",
                    ),
                )

    # Progression Images
    if state.progression_images:
        with me.expansion_panel(
            key="progression",
            title="Primary View",
            description=f"Image Progression",
            icon="checkroom",
            disabled=False,
            expanded=state.normal_accordion["progression"],
            hide_toggle=False,
            # on_toggle=on_accordion_toggle,
            style=me.Style(
                margin=me.Margin(top=10),
            ),
        ):
            for p in state.progression_images:
                with me.box():
                    with me.box(
                        style=me.Style(
                            height="100%",
                            display="flex",
                            flex_direction="row",
                        )
                    ):
                        for img in p.progression_images:
                            image_url = img.image_path.replace(
                                "gs://",
                                "https://storage.mtls.cloud.google.com/",
                            )

                            with me.box(
                                style=me.Style(
                                    position="relative",
                                    height="100%",
                                )
                            ):
                                with me.tooltip(
                                    message=str(img.reasoning),
                                ):
                                    if img.best_image and img.accurate:
                                        me.icon(
                                            "check_circle",
                                            style=me.Style(
                                                color="green",
                                                position="absolute",
                                                top="1px",
                                                left="15px",
                                            ),
                                        )
                                    elif img.best_image and not img.accurate:
                                        me.icon(
                                            "check_circle",
                                            style=me.Style(
                                                color="red",
                                                position="absolute",
                                                top="1px",
                                                left="15px",
                                            ),
                                        )
                                    elif img.accurate:
                                        me.icon(
                                            "check_circle",
                                            style=me.Style(
                                                color="#999",
                                                position="absolute",
                                                top="1px",
                                                left="15px",
                                            ),
                                        )
                                    else:
                                        me.icon(
                                            "error",
                                            style=me.Style(
                                                color="red",
                                                position="absolute",
                                                top="1px",
                                                left="15px",
                                            ),
                                        )
                                me.image(
                                    src=image_url,
                                    style=me.Style(
                                        margin=me.Margin(left=10),
                                        width="200px",  # Consider using max_width or responsive units
                                        height="200px",
                                        object_fit="cover",
                                        border_radius="5px",
                                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                        # opacity=("1" if img.best_image else ".5"),
                                    ),
                                )
            if state.alternate_progression_images:
                with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED):
                    with me.box(style=me.Style(height="100%")):
                        for img in state.alternate_progression_images:
                            image_url = img.replace(
                                "gs://",
                                "https://storage.mtls.cloud.google.com/",
                            )
                            me.image(
                                src=image_url,
                                style=me.Style(
                                    margin=me.Margin(left=10),
                                    width="200px",  # Consider using max_width or responsive units
                                    height="200px",
                                    object_fit="contain",
                                    border_radius="5px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                ),
                            )

    if state.retry_progression_images:
        with me.expansion_panel(
            key="retry_progression",
            title="Retry",
            description="Image Progression",
            icon="checkroom",
            disabled=False,
            expanded=state.normal_accordion["retry_progression"],
            hide_toggle=False,
            # on_toggle=on_accordion_toggle,
            style=me.Style(
                margin=me.Margin(top=10),
            ),
        ):
            for p in state.retry_progression_images:
                with me.box():
                    with me.box(
                        style=me.Style(
                            height="100%",
                            display="flex",
                            flex_direction="row",
                        )
                    ):
                        for img in p.progression_images:
                            image_url = img.image_path.replace(
                                "gs://",
                                "https://storage.mtls.cloud.google.com/",
                            )

                            with me.box(
                                style=me.Style(
                                    position="relative",
                                    height="100%",
                                )
                            ):
                                with me.tooltip(
                                    message=str(img.reasoning),
                                ):
                                    if img.best_image and img.accurate:
                                        me.icon(
                                            "check_circle",
                                            style=me.Style(
                                                color="green",
                                                position="absolute",
                                                top="1px",
                                                left="15px",
                                            ),
                                        )
                                    elif img.best_image and not img.accurate:
                                        me.icon(
                                            "check_circle",
                                            style=me.Style(
                                                color="red",
                                                position="absolute",
                                                top="1px",
                                                left="15px",
                                            ),
                                        )
                                    elif img.accurate:
                                        me.icon(
                                            "check_circle",
                                            style=me.Style(
                                                color="#999",
                                                position="absolute",
                                                top="1px",
                                                left="15px",
                                            ),
                                        )
                                    else:
                                        me.icon(
                                            "error",
                                            style=me.Style(
                                                color="red",
                                                position="absolute",
                                                top="1px",
                                                left="15px",
                                            ),
                                        )
                                me.image(
                                    src=image_url,
                                    style=me.Style(
                                        margin=me.Margin(left=10),
                                        width="200px",  # Consider using max_width or responsive units
                                        height="200px",
                                        object_fit="cover",
                                        border_radius="5px",
                                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                        # opacity=("1" if img.best_image else ".5"),
                                    ),
                                )
    return me


def on_click_manual_retry(e: me.ClickEvent):
    state = me.state(PageState)
    state.retry_counter -= 1

    new_event = e
    new_event.key = "retry"
    yield from on_click_vto_look(new_event)


def article_on_click(e: me.ClickEvent):
    state = me.state(PageState)
    selected_type = e.key.split("_")[-1]
    selected_id = e.key.split("_")[-2]

    selected = False
    for item in state.articles:
        print(f"comparing {item.item_id} to {selected_id}")
        if item.item_id == selected_id:
            item.selected = not item.selected
            selected = item.selected

    for item in state.articles:
        if item.item_id != selected_id:
            if selected_type == "shoe" and item.article_type == "shoe":
                item.available_to_select = not selected
                item.selected = False
            elif selected_type == "dress" and item.article_type in [
                "dress",
                "top",
                "bottom",
            ]:
                item.available_to_select = not selected
                item.selected = False
            elif selected_type == "top" and item.article_type in ["dress", "top"]:
                item.available_to_select = not selected
                item.selected = False
            elif selected_type == "bottom" and item.article_type in ["dress", "bottom"]:
                item.available_to_select = not selected
                item.selected = False

    yield


def stl_look_select():
    state = me.state(PageState)

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=10,
            align_items="center",
            width="100%",
        )
    ):
        me.text(
            text="Choose a Look",
            type="headline-2",
            # style=me.Style(width="100%", text_align="center"),
        )
    with me.box():
        with me.box(
            style=me.Style(
                height="100%",
                width="100%",
                display="flex",
                flex_direction="row",
                flex_wrap="wrap",
            )
        ):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="left",
                    # margin=me.Margin(left=10),
                )
            ):
                with me.box(
                    style=me.Style(
                        position="relative",
                        height="100%",
                        cursor="pointer",
                    ),
                    key="apparel",
                    # on_click=on_click_upload_image,
                ):
                    me.uploader(
                        label="",
                        accepted_file_types=["image/jpeg", "image/png"],
                        on_upload=on_click_upload_image,
                        type="flat",
                        color="primary",
                        style=me.Style(
                            position="relative",
                            cursor="pointer",
                            width="150px",  # Consider using max_width or responsive units
                            height="150px",
                            object_fit="cover",
                            border_radius="5px",
                            box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                            background="#FFFFFF",
                            margin=me.Margin(left=10, top=10),
                        ),
                        key="top",
                        multiple=True,
                    )
                    (
                        me.icon(
                            "add",
                            style=me.Style(
                                color="black",
                                position="absolute",
                                top="20px",
                                left="30px",
                                width="30px",
                                height="30px",
                                font_size="30px",
                            ),  # Consider using max_width or responsive units
                        ),
                    )
                    (
                        me.icon(
                            "apparel",
                            style=me.Style(
                                color="black",
                                position="absolute",
                                top="45px",
                                left="55px",
                                width="50px",
                                height="50px",
                                font_size="50px",
                            ),  # Consider using max_width or responsive units
                        ),
                    )
                    (
                        me.text(
                            text="Add Top",
                            style=me.Style(
                                position="absolute",
                                # width="100%",
                                text_align="center",
                                bottom="35px",
                                left="45px",
                                font_size="20px",
                            ),
                        ),
                    )
            with me.box(
                style=me.Style(
                    position="relative",
                    height="100%",
                    cursor="pointer",
                ),
                key="apparel",
                # on_click=on_click_upload_image,
            ):
                me.uploader(
                    label="",
                    accepted_file_types=["image/jpeg", "image/png"],
                    on_upload=on_click_upload_image,
                    type="flat",
                    color="primary",
                    style=me.Style(
                        position="relative",
                        cursor="pointer",
                        width="150px",  # Consider using max_width or responsive units
                        height="150px",
                        object_fit="cover",
                        border_radius="5px",
                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                        background="#FFFFFF",
                        margin=me.Margin(left=10, top=10),
                    ),
                    key="bottom",
                    multiple=True,
                )
                (
                    me.icon(
                        "add",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="20px",
                            left="30px",
                            width="30px",
                            height="30px",
                            font_size="30px",
                        ),  # Consider using max_width or responsive units
                    ),
                )
                (
                    me.icon(
                        "styler",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="45px",
                            left="55px",
                            width="50px",
                            height="50px",
                            font_size="50px",
                        ),  # Consider using max_width or responsive units
                    ),
                )
                (
                    me.text(
                        text="Add Bottom",
                        style=me.Style(
                            position="absolute",
                            # width="100%",
                            text_align="center",
                            bottom="35px",
                            left="30px",
                            font_size="20px",
                        ),
                    ),
                )

            with me.box(
                style=me.Style(
                    position="relative",
                    height="100%",
                    cursor="pointer",
                ),
                key="apparel",
                # on_click=on_click_upload_image,
            ):
                me.uploader(
                    label="",
                    accepted_file_types=["image/jpeg", "image/png"],
                    on_upload=on_click_upload_image,
                    type="flat",
                    color="primary",
                    style=me.Style(
                        position="relative",
                        cursor="pointer",
                        width="150px",  # Consider using max_width or responsive units
                        height="150px",
                        object_fit="cover",
                        border_radius="5px",
                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                        background="#FFFFFF",
                        margin=me.Margin(left=10, top=10),
                    ),
                    key="dress",
                    multiple=True,
                )
                (
                    me.icon(
                        "add",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="20px",
                            left="30px",
                            width="30px",
                            height="30px",
                            font_size="30px",
                        ),  # Consider using max_width or responsive units
                    ),
                )
                (
                    me.icon(
                        "girl",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="35px",
                            left="45px",
                            width="70px",
                            height="70px",
                            font_size="70px",
                        ),  # Consider using max_width or responsive units
                    ),
                )
                (
                    me.text(
                        text="Add Dress",
                        style=me.Style(
                            position="absolute",
                            # width="100%",
                            text_align="center",
                            bottom="35px",
                            left="35px",
                            font_size="20px",
                        ),
                    ),
                )

            with me.box(
                style=me.Style(
                    position="relative",
                    height="100%",
                    cursor="pointer",
                ),
                key="apparel",
                # on_click=on_click_upload_image,
            ):
                me.uploader(
                    label="",
                    accepted_file_types=["image/jpeg", "image/png"],
                    on_upload=on_click_upload_image,
                    type="flat",
                    color="primary",
                    style=me.Style(
                        position="relative",
                        cursor="pointer",
                        width="150px",  # Consider using max_width or responsive units
                        height="150px",
                        object_fit="cover",
                        border_radius="5px",
                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                        background="#FFFFFF",
                        margin=me.Margin(left=10, top=10),
                    ),
                    key="shoe",
                    multiple=True,
                )
                (
                    me.icon(
                        "add",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="20px",
                            left="30px",
                            width="30px",
                            height="30px",
                            font_size="30px",
                        ),  # Consider using max_width or responsive units
                    ),
                )
                (
                    me.icon(
                        "steps",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="45px",
                            left="55px",
                            width="50px",
                            height="50px",
                            font_size="50px",
                        ),  # Consider using max_width or responsive units
                    ),
                )
                (
                    me.text(
                        text="Add Shoe",
                        style=me.Style(
                            position="absolute",
                            # width="100%",
                            text_align="center",
                            bottom="35px",
                            left="35px",
                            font_size="20px",
                        ),
                    ),
                )

            for item in state.articles:
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=5,
                        align_items="left",
                        # margin=me.Margin(left=10),
                    )
                ):
                    img = item.clothing_image.replace(
                        "gs://",
                        "https://storage.mtls.cloud.google.com/",
                    )
                    print(f"item.clothing_image {item.clothing_image}")
                    with me.box(
                        key=f"{item.item_id}_{item.article_type}",
                        style=me.Style(
                            position="relative",
                            height="100%",
                            # display=("block" if item.available_to_select else "none"),
                            margin=me.Margin(left=10, top=10),
                            cursor="pointer",
                        ),
                        on_click=article_on_click,
                    ):
                        me.icon(
                            "check_circle",
                            style=me.Style(
                                color=("green" if item.selected else "#666"),
                                position="absolute",
                                top="1px",
                                left="5px",
                                opacity=("1" if item.selected else ".1"),
                            ),
                        )

                        me.image(
                            src=img,
                            style=me.Style(
                                width="150px",  # Consider using max_width or responsive units
                                height="150px",
                                object_fit="cover",
                                border_radius="5px",
                                box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                opacity=(
                                    "1"
                                    if (item.available_to_select or item.selected)
                                    else ".3"
                                ),
                            ),
                        )
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="row",
            gap=5,
            align_items="right",
        ),
    ):
        me.button(
            "Continue",
            type="flat",
            style=me.Style(
                width=75,
                height=40,
                border_radius=5,
                cursor="pointer",
                margin=me.Margin(left=5, top=10),
            ),
            on_click=on_continue_click,
        )


def on_model_click(e: me.ClickEvent):
    state = me.state(PageState)
    state.reference_image_gcs_model = e.key
    state.before_image_uri = e.key
    print(f"state.before_image_uri {state.before_image_uri}")
    for m in state.models:
        if m.model_image in e.key:
            state.selected_model = m


def on_continue_click(e: me.ClickEvent):
    state = me.state(PageState)
    print(e)
    state.look = 2


def on_look_button_click(e: me.ClickEvent):
    state = me.state(PageState)
    print(e)
    state.look = int(e.key)
    # You can add more complex logic here, like updating state, navigating, etc.


# Config Events
def on_config_generate_alt_views(event: me.CheckboxChangeEvent):
    state = me.state(PageState)
    state.generate_alternate_views = event.checked


def on_config_generate_videos(event: me.CheckboxChangeEvent):
    state = me.state(PageState)
    state.generate_video = event.checked


def on_config_upload_everyone(event: me.CheckboxChangeEvent):
    state = me.state(PageState)
    state.upload_everyone = event.checked


def on_veo_version_change(e: me.SelectSelectionChangeEvent):
    s = me.state(PageState)
    s.veo_model = e.value


def on_sample_count_change(e: me.SelectSelectionChangeEvent):
    s = me.state(PageState)
    s.vto_sample_count = e.value


def max_retry_change(e: me.SelectSelectionChangeEvent):
    s = me.state(PageState)
    s.max_retry = e.value


def on_blur_veo_prompt(e: me.InputBlurEvent):
    """Veo prompt blur event"""
    me.state(PageState).veo_prompt_input = e.value


# End Config Events


def vto_enterprise_config():
    state = me.state(PageState)
    app_state = me.state(AppState)

    with me.box():
        with me.box(
            style=me.Style(
                height="100%",
                width="100%",
                display="flex",
                flex_direction="row",
                flex_wrap="wrap",
            )
        ):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.text(
                    text="VTO",
                    type="headline-6",
                )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.checkbox(
                    "Upload model/clothing for all access?",
                    checked=state.upload_everyone,
                    on_change=on_config_upload_everyone,
                )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.select(
                    label="VTO Sample Count",
                    options=[
                        me.SelectOption(label="1 image", value="1"),
                        me.SelectOption(label="2 images", value="2"),
                        me.SelectOption(label="3 images", value="3"),
                        me.SelectOption(label="4 images", value="4"),
                    ],
                    on_selection_change=on_sample_count_change,
                    style=me.Style(width=180),
                    multiple=False,
                    appearance="outline",
                    value=state.vto_sample_count,
                )
                me.select(
                    label="Max Auto Retry",
                    options=[
                        me.SelectOption(label="1 times", value="1"),
                        me.SelectOption(label="2 times", value="2"),
                        me.SelectOption(label="3 times", value="3"),
                        me.SelectOption(label="4 times", value="4"),
                    ],
                    on_selection_change=max_retry_change,
                    style=me.Style(width=180),
                    multiple=False,
                    appearance="outline",
                    value=state.max_retry,
                )

            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.text(
                    text="VEO",
                    type="headline-6",
                )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.select(
                    label="Version",
                    options=[
                        me.SelectOption(label="Veo 3", value="3.0"),
                        me.SelectOption(label="Veo 2", value="2.0"),
                    ],
                    on_selection_change=on_veo_version_change,
                    style=me.Style(width=140),
                    multiple=False,
                    appearance="outline",
                    value=state.veo_model,
                )
                me.checkbox(
                    "Generate videos (in addition)",
                    checked=state.generate_video,
                    on_change=on_config_generate_videos,
                )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.text(
                    text="Base Prompt",
                    style=me.Style(
                        font_size="12px",
                    ),
                )
            me.native_textarea(
                autosize=True,
                min_rows=10,
                max_rows=13,
                placeholder="Base prompt",
                style=me.Style(
                    padding=me.Padding(top=16, left=16),
                    background=me.theme_var("secondary-container"),
                    outline="none",
                    width="1200px",
                    overflow_y="auto",
                    border=me.Border.all(
                        me.BorderSide(style="none"),
                    ),
                    color=me.theme_var("foreground"),
                    flex_grow=1,
                ),
                on_blur=on_blur_veo_prompt,
                # key=str(state.veo_prompt_textarea_key),
                value=state.veo_prompt_input,
            )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                    margin=me.Margin(top=10),
                )
            ):
                me.text(
                    text="Apparel",
                    type="headline-6",
                )
            if state.articles:
                for item in state.articles:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=5,
                            align_items="left",
                        )
                    ):
                        img = item.clothing_image.replace(
                            "gs://",
                            "https://storage.mtls.cloud.google.com/",
                        )
                        print(f"item.clothing_image {item.clothing_image}")
                        with me.box(
                            key=f"{item.item_id}-{item.article_type}",
                            style=me.Style(
                                position="relative",
                                height="100%",
                                margin=me.Margin(left=10, top=10),
                            ),
                        ):
                            with me.box(
                                key=f"{img}",
                                on_click=shop_the_look_workflow.article_on_delete,
                                style=me.Style(
                                    cursor="pointer",
                                ),
                            ):
                                me.icon(
                                    "delete",
                                    style=me.Style(
                                        color="red",
                                        position="absolute",
                                        top="5px",
                                        left="5px",
                                        height="30px",
                                        width="30px",
                                        font_size="30px",
                                    ),
                                )

                            me.image(
                                src=img,
                                style=me.Style(
                                    width="150px",  # Consider using max_width or responsive units
                                    height="150px",
                                    object_fit="cover",
                                    border_radius="5px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                ),
                            )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                for item in state.reference_image_uri_clothing:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=5,
                            align_items="left",
                        )
                    ):
                        with me.box(
                            key=f"{item}",
                            style=me.Style(
                                position="relative",
                                height="100%",
                                margin=me.Margin(left=7, top=7),
                                cursor="pointer",
                            ),
                        ):
                            me.image(
                                src=f"{item}",
                                style=me.Style(
                                    width="200px",  # Consider using max_width or responsive units
                                    height="200px",
                                    object_fit="cover",
                                    border_radius="5px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                ),
                            )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                    margin=me.Margin(top=10),
                )
            ):
                me.text(
                    text="Models",
                    type="headline-6",
                )
            print(state.models)
            if state.models:
                for model in state.models:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=5,
                            align_items="left",
                        )
                    ):
                        img = model.model_image.replace(
                            "gs://",
                            "https://storage.mtls.cloud.google.com/",
                        )
                        print(f"model.model_image {model.model_image}")
                        with me.box(
                            style=me.Style(
                                position="relative",
                                height="100%",
                                margin=me.Margin(left=10, top=10),
                            ),
                        ):
                            with me.box(
                                key=f"{img}",
                                on_click=shop_the_look_workflow.model_on_delete,
                                style=me.Style(
                                    cursor="pointer",
                                ),
                            ):
                                me.icon(
                                    "delete",
                                    style=me.Style(
                                        color="red",
                                        position="absolute",
                                        top="5px",
                                        left="5px",
                                        height="30px",
                                        width="30px",
                                        font_size="30px",
                                    ),
                                )

                            me.image(
                                src=img,
                                style=me.Style(
                                    width="150px",  # Consider using max_width or responsive units
                                    height="150px",
                                    object_fit="cover",
                                    border_radius="5px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",  # Use theme shadow if available
                                ),
                            )

    return me


def build_tab_nav():
    state = me.state(PageState)
    app_state = me.state(AppState)

    visible = (
        True
        if app_state.user_email in ["andrewturner@google.com", "rouzbeha@google.com"]
        else True
    )
    tabs = [
        Tab(label="Shop the Look", icon="apparel", content=tab_stl),
        Tab(
            label="Config",
            icon="settings",
            content=tab_config,
            tab_width="100px",
            visible=visible,
        ),
    ]
    for index, tab in enumerate(tabs):
        tab.selected = state.selected_tab_index == index
        tab.disabled = index in state.disabled_tab_indexes
    # return tabs
    tab_group(tabs, on_tab_click)


def on_tab_click(e: me.ClickEvent):
    """Click handler that handles updating the tabs when clicked."""
    state = me.state(PageState)
    _, tab_index = e.key.split("-")
    tab_index = int(tab_index)

    if tab_index == state.selected_tab_index:
        return
    if tab_index in state.disabled_tab_indexes:
        return

    next(on_click_clear_reference_image())
    state.selected_tab_index = int(tab_index)


def on_click_upload_image(e: me.UploadEvent):
    """Upload image to GCS"""
    state = me.state(PageState)

    for i, file in enumerate(e.files):
        state.current_status = f"Uploading {i + 1} of {len(e.files)}"
        state.reference_image_file_clothing = e.file
        yield
        filename_uuid = str(uuid.uuid4())
        file_ext = file.name.split(".")[-1]
        filename = f"{filename_uuid}.{file_ext}"

        if e.key == "model":
            file_path = f"gs://{config.GENMEDIA_BUCKET}/uploads/models/{filename}"
            gcs_url = store_to_gcs(
                "uploads/models",
                filename.lower(),
                file.mime_type,
                file.getvalue(),
            )
            shop_the_look_workflow.store_model_data(file_path)
        else:
            file_path = (
                f"gs://{config.GENMEDIA_BUCKET}/uploads/apparel/{e.key}/{filename}"
            )
            gcs_url = store_to_gcs(
                f"uploads/apparel/{e.key}",
                filename.lower(),
                file.mime_type,
                file.getvalue(),
            )
            state.reference_image_gcs_clothing.append(f"{gcs_url}")
            state.reference_image_uri_clothing.append(
                gcs_url.replace(
                    "gs://",
                    "https://storage.mtls.cloud.google.com/",
                )
            )
            article_type = gcs_url.split("/")[-2]
            shop_the_look_workflow.store_article_data(file_path, article_type)

        print(
            f"{gcs_url} of type {e.file.mime_type} uploaded to {config.GENMEDIA_BUCKET}."
        )

        state.current_status = ""
        yield

    if e.key == "model":
        state.models = shop_the_look_workflow.load_model_data()
        yield
    else:
        shop_the_look_workflow.load_article_data()
        yield


def on_click_vto_look(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Veo generate request handler"""
    vto_start_time = time.time()
    state = me.state(PageState)
    state.tryon_started = True
    state.is_loading = True
    state.show_error_dialog = False  # Reset error state before starting
    state.error_message = ""
    # state.result_image = ""  # Clear previous result
    state.timing = ""  # Clear previous timing
    yield

    look_articles = shop_the_look_workflow.get_selected_look()
    articles_for_vto = []

    if e.key == "primary":
        state.retry_counter = 0
    elif e.key == "retry":
        print(f"attempting retry {state.retry_counter}")
        if state.retry_counter >= int(state.max_retry):
            return

        state.retry_counter += 1

    # Create a list of failed items to be used later
    if e.key == "retry":
        # reverse order during retry bc try on order may have been reason for failure
        look_articles.reverse()

        failed_articles = list(
            filter(
                lambda critic_record: critic_record.accurate == False,
                state.final_critic.image_accuracy,
            )
        )

        print(f"failed articles is {failed_articles}")
        failed_article_paths = []
        for f in failed_articles:
            failed_article_paths.append(f.article_image_path.split("/")[-1])

        for i, row in enumerate(look_articles):
            print(f"comparing {row.item_id} to {failed_article_paths}")
            if row.item_id.split("/")[-1] in failed_article_paths:
                articles_for_vto.append(row)
    else:
        articles_for_vto = look_articles

    print(f"articles_for_vto {articles_for_vto}")
    images_to_process = shop_the_look_workflow.get_model_records(
        state.selected_model.model_id
    )

    if e.key == "alternate":
        status_prefix = "Alt View: "
    elif e.key == "retry":
        status_prefix = f"Critic Retry {state.retry_counter}: "
    else:
        status_prefix = "Primary View: "

    # article_image_bytes_list_wrapper = []

    print(f"images_to_process {images_to_process}")

    for r in images_to_process:
        # loop through images for the model (primary + alternate model)
        # TODO change from primary being int to bool
        if e.key == "primary" and r.primary_view == False:
            continue
        elif e.key == "alternate" and r.primary_view == True:
            continue
        elif e.key == "retry" and r.primary_view == False:
            continue

        if e.key != "retry":
            # state.reference_image_gcs_model = (
            #     f"gs://{config.GENMEDIA_BUCKET}/{r.model_image}"
            # )
            state.reference_image_gcs_model = r.model_image

            state.current_status = "Generating catalog descriptions"
            yield
            # STEP 1 DESCRIBE PRODUCT
            step_start_time = time.time()
            yield WorkflowStepResult(
                step_name="describe_product",
                status="processing",
                message=f"Catalog Enrichment: Generating catalog description",
                duration_seconds=0,
                data={},
            )

        articles = []
        for i, row in enumerate(look_articles):
            articles.append(f"{row.clothing_image}")

        # Call Gemini to get catalog enrichment information
        with concurrent.futures.ThreadPoolExecutor() as executor_catalog_enrichment:
            futures = []
            futures_vto = []

            if e.key == "primary" or e.key == "retry":
                futures.append(
                    executor_catalog_enrichment.submit(
                        describe_images_and_look, look_articles
                    )
                )

                # Download catalog images while we wait on enrichment callback
                # TODO make this an object instead of two lists
                article_image_bytes_list = []
                article_image_uri_list = []
                with concurrent.futures.ThreadPoolExecutor() as executor_apparel_images:
                    print(f"articles is {articles}")
                    results = executor_apparel_images.map(download_from_gcs, articles)
                    with concurrent.futures.ThreadPoolExecutor() as executor_vto:
                        r1 = articles_for_vto[0]
                        article_image_uri_list.append(r1.clothing_image)
                        state.current_status = (
                            f"{status_prefix}Trying on {r1.article_type}..."
                        )
                        yield
                        futures_vto.append(
                            executor_vto.submit(
                                call_virtual_try_on,
                                person_image_bytes=None,
                                product_image_bytes=None,
                                person_image_uri=state.reference_image_gcs_model,
                                product_image_uri=r1.clothing_image,
                                sample_count=int(state.vto_sample_count),
                                prompt="the shirt should be tucked in",
                                product_description="tucked in shirt",
                            )
                        )
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            result = (
                                future.result()
                            )  # Get the result of the completed task
                            if e.key != "retry":
                                state.look_description = result.look_description

                                for item in state.articles:
                                    for article in result.articles:
                                        if (
                                            item.item_id.split("/")[-1]
                                            == article.article_image_path.split("/")[-1]
                                        ):
                                            item.ai_description = (
                                                article.article_description
                                            )
                                yield
                        except Exception as exc:
                            print(f"generated an exception: {exc}")

                            step_duration = time.time() - step_start_time
                            yield WorkflowStepResult(
                                step_name="describe_product",
                                status="complete",
                                message="Look and article description generated",
                                duration_seconds=step_duration,
                                data={},
                            )

                    for result in results:
                        # article_image_bytes_list_wrapper.append(result)
                        article_image_bytes_list.append(result)

                    # print(f"Results are {results}")
                    # print(f"article_image_bytes_list are {article_image_bytes_list}")

                    for future in concurrent.futures.as_completed(futures_vto):
                        for i, row in enumerate(articles_for_vto):
                            start_time = time.time()  # Record the starting time

                            # try:
                            potential_images = []
                            progressions = ProgressionImages()
                            temp_progressions = []

                            if i > 0:
                                article_image_uri_list.append(row.clothing_image)

                                state.current_status = (
                                    f"{status_prefix}Trying on {row.article_type}..."
                                )
                                yield
                                # ###########THREAD 2###########
                                # STEP 2 CALL VTO
                                op = call_virtual_try_on(
                                    person_image_bytes=None,
                                    product_image_bytes=None,
                                    person_image_uri=state.reference_image_gcs_model,
                                    product_image_uri=row.clothing_image,
                                    sample_count=int(state.vto_sample_count),
                                    # TODO testing with these
                                    # prompt="the shirt should be tucked in",
                                    # product_description="tucked in shirt",
                                )
                            else:
                                result = future.result()
                                op = result

                            # if e.key != "retry":
                            for p in op.predictions:
                                potential_images.append(p["gcsUri"])
                                temp_progressions.append(
                                    # TODO just attach progression image instead of generating new object
                                    ProgressionImage(
                                        image_path=p["gcsUri"],
                                        best_image=False,
                                        reasoning="",
                                    )
                                )

                            # STEP 4 DOWNLOAD PROGRESSION IMAGES FROM STORAGE
                            step_start_time = time.time()
                            yield WorkflowStepResult(
                                step_name="download_candidate_images",
                                status="processing",
                                message=f"Step 1 of 7: Downloading {len(potential_images)} candidate images...",
                                duration_seconds=0,
                                data={},
                            )

                            reference_image_bytes_list = []
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                reference_image_bytes_list = list(
                                    executor.map(download_from_gcs, potential_images)
                                )
                            step_duration = time.time() - step_start_time
                            yield WorkflowStepResult(
                                step_name="download_candidate_images",
                                status="complete",
                                message="Reference images downloaded.",
                                duration_seconds=step_duration,
                                data={},
                            )

                            state.current_status = f"{status_prefix}Selecting best image of {row.article_type}..."
                            yield

                            # STEP 5 CALL PROGRESSION CRITIC - CHOOSE BEST IMAGE
                            step_start_time = time.time()
                            yield WorkflowStepResult(
                                step_name="display_images",
                                status="processing",
                                message=f"Step 3 of 7: Display images",
                                duration_seconds=0,
                                data={},
                            )

                            byte_lookup = None
                            for z, art in enumerate(articles):
                                if (
                                    row.clothing_image.split("/")[-1]
                                    == art.split("/")[-1]
                                ):
                                    byte_lookup = article_image_bytes_list[z]
                                    continue

                            best_match = select_best_image_with_description(
                                [byte_lookup],
                                reference_image_bytes_list,
                                potential_images,
                                f"a {row.article_type}",
                                f"the {row.article_type}",
                            )
                            print(f"best match is {best_match}")
                            last_best_image = None

                            for p in temp_progressions:
                                for bm in best_match.image_accuracy:
                                    if bm.best_image:
                                        last_best_image = p.image_path
                                    if bm.article_image_path == p.image_path:
                                        p.best_image = bm.best_image
                                        p.reasoning = bm.reasoning
                                        p.article_image_path = bm.article_image_path
                                        p.reasoning = bm.reasoning
                                        p.best_image = bm.best_image
                                        p.accurate = bm.accurate
                                        state.result_images.append(p.image_path)
                                        continue

                            print(
                                f"state.progression_images is {state.progression_images}"
                            )

                            print(f"last_best_image is {last_best_image}")

                            # If all images are poor, the critic refuses to select one, so select the last image to move forward with
                            if last_best_image is None:
                                last_best_image = state.result_images[-1]
                            progressions.progression_images = temp_progressions
                            print(f"last_best_image is {last_best_image}")
                            if e.key == "retry":
                                state.retry_progression_images.append(progressions)
                            elif r.primary_view == True:
                                state.progression_images.append(progressions)
                            else:
                                state.alternate_progression_images.append(progressions)

                            if r.primary_view == True and (i + 1) == len(
                                articles_for_vto
                            ):
                                state.result_image = (
                                    last_best_image  # state.result_images[-1]
                                )
                            elif i == len(look_articles):
                                state.alternate_images.append(p["gcsUri"])

                            # TODO I believe this is just used for veo call. replace it with result_image?
                            state.reference_image_gcs_model = (
                                last_best_image  # state.result_images[-1]
                            )
                            yield

                            # # Catch specific exceptions you anticipate
                            # except ValueError as err:
                            #     print(f"ValueError caught: {err}")
                            #     current_error_message = f"Input Error: {err}"
                            # except requests.exceptions.HTTPError as err:
                            #     print(f"HTTPError caught: {err}")
                            #     current_error_message = f"Network/API Error: {err}"
                            # # Catch any other unexpected exceptions
                            # except Exception as err:
                            #     print(
                            #         f"Generic Exception caught: {type(err).__name__}: {err}"
                            #     )
                            #     current_error_message = (
                            #         f"An unexpected error occurred: {err}"
                            #     )

                            # finally:
                            end_time = time.time()  # Record the ending time
                            execution_time = (
                                end_time - start_time
                            )  # Calculate the elapsed time
                            print(
                                f"Execution time: {execution_time} seconds"
                            )  # Print the execution time
                            state.timing = (
                                f"Generation time: {round(execution_time)} seconds"
                            )
                            state.current_status = ""
                            yield

    print("Cut! That's a wrap!")

    if e.key == "primary" or e.key == "retry":
        # run final critic
        step_start_time = time.time()
        yield WorkflowStepResult(
            step_name="final_critic",
            status="processing",
            message=f"Step 9000 of 7: final critic",
            duration_seconds=0,
            data={},
        )

        with concurrent.futures.ThreadPoolExecutor() as executor:
            final_image_bytes_list = list(
                executor.map(download_from_gcs, [state.result_image])
            )
            state.current_status = "Critic evaluation in progress..."
            yield
            final_critic = final_image_critic(
                # article_image_bytes_list_wrapper,
                article_image_bytes_list,
                articles,
                final_image_bytes_list,
            )
            state.final_critic = final_critic
            state.final_accuracy = final_critic.accurate
            state.current_status = ""
            yield
            # retry if necessary
            print(f"final_critic is {final_critic}")
            if not state.final_critic.accurate and state.retry_counter < int(
                state.max_retry
            ):
                # retry logic
                new_event = e
                new_event.key = "retry"
                yield from on_click_vto_look(new_event)
            # elif state.generate_alternate_views:
            #     new_event = e
            #     new_event.key = "alternate"
            #     yield from on_click_vto_look(new_event)
            elif state.generate_video:
                # video_result = on_click_veo(e)
                yield from on_click_veo(e)

        step_duration = time.time() - step_start_time
        yield WorkflowStepResult(
            step_name="final_critic",
            status="complete",
            message="Article description generated",
            duration_seconds=step_duration,
            data={},
        )

    state.is_loading = False
    yield

    vto_end_time = time.time()
    vto_duration = vto_end_time - vto_start_time
    print(vto_duration)


def workflows_content_retail_look():
    state = me.state(PageState)
    with page_scaffold():  # pylint: disable=E1129
        with page_frame():  # pylint: disable=E1129
            header("Shop the Look", "Apparel", current_status=state.current_status)

            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=10,
                    height="100%",
                    width="100%",
                )
            ):
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="column",
                        gap=15,
                        width="100%",
                    )
                ):
                    build_tab_nav()


def on_click_clear_reference_image(
    e: me.ClickEvent = None,
):  # pylint: disable=unused-argument
    """Clear reference image"""
    state = me.state(PageState)
    state.is_loading = False
    for p in state.progression_images:
        del p

    state.progression_images = []
    state.retry_progression_images = []
    # state.progression_images.clear()
    state.alternate_progression_images = []
    state.alternate_images = []
    # state.veo_prompt_input = "Model walks torwards camera and slowly turns 360 degrees."
    state.result_video = None
    # state.generate_alternate_views = False
    state.look_description = ""

    # I2V reference Image
    state.reference_image_file_clothing = None
    state.reference_image_file_key_clothing = 0
    state.reference_image_gcs_clothing = []
    state.reference_image_uri_clothing = []

    state.reference_image_file_model = None
    state.reference_image_file_key_model = 0
    state.reference_image_gcs_model = None
    state.reference_image_uri_model = None

    state.result_image = None

    # TAB NAV
    state.aspect_ratio = "9:16"
    state.video_length = 8  # 5-8
    state.error_message = ""
    state.timing = None
    state.look = 0
    state.catalog = []
    state.before_image_uri = None
    state.models = []
    # state.selected_model = None
    state.result_images = []
    # state.final_accuracy = False
    state.final_critic = None
    state.tryon_started = False
    state.retry_counter = 0
    yield
