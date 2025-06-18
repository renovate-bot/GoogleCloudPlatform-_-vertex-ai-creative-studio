import mesop as me
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from state.vto_state import PageState
from common.storage import store_to_gcs
from models.vto import generate_vto_image
from common.metadata import add_vto_metadata
from state.state import AppState

@me.page(path="/vto")
def vto():
    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Virtual Try-On", "checkroom")

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
                with me.box(style=me.Style(width="calc(50% - 8px)")):
                    me.uploader(
                        label="Upload Person Image",
                        on_upload=lambda e: on_upload_person(e),
                        style=me.Style(width="100%"),
                        key="person_uploader",
                    )
                    if state.person_image_gcs:
                        me.image(src=state.person_image_gcs, style=me.Style(width="400px", margin=me.Margin(top=16), border_radius=12))

                with me.box(style=me.Style(width="calc(50% - 8px)")):
                    me.uploader(
                        label="Upload Product Image",
                        on_upload=lambda e: on_upload_product(e),
                        style=me.Style(width="100%"),
                        key="product_uploader",
                    )
                    if state.product_image_gcs:
                        me.image(src=state.product_image_gcs, style=me.Style(width="400px", margin=me.Margin(top=16), border_radius=12))

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=16, margin=me.Margin(top=16))):
              me.button("Generate", on_click=on_generate)
              me.button("Clear", on_click=on_clear, type="stroked")

            if state.is_loading:
                me.progress_spinner()

            if state.result_image:
                me.image(src=state.result_image, style=me.Style(width="100%", margin=me.Margin(top=16)))

def on_upload_person(e: me.UploadEvent):
    state = me.state(PageState)
    state.person_image_file = e.file
    gcs_url = store_to_gcs("vto_person_images", e.file.name, e.file.mime_type, e.file.getvalue())
    state.person_image_gcs = f"https://storage.mtls.cloud.google.com/{gcs_url}"
    yield

def on_upload_product(e: me.UploadEvent):
    state = me.state(PageState)
    state.product_image_file = e.file
    gcs_url = store_to_gcs("vto_product_images", e.file.name, e.file.mime_type, e.file.getvalue())
    state.product_image_gcs = f"https://storage.mtls.cloud.google.com/{gcs_url}"
    yield

def on_generate(e: me.ClickEvent):
    app_state = me.state(AppState)
    state = me.state(PageState)
    state.is_loading = True
    yield

    try:
        result_gcs_uri = generate_vto_image(state.person_image_gcs, state.product_image_gcs)
        if result_gcs_uri.startswith("gs://"):
            state.result_image = result_gcs_uri.replace("gs://", "https://storage.mtls.cloud.google.com/")
        else:
            state.result_image = result_gcs_uri
        add_vto_metadata(
            person_image_gcs=state.person_image_gcs,
            product_image_gcs=state.product_image_gcs,
            result_image_gcs=result_gcs_uri,
            user_email=app_state.user_email,
        )
    except Exception as e:
        state.error_message = str(e)
        state.show_error_dialog = True
    finally:
        state.is_loading = False
        yield

def on_clear(e: me.ClickEvent):
    state = me.state(PageState)
    state.person_image_gcs = ""
    state.product_image_gcs = ""
    state.result_image = ""
    yield