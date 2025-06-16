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


SIDENAV_MIN_WIDTH=68
SIDENAV_MAX_WIDTH=200

DEFAULT_MENU_STYLE = me.Style(align_content="left")

_FANCY_TEXT_GRADIENT = me.Style(
    color="transparent",
    background=(
        "linear-gradient(72.83deg,#4285f4 11.63%,#9b72cb 40.43%,#d96570 68.07%)"
        " text"
    ),
)

_BOX_STYLE = me.Style(
    background=me.theme_var("surface"),  # Use theme variable for background
    border_radius=12,
    box_shadow=me.theme_var("shadow_elevation_2"),  # Use theme variable for shadow
    padding=me.Padding.all(16),  # Simpler padding
    display="flex",
    flex_direction="column",
    margin=me.Margin(bottom=28),
)