import mesop as me
import typing

@me.web_component(path="./selfie_camera.js")
def selfie_camera(
    *,
    on_capture: typing.Callable[[me.WebEvent], None] | None = None,
    key: str | None = None,
):
    """Defines the API for the selfie_camera web component."""
    return me.insert_web_component(
        key=key,
        name="selfie-camera",
        events={
            "capture": on_capture,
        },
    )
