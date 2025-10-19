import mesop as me
import base64
import uuid
from components.page_scaffold import page_scaffold
from components.selfie_camera.selfie_camera import selfie_camera
from common.storage import store_to_gcs
from common.metadata import MediaItem, add_media_item_to_firestore
from state.state import AppState
from common.utils import create_display_url

@me.stateclass
class PageState:
    captured_image_url: str = ""
    is_saving: bool = False

def on_capture(e: me.WebEvent):
    """Handles the capture event from the selfie camera component."""
    state = me.state(PageState)
    app_state = me.state(AppState)

    state.is_saving = True
    yield

    try:
        # The data URL is in the format: data:image/png;base64,iVBORw0KGgo...
        # We need to strip the header to get the pure base64 data.
        header, encoded = e.value['value'].split(",", 1)
        image_data = base64.b64decode(encoded)

        # Generate a unique filename
        filename = f"selfie-{uuid.uuid4()}.png"

        # Store the image to GCS
        gcs_uri = store_to_gcs(
            "selfie_captures",
            filename,
            "image/png",
            image_data,
        )

        # Create a MediaItem and save it to Firestore
        item = MediaItem(
            gcs_uris=[gcs_uri],
            prompt="Selfie capture",
            mime_type="image/png",
            user_email=app_state.user_email,
            comment="captured by selfie camera",
        )
        add_media_item_to_firestore(item)

        state.captured_image_url = create_display_url(gcs_uri)

    except Exception as ex:
        print(f"ERROR: Failed to save selfie. Details: {ex}")
    finally:
        state.is_saving = False
        yield

@me.page(path="/selfie", title="Selfie Capture")
def page():
  """Defines the Mesop page route for Selfie Capture."""
  state = me.state(PageState)

  with page_scaffold(page_name="selfie"):
    with me.box(style=me.Style(padding=me.Padding.all(24), display="flex", flex_direction="column", align_items="center", gap=16)):
        me.text("Selfie Capture", type="headline-5")

        selfie_camera(on_capture=on_capture)

        if state.is_saving:
            me.progress_spinner()
            me.text("Saving image...")

        if state.captured_image_url:
            me.text("Captured Image:")
            me.image(src=state.captured_image_url, style=me.Style(width=400, border_radius=12))