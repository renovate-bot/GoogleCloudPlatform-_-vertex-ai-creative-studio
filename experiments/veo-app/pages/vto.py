import mesop as me
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from state.vto_state import PageState
from common.storage import store_to_gcs
from models.vto import generate_vto_image
from common.metadata import add_vto_metadata
from state.state import AppState
from config.default import Default

config = Default()

@me.page(path="/vto")
def vto():
    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Virtual Try-On", "checkroom")

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
                with me.box(style=me.Style(width="calc(50% - 8px)", display="flex", flex_direction="column", align_items="center")):
                    me.uploader(
                        label="Upload Person Image",
                        on_upload=lambda e: on_upload_person(e),
                        style=me.Style(width="100%"),
                        key="person_uploader",
                    )
                    if state.person_image_gcs:
                        me.image(src=state.person_image_gcs, style=me.Style(width="400px", margin=me.Margin(top=16), border_radius=12))

                with me.box(style=me.Style(width="calc(50% - 8px)", display="flex", flex_direction="column", align_items="center")):
                    me.uploader(
                        label="Upload Product Image",
                        on_upload=lambda e: on_upload_product(e),
                        style=me.Style(width="100%"),
                        key="product_uploader",
                    )
                    if state.product_image_gcs:
                        me.image(src=state.product_image_gcs, style=me.Style(width="400px", margin=me.Margin(top=16), border_radius=12))

            with me.box(style=me.Style(width="400px", margin=me.Margin(top=16))):
                with me.box(style=me.Style(display="flex", justify_content="space-between")):
                    me.text("Number of images")
                    me.text(f"{state.vto_sample_count}")
                me.slider(
                    min=1,
                    max=4,
                    step=1,
                    value=state.vto_sample_count,
                    on_value_change=lambda e: on_sample_count_change(e.value),
                )

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=16, margin=me.Margin(top=16))):
              me.button("Generate", on_click=on_generate)
              me.button("Clear", on_click=on_clear, type="stroked")

            if state.is_loading:
                me.progress_spinner()

            if state.result_images:
                print(f"Images: {state.result_images}")
                with me.box(style=me.Style(display="flex", flex_wrap="wrap", gap=16, margin=me.Margin(top=16))):
                    for image in state.result_images:
                        me.image(src=image, style=me.Style(width="400px", border_radius=12))

def on_upload_person(e: me.UploadEvent):
    """Upload person image handler"""
    state = me.state(PageState)
    state.person_image_file = e.file
    gcs_url = store_to_gcs("vto_person_images", e.file.name, e.file.mime_type, e.file.getvalue())
    state.person_image_gcs = gcs_url.replace("gs://", "https://storage.mtls.cloud.google.com/")
    yield

def on_upload_product(e: me.UploadEvent):
    """Upload product image handler"""
    state = me.state(PageState)
    state.product_image_file = e.file
    gcs_url = store_to_gcs("vto_product_images", e.file.name, e.file.mime_type, e.file.getvalue())
    state.product_image_gcs = gcs_url.replace("gs://", "https://storage.mtls.cloud.google.com/")
    yield

def on_generate(e: me.ClickEvent):
    """Generate VTO handler"""
    app_state = me.state(AppState)
    state = me.state(PageState)
    state.is_loading = True
    yield

    try:
        result_gcs_uris = generate_vto_image(state.person_image_gcs, state.product_image_gcs, state.vto_sample_count, state.vto_base_steps)
        print(f"Result GCS URIs: {result_gcs_uris}")
        state.result_images = [
            uri.replace("gs://", "https://storage.mtls.cloud.google.com/")
            for uri in result_gcs_uris
        ]
        add_vto_metadata(
            person_image_gcs=state.person_image_gcs,
            product_image_gcs=state.product_image_gcs,
            result_image_gcs=result_gcs_uris,
            user_email=app_state.user_email,
        )
    except Exception as e:
        state.error_message = str(e)
        state.show_error_dialog = True
    finally:
        state.is_loading = False
        yield
    yield

def on_sample_count_change(value: int):
    state = me.state(PageState)
    state.vto_sample_count = value
    yield

def on_clear(e: me.ClickEvent):
    state = me.state(PageState)
    state.person_image_gcs = ""
    state.product_image_gcs = ""
    state.result_images = []
    yield