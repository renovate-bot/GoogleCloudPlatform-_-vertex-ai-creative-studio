import mesop as me
from dataclasses import field
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from common.storage import store_to_gcs
from models.image_models import recontextualize_product_in_scene
from common.metadata import add_media_item
from state.state import AppState
from config.default import Default
from components.recontext.image_thumbnail import image_thumbnail

config = Default()

@me.stateclass
class PageState:
    """Recontext Page State"""
    uploaded_images: list[me.UploadedFile] = field(default_factory=list) # pylint: disable=invalid-field-call
    uploaded_image_gcs_uris: list[str] = field(default_factory=list) # pylint: disable=invalid-field-call
    prompt: str = ""
    result_images: list[str] = field(default_factory=list) # pylint: disable=invalid-field-call
    is_loading: bool = False
    error_message: str = ""
    show_error_dialog: bool = False

@me.page(path="/recontextualize")
def recontextualize():
    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Product in Scene", "scene_based_layout")

            with me.box(style=me.Style(display="flex", flex_direction="column", gap=16)):
                me.uploader(
                    label="Upload Product Images (1-4)",
                    on_upload=on_upload,
                    style=me.Style(width="100%"),
                    key="product_uploader",
                    multiple=True,
                )

                if state.uploaded_image_gcs_uris:
                    with me.box(style=me.Style(display="flex", flex_wrap="wrap", gap=16)):
                        for i, uri in enumerate(state.uploaded_image_gcs_uris):
                            image_thumbnail(image_uri=uri, index=i, on_remove=on_remove_image)

                me.input(
                    label="Scene Prompt",
                    on_input=lambda e: on_input_prompt(e.value),
                    style=me.Style(width="100%"),
                )

                with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
                    me.button("Generate", on_click=on_generate, type="flat")
                    me.button("Clear", on_click=on_clear, type="stroked")

                if state.is_loading:
                    with me.box(
                        style=me.Style(
                            display="flex", align_items="center", justify_content="center",
                        )
                    ):
                        me.progress_spinner()

                if state.result_images:
                    with me.box(style=me.Style(display="flex", flex_wrap="wrap", gap=16, justify_content="center", margin=me.Margin(top=16))):
                        for image in state.result_images:
                            me.image(src=image, style=me.Style(width="400px", border_radius=12))

def on_upload(e: me.UploadEvent):
    state = me.state(PageState)
    for file in e.files:
        gcs_url = store_to_gcs("recontext_sources", file.name, file.mime_type, file.getvalue())
        state.uploaded_image_gcs_uris.append(gcs_url)
    yield

def on_input_prompt(value: str):
    state = me.state(PageState)
    state.prompt = value
    yield


def on_remove_image(e: me.ClickEvent):
    state = me.state(PageState)
    del state.uploaded_image_gcs_uris[int(e.key)]
    yield


def on_generate(e: me.ClickEvent):
    app_state = me.state(AppState)
    state = me.state(PageState)
    state.result_images = []
    state.is_loading = True
    yield

    try:
        result_gcs_uris = recontextualize_product_in_scene(state.uploaded_image_gcs_uris, state.prompt)
        state.result_images = [uri.replace("gs://", "https://storage.mtls.cloud.google.com/") for uri in result_gcs_uris]
        add_media_item(
            user_email=app_state.user_email,
            model=config.MODEL_IMAGEN_PRODUCT_RECONTEXT,
            mime_type="image/png",
            prompt=state.prompt,
            gcs_uris=result_gcs_uris,
            source_images_gcs=state.uploaded_image_gcs_uris,
            comment="product recontext",
        )
    except Exception as e:
        state.error_message = str(e)
        state.show_error_dialog = True
    finally:
        state.is_loading = False
        yield

def on_clear(e: me.ClickEvent):
    state = me.state(PageState)
    state.uploaded_image_gcs_uris = []
    state.result_images = []
    yield