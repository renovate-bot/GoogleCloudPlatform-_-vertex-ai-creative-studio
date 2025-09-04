import mesop as me
import typing

@me.web_component(path="./interactive_tile.js")
def interactive_tile(
    *,
    label: str,
    icon: str,
    description: str,
    route: str,
    gif_url: str = "",
    on_tile_click: typing.Callable[[me.WebEvent], None] | None = None,
    key: str | None = None,
):
    """Defines the API for the interactive tile web component."""
    return me.insert_web_component(
        key=key,
        name="interactive-tile",
        properties={
            "label": label,
            "icon": icon,
            "description": description,
            "route": route,
            "gifUrl": gif_url,
        },
        events={
            "tileClickEvent": on_tile_click,
        },
    )
