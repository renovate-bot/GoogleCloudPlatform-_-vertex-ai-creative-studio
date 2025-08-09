"""Test page for the Worsfold Encoder component."""

import mesop as me
from components.worsfold_encoder.worsfold_encoder import worsfold_encoder
from state.state import AppState
from components.header import header
from components.page_scaffold import page_frame, page_scaffold

from components.library.video_chooser_button import video_chooser_button
from components.library.events import LibrarySelectionChangeEvent

@me.stateclass
class PageState:
    logs: str = ""
    result_gif: str = ""
    start_encode: bool = False
    ffmpeg_loaded: bool = False
    is_encoding: bool = False
    selected_video_gcs_uri: str = ""
    selected_video_url: str = "" # For the component
    selected_video_display_url: str = "" # For the video player

@me.page(
    path="/test_worsfold_encoder",
    title="Test Worsfold Encoder",
)
def test_worsfold_encoder_page():
    state = me.state(PageState)
    with page_scaffold():
        with page_frame():
            header("Worsfold Encoder Test", "movie")

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=20)):
                with me.box(style=me.Style(display="flex", flex_direction="column", gap=10)):
                    me.text("Select a video from the library:")
                    video_chooser_button(on_library_select=on_video_select)

                    if state.selected_video_display_url:
                        me.video(src=state.selected_video_display_url, style=me.Style(height="200px"))

                with me.box(style=me.Style(display="flex", flex_direction="column", gap=10, flex_grow=1)):
                    with me.content_button(
                        on_click=on_start_click, 
                        disabled=not state.ffmpeg_loaded or state.is_encoding or not state.selected_video_url,
                        type="flat",
                    ):
                        if state.is_encoding:
                            me.progress_spinner(diameter=20, stroke_width=3)
                            me.text("Encoding...")
                        else:
                            me.text("Start Encoding")

                    me.text("Logs:")
                    with me.box(style=me.Style(height="200px", width="100%", border=me.Border.all(me.BorderSide(width=1)), overflow_y="scroll")):
                        me.text(state.logs, style=me.Style(white_space="pre-wrap"))

            me.text("Result:")
            if state.result_gif:
                me.image(src=state.result_gif)
            else:
                me.text("GIF will appear here")

            worsfold_encoder(
                video_url=state.selected_video_url,
                config={"fps": 15, "scale": 0.5},
                start_encode=state.start_encode,
                on_log=on_log,
                on_encode_complete=on_encode_complete,
                on_load_complete=on_load_complete,
            )

def on_video_select(e: LibrarySelectionChangeEvent):
    state = me.state(PageState)
    state.selected_video_gcs_uri = e.gcs_uri
    state.selected_video_url = e.gcs_uri # Pass the gs:// URI to the component
    state.selected_video_display_url = e.gcs_uri.replace("gs://", "https://storage.mtls.cloud.google.com/")
    yield

def on_start_click(e: me.ClickEvent):
    state = me.state(PageState)
    state.is_encoding = True
    state.start_encode = True
    state.logs = ""
    state.result_gif = ""
    yield
    state.start_encode = False
    yield

def on_log(e: me.WebEvent):
    state = me.state(PageState)
    state.logs += e.value + "\n"
    yield

def on_encode_complete(e: me.WebEvent):
    state = me.state(PageState)
    state.result_gif = e.value
    state.is_encoding = False
    yield

def on_load_complete(e: me.WebEvent):
    print("on_load_complete event received in Python:", e)
    state = me.state(PageState)
    state.ffmpeg_loaded = True
    yield
