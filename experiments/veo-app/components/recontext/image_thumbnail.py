import mesop as me
from typing import Callable

@me.component
def image_thumbnail(image_uri: str, index: int, on_remove: Callable):
    with me.box(style=me.Style(position="relative", width=100, height=100)):
        me.image(src=image_uri.replace("gs://", "https://storage.mtls.cloud.google.com/"), style=me.Style(width="100%", height="100%", border_radius=8, object_fit="cover"))
        with me.box(
            on_click=on_remove,
            key=str(index),
            style=me.Style(
                background="rgba(0, 0, 0, 0.5)",
                color="white",
                position="absolute",
                top=4,
                right=4,
                border_radius=50,
                padding=me.Padding.all(4),
                cursor="pointer",
            ),
        ):
            me.icon("close")
