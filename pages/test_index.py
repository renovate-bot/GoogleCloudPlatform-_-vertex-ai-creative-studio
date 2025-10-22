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
from components.header import header
from components.page_scaffold import on_theme_load
from components.theme_manager.theme_manager import theme_manager
from state.state import AppState


def on_navigate(e: me.ClickEvent):
    me.navigate(e.key)


@me.page(
    path="/labs",
)
def page():
    app_state = me.state(AppState)
    theme_manager(theme=app_state.theme_mode, on_theme_load=on_theme_load)

    test_pages = [
        {
            "title": "Banana Studio",
            "description": "An experimental Gemini Image Generation page.",
            "route": "/banana-studio",
        },
        {
            "title": "Gemini Writers Workshop",
            "description": "A place to generate text content from prompts and optional media assets.",
            "route": "/gemini-writers-workshop",
        },
        {
            "title": "Guideline Analysis",
            "description": "A page to analyze a media item's prompt and generate guideline criteria.",
            "route": "/guideline-analysis",
        },
        {
            "title": "VTO Model Composite Card Generator",
            "description": "A tool to generate a matrix of virtual models with different attributes.",
            "route": "/test_vto_prompt_generator",
        },
        {
            "title": "Selfie Camera",
            "description": "A test page for the selfie camera component.",
            "route": "/selfie",
        },
        {
            "title": "Uploader",
            "description": "A test page for determining uploader component capabilities.",
            "route": "/test_uploader",
        },
        {
            "title": "Character Consistency Test",
            "description": "A test page for the character consistency workflow.",
            "route": "/test_character_consistency",
        },
        {
            "title": "Pixie Compositor Test",
            "description": "A test page for the Pixie Compositor web component.",
            "route": "/test_pixie_compositor",
        },
        {
            "title": "Media Chooser Test",
            "description": "A test page for the generic, high-performance media chooser component.",
            "route": "/test_media_chooser",
        },
        {
            "title": "Proxy Caching Test",
            "description": "A page to compare the performance of signed URLs vs. a caching proxy endpoint.",
            "route": "/test_proxy_caching",
        }
    ]

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            height="100%",
        )
    ):
        with me.box(
            style=me.Style(
                background=me.theme_var("background"),
                height="100%",
                overflow_y="scroll",
                margin=me.Margin(bottom=20),
            )
        ):
            with me.box(
                style=me.Style(
                    background=me.theme_var("background"),
                    padding=me.Padding(top=24, left=24, right=24, bottom=24),
                    display="flex",
                    flex_direction="column",
                )
            ):
                header("Labs Page Index", "science")

                me.text("A list of test pages for debugging and exploring new features.")

                with me.box(style=me.Style(margin=me.Margin(top=24))):
                    me.text(
                        "Test Pages:",
                        style=me.Style(
                            font_weight="bold",
                            font_size="1.2rem",
                            margin=me.Margin(bottom=12),
                        ),
                    )
                    with me.box(
                        style=me.Style(
                            display="grid",
                            grid_template_columns="repeat(auto-fill, minmax(250px, 1fr))",
                            gap=15,
                        )
                    ):
                        for test_page in test_pages:
                            with me.box(
                                key=test_page["route"],
                                on_click=on_navigate,
                                style=me.Style(
                                    border=me.Border.all(
                                        me.BorderSide(
                                            width=1,
                                            style="solid",
                                            color=me.theme_var("outline"),
                                        )
                                    ),
                                    background=me.theme_var("surface-container-lowest"),
                                    padding=me.Padding.all(15),
                                    border_radius=12,
                                    cursor="pointer",
                                ),
                            ):
                                me.text(test_page["title"], type="subtitle-1")
                                me.text(
                                    test_page["description"],
                                    type="body-2",
                                    style=me.Style(margin=me.Margin(top=8)),
                                )
