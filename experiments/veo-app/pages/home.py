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
"""Welcome page."""

from collections import defaultdict
from typing import Dict, List

import mesop as me

from components.capability_tile import media_tile
from components.header import header
from config.default import WELCOME_PAGE

GROUP_ORDER = ["foundation", "workflows", "app"]


def home_page_content(app_state: me.state):  # pylint: disable=unused-argument
    """Home Page"""
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            height="100%",
        ),
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
                header("GenMedia Creative Studio", "home")

                # me.text(
                #     "GenMedia Creative Studio",
                #     style=me.Style(
                #         color="transparent",
                #         font_size="2.5rem",
                #         font_weight="bold",
                #         background=(
                #             "linear-gradient(90deg, rgb(0, 44, 112) 0%, rgb(7, 110, 255) 100%)"
                #             "text"
                #         ),
                #     ),
                # )
                me.text(
                    "Welcome to the v.next of Vertex AI GenMedia Creative Studio"
                )

                # Group pages by the "group" key
                grouped_pages: Dict[str, List[Dict]] = defaultdict(list)
                pages_to_display = [
                    page for page in WELCOME_PAGE if page.get("display") != "Home"
                ]

                for page_data in pages_to_display:
                    group_name = page_data.get("group")
                    if group_name:
                        grouped_pages[group_name].append(page_data)

                # Render each group based on GROUP_ORDER
                for group_name in GROUP_ORDER:
                    items_in_group = grouped_pages.get(
                        group_name
                    )  # Get items for the current group

                    if (
                        not items_in_group
                    ):  # Skip if group is not in data or has no items
                        continue

                    # Group Title
                    me.text(
                        group_name.replace("_", " ").title(),
                        style=me.Style(
                            font_size="1.2rem",
                            font_weight="bold",
                            margin=me.Margin(top=24, bottom=12),
                            color=me.theme_var("on-surface"),
                            background=(
                             "linear-gradient(90deg, rgb(0, 44, 112) 0%, rgb(7, 110, 255) 100%)"
                             "text"
                         ),
                        ),
                    )

                    # Row for tiles in this group
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            flex_wrap="wrap",
                            gap=16,
                            justify_content="flex-start",
                            margin=me.Margin(bottom=24),
                        ),
                    ):
                        for page_data in items_in_group:
                            route = page_data.get("route")
                            icon = page_data.get("icon", "broken_image")
                            display_name = page_data.get("display", "Unnamed Page")

                            media_tile(display_name, icon, route)
