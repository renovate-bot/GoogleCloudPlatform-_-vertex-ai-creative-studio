import mesop as me

@me.stateclass
class PageState:
    """VTO Page State"""
    person_image_file: me.UploadedFile = None
    person_image_gcs: str = ""
    product_image_file: me.UploadedFile = None
    product_image_gcs: str = ""
    result_image: str = ""
    is_loading: bool = False
    error_message: str = ""
    show_error_dialog: bool = False
