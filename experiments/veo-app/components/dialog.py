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
"""Dialog mesop component"""

from typing import Callable, Optional

import mesop as me


@me.content_component
def dialog(is_open: bool, dialog_style: Optional[me.Style] = None, key: Optional[str] = None):
    """Renders a dialog component.

    The design of the dialog borrows from the Angular component dialog. So basically
    rounded corners and some box shadow.

    One current drawback is that it's not possible to close the dialog
    by clicking on the overlay background. This is due to
    https://github.com/google/mesop/issues/268.

    Args:
      is_open: Whether the dialog is visible or not.
      dialog_style: Optional style to apply to the main dialog box container,
                    allowing overrides for width, max_width, etc.
    """
    base_style = me.Style(
        background=me.theme_var("surface-container-lowest"),
        color=me.theme_var("on-surface"),
        border_radius=8,
        box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
        padding=me.Padding.all(24),
        width="auto",
        max_width="500px",  # Default max_width
        display="block",
        box_sizing="border-box",
    )

    # If a dialog_style is provided, merge it with the base_style.
    # Properties in dialog_style will override those in base_style.
    effective_style = base_style
    if dialog_style:
        # INFO: The style merging logic below is verbose because Mesop me.Style objects
        # are immutable, and there isn't a direct style.override() or style.extend() method.
        # This approach manually checks each property. For simpler customization,
        # it's recommended that the passed 'dialog_style' primarily focuses on overriding
        # key layout properties like width, max_width, height, etc., rather than attempting
        # to redefine all aspects of the style.
        # Create a new style object by "merging".
        # This isn't a deep merge, but for typical overrides like width/max_width it's fine.
        # For more complex merging, a helper function might be needed.

        # Convert Style objects to dicts, merge, then create new Style
        # This is a bit verbose but ensures all fields are handled.
        # A simpler approach for specific overrides might be direct attribute setting if Style was mutable.

        # Simpler approach: Create a new style and copy attributes, then update.
        # This assumes dialog_style won't try to unset things by passing None for specific fields
        # if those fields were set in base_style.

        # Let's create a new style and apply overrides.
        # We need to be careful as me.Style attributes are read-only after creation.
        # The most straightforward way is to conditionally set attributes when creating the style.

        # A more robust way to "merge" styles in Mesop if me.Style(**dict1, **dict2) worked perfectly
        # or if there was a style.update() method.
        # For now, let's assume dialog_style provides a complete override for conflicting properties.
        # A common pattern is to provide specific override parameters (e.g., width, max_width)
        # instead of a full Style object for merging.

        # Given me.Style is a dataclass, we can create a new one with combined properties.
        # However, we need to handle None values carefully.

        # Prioritizing properties from dialog_style and build a dictionary of properties and then 
        # create the Style object.

        style_props = {
            "background": dialog_style.background
            if dialog_style.background is not None
            else base_style.background,
            "color": dialog_style.color
            if dialog_style.color is not None
            else base_style.color,
            "border_radius": dialog_style.border_radius
            if dialog_style.border_radius is not None
            else base_style.border_radius,
            "box_shadow": dialog_style.box_shadow
            if dialog_style.box_shadow is not None
            else base_style.box_shadow,
            "padding": dialog_style.padding
            if dialog_style.padding is not None
            else base_style.padding,
            "width": dialog_style.width
            if dialog_style.width is not None
            else base_style.width,
            "max_width": dialog_style.max_width
            if dialog_style.max_width is not None
            else base_style.max_width,
            "display": dialog_style.display
            if dialog_style.display is not None
            else base_style.display,
            "box_sizing": dialog_style.box_sizing
            if dialog_style.box_sizing is not None
            else base_style.box_sizing,
            # Add any other me.Style properties here if needed for merging
            "margin": dialog_style.margin
            if dialog_style.margin is not None
            else base_style.margin,
            "height": dialog_style.height
            if dialog_style.height is not None
            else base_style.height,
            "flex_grow": dialog_style.flex_grow
            if dialog_style.flex_grow is not None
            else base_style.flex_grow,
            # ... and so on for all Style attributes
        }
        # Filter out None values before creating the Style object to avoid errors
        filtered_style_props = {k: v for k, v in style_props.items() if v is not None}
        effective_style = me.Style(**filtered_style_props)

    with me.box(
        key=key,
        style=me.Style(
            background="rgba(0,0,0,0.4)",
            display="block" if is_open else "none",
            height="100%",
            left=0,
            top=0,
            overflow_x="auto",
            overflow_y="auto",
            position="fixed",
            width="100%",
            z_index=1000,
            
        )
    ):
        with me.box(
            style=me.Style(
                display="flex",
                align_items="center",
                justify_content="center",
                height="100%",
                width="100%",
                padding=me.Padding.all(20),
            )
        ):
            # Apply the effective_style (base merged with override)
            with me.box(style=effective_style):
                me.slot()


@me.content_component
def dialog_actions():
    """Helper component for rendering action buttons so they are right aligned.

    This component is optional. If you want to position action buttons differently,
    you can just write your own Mesop markup.
    """
    with me.box(
        style=me.Style(
            display="flex", justify_content="flex-end", margin=me.Margin(top=24), gap=8
        )
    ):
        me.slot()
