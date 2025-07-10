import mesop as me

from dataclasses import field

@me.stateclass
class PageState:
    """VTO Page State"""
    person_image_file: me.UploadedFile = None
    person_image_gcs: str = ""
    product_image_file: me.UploadedFile = None
    product_image_gcs: str = ""
    result_images: list[str] = field(default_factory=list)
    vto_sample_count: int = 4
    vto_base_steps: int = 0
    is_loading: bool = False
    error_message: str = ""
    show_error_dialog: bool = False
