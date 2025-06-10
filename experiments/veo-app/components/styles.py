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