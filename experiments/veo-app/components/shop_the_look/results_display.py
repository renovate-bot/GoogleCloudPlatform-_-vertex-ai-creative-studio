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

import models.shop_the_look_workflow as shop_the_look_workflow
from models.shop_the_look_workflow import run_shop_the_look_workflow
from pages.styles import _BOX_STYLE_CENTER_DISTRIBUTED
from state.shop_the_look_state import PageState
from state.state import AppState


@me.component
def results_display():
    state = me.state(PageState)
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="row",
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
                        width="200px",
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
                            on_click=on_click_vto_look, # This should be on_click_veo, which we will create later
                        ):
                            with me.box(style=icon_style):
                                me.icon("cinematic_blur")
                                me.text("Create Video")
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
                                    width="100px",
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
                                            width="100px",
                                            height="100px",
                                            font_size=(
                                                "25px" if state.result_video else "50px"
                                            ),
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
                            ),
                            height=(
                                "250px" if state.result_video else "500px"
                            ),
                            object_fit="contain",
                            border_radius="5px",
                            box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                        ),
                    )
                    if state.result_video:
                        video_url = state.result_video.replace(
                            "gs://",
                            "https://storage.mtls.cloud.google.com/",
                        )
                        with me.tooltip(message=state.veo_prompt_input):
                            me.icon("information")
                        me.video(
                            src=video_url,
                            style=me.Style(
                                border_radius=6,
                                width="250px",
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
                                            width="200px",
                                            height="200px",
                                            object_fit="contain",
                                            border_radius="5px",
                                            box_shadow="0 2px 4px rgba(0,0,0,0.1)",
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
                        width="500px",
                        height="500px",
                        object_fit="contain",
                        border_radius="5px",
                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",
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
                                        width="200px",
                                        height="200px",
                                        object_fit="cover",
                                        border_radius="5px",
                                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",
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
                                    width="200px",
                                    height="200px",
                                    object_fit="contain",
                                    border_radius="5px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",
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
                                        width="200px",
                                        height="200px",
                                        object_fit="cover",
                                        border_radius="5px",
                                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                                    ),
                                )

def on_click_vto_look(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Handles the click event to start the Shop the Look workflow."""
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_loading = True
    state.tryon_started = True
    state.show_error_dialog = False
    state.error_message = ""
    yield

    try:
        look_articles = shop_the_look_workflow.get_selected_look()
        for step_result in run_shop_the_look_workflow(app_state.user_email, state.selected_model, look_articles, int(state.vto_sample_count), int(state.max_retry)):
            state.current_status = step_result.message
            if step_result.data.get("look_description"):
                state.look_description = step_result.data["look_description"]
            if step_result.data.get("articles"):
                new_articles = []
                for item in state.articles:
                    for article_dict in step_result.data["articles"]:
                        if item.item_id.split("/")[-1] == article_dict['article_image_path'].split("/")[-1]:
                            item.ai_description = article_dict['article_description']
                    new_articles.append(item)
                state.articles = new_articles
            if step_result.data.get("progressions"):
                new_progression_images = state.progression_images.copy()
                if step_result.data["primary_view"]:
                    new_progression_images.append(step_result.data["progressions"])
                    state.progression_images = new_progression_images
                else:
                    new_alternate_progression_images = state.alternate_progression_images.copy()
                    new_alternate_progression_images.append(step_result.data["progressions"])
                    state.alternate_progression_images = new_alternate_progression_images
                print(f"DEBUG: Progression images count: {len(state.progression_images)}")
                print(f"DEBUG: Alternate progression images count: {len(state.alternate_progression_images)}")
                
                yield
            if step_result.data.get("last_best_image"):
                if step_result.data["primary_view"]:
                    state.result_image = step_result.data["last_best_image"]
                else:
                    state.alternate_images.append(step_result.data["last_best_image"])
            if step_result.data.get("final_critic"):
                state.final_critic = step_result.data["final_critic"]
                state.final_accuracy = state.final_critic.accurate

            yield

        state.current_status = "Workflow complete!"

    except Exception as err:
        state.error_message = f"An unexpected error occurred: {err}"
        state.show_error_dialog = True
        state.current_status = "Workflow failed."

    state.is_loading = False
    yield

def on_click_manual_retry(e: me.ClickEvent):
    state = me.state(PageState)
    state.retry_counter -= 1

    new_event = e
    new_event.key = "retry"
    yield from on_click_vto_look(new_event)

def on_click_clear_reference_image(
    e: me.ClickEvent = None,  # pylint: disable=unused-argument
):
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
