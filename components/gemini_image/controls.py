import mesop as me
from config.gemini_image_models import GeminiImageModelConfig

@me.component
def gemini_image_controls(
    state,
    model_config: GeminiImageModelConfig,
    on_aspect_ratio_change,
    on_image_size_change,
    on_num_images_change,
    on_search_change,
    on_image_search_change,
    on_include_thoughts_change,
    on_thinking_level_change,
):
    """Shared UI controls for Gemini Image Generation features."""
    with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
        me.select(
            label="Aspect Ratio",
            options=[
                me.SelectOption(label="1:1", value="1:1"),
                me.SelectOption(label="3:2", value="3:2"),
                me.SelectOption(label="2:3", value="2:3"),
                me.SelectOption(label="3:4", value="3:4"),
                me.SelectOption(label="4:3", value="4:3"),
                me.SelectOption(label="4:5", value="4:5"),
                me.SelectOption(label="9:16", value="9:16"),
                me.SelectOption(label="16:9", value="16:9"),
                me.SelectOption(label="21:9", value="21:9"),
            ],
            on_selection_change=on_aspect_ratio_change,
            value=str(state.aspect_ratio),
            style=me.Style(flex_grow=1),
        )

        if model_config and model_config.supported_image_sizes:
            me.select(
                label="Image Size",
                options=[
                    me.SelectOption(label=size, value=size)
                    for size in model_config.supported_image_sizes
                ],
                on_selection_change=on_image_size_change,
                value=str(state.image_size),
                style=me.Style(flex_grow=1, width="65%"),
            )

    me.box(style=me.Style(height=16))

    max_output_images = model_config.max_output_images if model_config else 1

    with me.box(style=me.Style(display="flex", flex_direction="row", gap=16, align_items="center", margin=me.Margin(bottom=16))):
        if max_output_images > 1:
            me.select(
                label="Number of Images",
                options=[me.SelectOption(label="Auto", value="0")]
                + [
                    me.SelectOption(label=str(i), value=str(i))
                    for i in range(1, max_output_images + 1)
                ],
                on_selection_change=on_num_images_change,
                value=str(state.num_images_to_generate),
                style=me.Style(flex_grow=1),
            )

    if model_config and model_config.supports_search:
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=16, align_items="center", margin=me.Margin(bottom=16))):
            me.checkbox(
                label="Use Web Search",
                checked=state.use_search,
                on_change=on_search_change,
            )
            me.checkbox(
                label="Use Image Search",
                checked=state.use_image_search,
                on_change=on_image_search_change,
            )
            
    if model_config and getattr(model_config, "supports_thinking", False):
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=16, align_items="center", margin=me.Margin(bottom=16))):
            me.checkbox(
                label="Include Thoughts",
                checked=state.include_thoughts,
                on_change=on_include_thoughts_change,
            )
            me.select(
                label="Thinking Level",
                options=[
                    me.SelectOption(label="HIGH", value="HIGH"),
                    me.SelectOption(label="MINIMAL", value="MINIMAL")
                ],
                on_selection_change=on_thinking_level_change,
                value=state.thinking_level,
                style=me.Style(flex_grow=1),
            )
