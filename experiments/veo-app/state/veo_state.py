import mesop as me


@me.stateclass
class PageState:
    """Mesop Page State"""

    veo_model: str = "2.0"
    veo_prompt_input: str = ""
    veo_prompt_placeholder: str = ""
    veo_prompt_textarea_key: int = 0

    veo_mode: str = "t2v"

    prompt: str
    original_prompt: str

    aspect_ratio: str = "16:9"
    video_length: int = 5  # 5-8

    # I2V reference Image
    reference_image_file: me.UploadedFile = None
    reference_image_file_key: int = 0
    reference_image_gcs: str
    reference_image_uri: str
    reference_image_mime_type: str

    # Interpolation last reference image
    last_reference_image_file: me.UploadedFile = None
    last_reference_image_file_key: int = 0
    last_reference_image_gcs: str
    last_reference_image_uri: str
    last_reference_image_mime_type: str

    # extend
    video_extend_length: int = 0  # 4-7

    # Rewriter
    auto_enhance_prompt: bool = False

    rewriter_name: str

    is_loading: bool = False
    show_error_dialog: bool = False
    error_message: str = ""
    result_video: str
    timing: str
